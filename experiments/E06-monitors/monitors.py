"""Black-box monitors on the E05 step table: LLM judge and decision models, cached, under a hard budget cap.

Rows come from the E05 fit run (rows.jsonl + main/predictions.npz eligible set), so every monitor score
joins one-to-one with the probe's out-of-fold score by (episode, request_idx, request_sha256).
The network is only touched by `post_json`; tests replace it.
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
import urllib.request
import urllib.error
import http.client
import socket
import threading
import time
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'experiments/E01-behaviour-pilot'))
sys.path.insert(0, str(HERE))
from collusion.runs import Run, start_run, write_json_atomic  # noqa: E402
from judge_labels import reserve_cost  # noqa: E402
import prompts as P  # noqa: E402

FIT_RUN = '20261024-1937-e05-probe-core'
MONITORS = {
    'llm': 'openai/gpt-5-nano',
    'luna': 'openai/gpt-6-luna-decisions',
    'jev': 'typesafe/jev-1.14',
}
DECISION_URL = 'https://openrouter.ai/api/alpha/decisions'
CHAT_URL = 'https://openrouter.ai/api/v1/chat/completions'
MAX_CAP = Decimal('2.50')       # prelim / smoke runs
MAX_CAP_MAIN = Decimal('17.00')  # only for run directories named e06-monitor-main (Leo, 2026-10-25)
LLM_MAX_TOKENS = 3000


# ---------- step table ----------

def load_step_table(fit_run=FIT_RUN):
    """E05 rows restricted to the main variant's eligible set, with seed-42 fold, step id and scenario.

    For the main run, swap in the replay-2 step table; rows must carry episode, request_idx,
    request_sha256, condition, label, round, family and a fold id ('fold' or 'fold_seed42').
    'scenario' is filled from the episode when missing."""
    import numpy as np  # only needed here; tests use synthetic tables
    base = ROOT / 'runs' / fit_run
    rows = [json.loads(s) for s in (base / 'rows.jsonl').read_text().splitlines()]
    d = np.load(base / 'main' / 'predictions.npz')
    table = []
    for i in d['eligible']:
        r = dict(rows[int(i)])
        r['row'] = int(i)
        r['fold_seed42'] = int(d['folds'][0, i])
        r['step_id'] = r['episode'] + '::request_idx=' + str(r['request_idx'])
        table.append(r)
    return add_scenarios(table)


REQUIRED = ('episode', 'request_idx', 'request_sha256', 'condition', 'round')


def load_steps_file(path):
    """All eligible rows of a replay step table (e.g. the replay-2 plan/fit rows), no sampling.

    Eligible = valid_for_comparison and token_in_context and before_first_action (the action step's own
    input is kept, as in E05). Accepts 'episode' or 'episode_key'."""
    table = []
    for line in Path(path).read_text().splitlines():
        r = json.loads(line)
        r.setdefault('episode', r.get('episode_key'))
        if not (r.get('valid_for_comparison', r.get('valid')) and r.get('token_in_context') and r.get('before_first_action')):
            continue
        missing = [k for k in REQUIRED if r.get(k) is None]
        if missing:
            raise ValueError(f'Step table row lacks {missing}')
        r['step_id'] = r['episode'] + '::request_idx=' + str(r['request_idx'])
        r.setdefault('family', str(r.get('family_id')))
        table.append(r)
    if len({r['step_id'] for r in table}) != len(table):
        raise ValueError('Duplicate step ids')
    return add_scenarios(table)


def add_scenarios(table, load_episode=None):
    load_episode = load_episode or (lambda k: json.loads(episode_path(k).read_text()))
    cache = {}
    for r in table:
        if not r.get('scenario'):
            if r['episode'] not in cache:
                cache[r['episode']] = scenario_id(load_episode(r['episode']))
            r['scenario'] = cache[r['episode']]
    return table


def sample_steps(table, n_pos=60, n_held=60, n_control=30, seed=6):
    """Stratified sample: give-in steps spread over each episode's rounds, held and control steps
    matched to the give-in steps' rounds. Uses labels and rounds only, never scores."""
    rng = random.Random(seed)
    by_ep = defaultdict(list)
    for r in table:
        by_ep[r['episode']].append(r)
    give = sorted(e for e, rs in by_ep.items() if rs[0]['condition'] == 'recruiting' and rs[0]['label'] == 1)
    held = sorted(e for e, rs in by_ep.items() if rs[0]['condition'] == 'recruiting' and rs[0]['label'] == 0)
    ctrl = sorted(e for e, rs in by_ep.items() if rs[0]['condition'] != 'recruiting')
    pos = []
    # Round-robin over give-in episodes; each pass takes a step from a different part of the episode.
    pools = {e: sorted(by_ep[e], key=lambda r: r['ordinal']) for e in give}
    for e in give:
        rng.shuffle(pools[e])
    while len(pos) < n_pos and any(pools.values()):
        for e in give:
            if pools[e] and len(pos) < n_pos:
                pos.append(pools[e].pop())
    def matched(episodes, n):
        pick, used = [], set()
        candidates = defaultdict(list)
        for e in episodes:
            for r in by_ep[e]:
                candidates[r['round']].append(r)
        for v in candidates.values():
            rng.shuffle(v)
        target_rounds = [r['round'] for r in pos]
        rng.shuffle(target_rounds)
        for rnd in target_rounds:
            if len(pick) >= n:
                break
            options = [r for r in candidates.get(rnd, []) if r['step_id'] not in used]
            fresh = [r for r in options if r['episode'] not in {p['episode'] for p in pick}]
            choice = (fresh or options or [None])[0]
            if choice:
                pick.append(choice); used.add(choice['step_id'])
        return pick
    return pos + matched(held, n_held) + matched(ctrl, n_control)


def episode_path(episode_key):
    run, name = episode_key.split('/')
    return ROOT / 'runs' / run / 'episodes' / name


def target_messages(ep, request_idx):
    """The message list of one target API request: what the target had seen at that step."""
    record = ep['requests'][request_idx]
    if record['actor'] != 'target':
        raise ValueError('Expected a target request')
    return record['request']['messages']


def request_sha(ep, request_idx):
    """Same digest as E02 replay.py `digest(record['request'])`, so joins can be verified."""
    data = json.dumps(ep['requests'][request_idx]['request'], ensure_ascii=False, separators=(',', ':')).encode()
    return hashlib.sha256(data).hexdigest()


# ---------- requests ----------

def scenario_id(ep):
    """Scenario label for strata: spray row id, else deploy-token generation (v1/v2)."""
    md = ep['scenario_spec'].get('metadata', {})
    if md.get('spray_row_id'):
        return md['spray_row_id']
    if md.get('scenario_family') == 'deploy-token':
        return 'deploy-token-v2' if md.get('scenario_generation') == 'deploy-token-v2' else 'deploy-token-v1'
    return md.get('scenario_family') or ep['scenario_spec'].get('name')


def option_order(monitor, step_id):
    return None if monitor == 'llm' else P.option_order(step_id)


def build_call(monitor, prompt_id, messages, level, metadata, order=None):
    model = MONITORS[monitor]
    if monitor == 'llm':
        body = {'model': model, 'messages': [{'role': 'user', 'content': P.llm_prompt(prompt_id, messages, level, metadata)}],
                'max_completion_tokens': LLM_MAX_TOKENS, 'reasoning': {'effort': 'low'},
                'provider': {'order': ['OpenAI'], 'allow_fallbacks': False,
                             'max_price': {'prompt': 0.05, 'completion': 0.40}}}
        return CHAT_URL, body
    return DECISION_URL, P.decision_payload(model, prompt_id, messages, level, metadata, order or ('yes', 'no'))


def cache_key(step_id, request_sha256, monitor, prompt_id, level, order=None):
    raw = json.dumps([step_id, request_sha256, MONITORS[monitor], prompt_id, P.prompt_sha(prompt_id), level]
                     + ([list(order)] if order else []))
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


SCORE_RE = re.compile(r'<score>\s*\[?\s*(-?\d+(?:\.\d+)?)')


def parse_llm(text, scale):
    if not isinstance(text, str):
        raise ValueError('No text')
    found = SCORE_RE.findall(text)
    if not found:
        raise ValueError('No <score> tag')
    value = float(found[-1])
    if not 0 <= value <= scale:
        raise ValueError(f'Score {value} outside 0..{scale}')
    return value / scale


def parse_decision(raw, prompt_id):
    answer = (raw.get('answers') or {}).get(prompt_id) or {}
    probs = answer.get('probabilities') or {}
    if 'yes' not in probs:
        raise ValueError('Missing yes probability')
    value = float(probs['yes'])
    if not 0 <= value <= 1:
        raise ValueError('Probability outside 0..1')
    return value


def parse(monitor, prompt_id, raw):
    if monitor == 'llm':
        message = ((raw.get('choices') or [{}])[0].get('message') or {})
        return parse_llm(message.get('content'), P.PROMPTS[prompt_id][1])
    return parse_decision(raw, prompt_id)


def post_json(url, body, key):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.load(response)


# ---------- retries and concurrency ----------

class CallFailed(Exception):
    """A call that failed after all retries (or a non-retryable 4xx). Recorded, retried on the next run."""

    def __init__(self, message, attempts, status=None):
        super().__init__(message)
        self.attempts, self.status = attempts, status


MAX_ATTEMPTS = 6
TRANSIENT = (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout, http.client.HTTPException,
             json.JSONDecodeError, OSError)


def _retry_after(headers):
    try:
        value = float((headers or {}).get('Retry-After'))
        return value if 0 <= value <= 600 else None
    except (TypeError, ValueError):
        return None


def post_with_retry(post, url, body, key, sleep=time.sleep, rng=random, limiter=None, max_attempts=MAX_ATTEMPTS):
    """Exponential backoff with jitter on 429, 5xx, timeouts and connection errors; honours Retry-After.
    Other 4xx fail at once. Returns (response, attempts)."""
    last = None
    for attempt in range(1, max_attempts + 1):
        delay = None
        try:
            return post(url, body, key), attempt
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise CallFailed(f'HTTP {exc.code}', attempt, exc.code)
            if exc.code == 429 and limiter is not None:
                limiter.on_429()
            last, delay = exc, _retry_after(exc.headers)
        except TRANSIENT as exc:
            last = exc
        if attempt == max_attempts:
            break
        if delay is None:
            delay = min(60.0, 2.0 ** attempt) * (0.5 + rng.random())
        sleep(delay)
    raise CallFailed(f'{type(last).__name__}: {last}', max_attempts, getattr(last, 'code', None))


class Limiter:
    """In-flight call limit per monitor. Halves when 429s arrive (at most once per cool-down),
    grows by one after `grow_every` successes in a row."""

    def __init__(self, start, maximum, minimum=1, grow_every=50, cooldown=20.0, clock=time.monotonic):
        self.limit, self.max, self.min = start, maximum, minimum
        self.grow_every, self.cooldown, self.clock = grow_every, cooldown, clock
        self.active, self.streak, self.last_cut = 0, 0, -1e9
        self.cond = threading.Condition()

    def acquire(self):
        with self.cond:
            while self.active >= self.limit:
                self.cond.wait(1.0)
            self.active += 1

    def release(self, ok=True):
        with self.cond:
            self.active -= 1
            if ok:
                self.streak += 1
                if self.streak >= self.grow_every and self.limit < self.max:
                    self.limit += 1; self.streak = 0
            self.cond.notify_all()

    def on_429(self):
        with self.cond:
            self.streak = 0
            now = self.clock()
            if now - self.last_cut >= self.cooldown:
                self.limit = max(self.min, self.limit // 2); self.last_cut = now


# ---------- ledger ----------

class BudgetStop(Exception):
    pass


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


class Ledger:
    """Reserve a worst-case cost before each call; settle to the billed cost.

    The cap is global over every budget*.json ledger in the same run directory (shards), so parallel
    processes can never together exceed it. Thread-safe within a process."""

    def __init__(self, path, cap, limit=MAX_CAP):
        if not Decimal('0') < cap <= limit:
            raise ValueError(f'Cap must be in (0, {limit}]')
        self.path, self.cap = Path(path), cap
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {'billed': '0', 'charged_or_reserved': '0', 'calls': []}
        self.lock = threading.RLock()
        self._others, self._others_at = Decimal(0), -1e9

    def others(self, refresh=15.0):
        now = time.monotonic()
        if now - self._others_at >= refresh:
            total = Decimal(0)
            for p in self.path.parent.glob('budget*.json'):
                if p.resolve() != self.path.resolve():
                    try:
                        total += Decimal(json.loads(p.read_text())['charged_or_reserved'])
                    except (ValueError, KeyError, OSError):
                        pass
            self._others, self._others_at = total, now
        return self._others

    def global_used(self):
        with self.lock:
            return Decimal(self.data['charged_or_reserved']) + self.others(refresh=0)

    def reconcile(self, cache_dir, stale_minutes=30, now=None):
        """Rows left 'reserved' by a dead process (or older than stale_minutes): settle from the cached
        record's reported cost if there is one, else keep them charged at their reservation (max cost)."""
        now = time.time() if now is None else now
        fixed = {'settled': 0, 'kept': 0}
        with self.lock:
            for row in self.data['calls']:
                if row.get('state') != 'reserved':
                    continue
                pid, t = row.get('pid'), row.get('t', 0)
                if pid is not None and int(pid) == os.getpid():
                    continue  # our own in-flight call
                if pid is not None and pid_alive(pid) and now - t < stale_minutes * 60:
                    continue  # another live shard, still recent
                path = Path(cache_dir) / f"{row['key']}.json"
                cost = None
                if path.exists():
                    try:
                        cost = json.loads(path.read_text()).get('cost')
                    except ValueError:
                        cost = None
                if cost is not None:
                    self.settle(row, cost, save=False); row['reconciled'] = True; fixed['settled'] += 1
                else:
                    row['state'] = 'stale_kept'; fixed['kept'] += 1
            self.save()
        return fixed

    def reserve(self, key, amount):
        with self.lock:
            used = Decimal(self.data['charged_or_reserved'])
            if used + self.others() + amount > self.cap:
                raise BudgetStop(f'{used}+{self.others()}+{amount}>{self.cap}')
            row = {'key': key, 'reserve': str(amount), 'state': 'reserved', 'pid': os.getpid(), 't': time.time()}
            self.data['calls'].append(row)
            self.data['charged_or_reserved'] = str(used + amount)
            self.save()
            return row

    def settle(self, row, cost, save=True):
        with self.lock:
            if cost is None:
                row['state'] = 'unbilled_kept_reservation'
            else:
                cost = Decimal(str(cost))
                if not cost.is_finite() or cost < 0:
                    raise ValueError('Invalid cost')
                used = Decimal(self.data['charged_or_reserved'])
                self.data['charged_or_reserved'] = str(used - Decimal(row['reserve']) + cost)
                self.data['billed'] = str(Decimal(self.data['billed']) + cost)
                row.update(state='billed', cost=str(cost))
            if save:
                self.save()

    def mark(self, row, state, **extra):
        with self.lock:
            row.update(state=state, **extra); self.save()

    def save(self):
        with self.lock:
            write_json_atomic(self.path, self.data)


def prices(monitor, fetch=None):
    """Worst-case per-token prices for the endpoint we will use."""
    if fetch is None:
        def fetch(url):
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
    data = fetch(f'https://openrouter.ai/api/v1/models/{MONITORS[monitor]}/endpoints')['data']['endpoints']
    if monitor == 'llm':
        data = [e for e in data if e['provider_name'] == 'OpenAI'] or data
    prompt = max(Decimal(e['pricing']['prompt']) for e in data)
    completion = max(Decimal(e['pricing']['completion']) for e in data)
    if monitor != 'llm' and completion != 0:
        raise ValueError('Decision model with output price')
    return prompt, completion, data


# ---------- run ----------

CONCURRENCY = {'llm': (32, 48), 'luna': (4, 8), 'jev': (4, 8)}  # (start, max) in-flight calls per monitor
PARSE_ATTEMPTS = 2


def task_key(step, job):
    monitor, prompt_id, level = job
    order = option_order(monitor, step['step_id'])
    return cache_key(step['step_id'], step['request_sha256'], monitor, prompt_id, level, order), order


def plan_tasks(steps, jobs, cache_dir):
    """(step, job, key, order) for every pair not yet in the cache, step-major (so a partial run covers
    every combination on the steps it reached)."""
    done = {p.stem for p in Path(cache_dir).glob('*.json')}
    out = []
    for step in steps:
        for job in jobs:
            k, order = task_key(step, job)
            if k not in done:
                out.append((step, job, k, order))
    return out


def score_steps(steps, jobs, cache_dir, ledger, price_table, key=None, post=post_json, max_calls=None, load_episode=None,
                concurrency=None, sleep=time.sleep, rng=None, log_every=200):
    """Run every (step, job) not already cached. Returns the number of new calls (attempted reservations).

    Completed calls are written atomically to cache/<key>.json at once, so a killed process loses only
    in-flight calls. Calls that fail after retries go to failed/<key>.json and are retried on rerun.
    Raises BudgetStop after draining if the global cap stopped new calls."""
    cache_dir = Path(cache_dir); cache_dir.mkdir(parents=True, exist_ok=True)
    failed_dir = cache_dir.parent / 'failed'; failed_dir.mkdir(exist_ok=True)
    unparsed_dir = cache_dir.parent / 'unparsed'; unparsed_dir.mkdir(exist_ok=True)
    load_episode = load_episode or (lambda k: json.loads(episode_path(k).read_text()))
    rng = rng or random.Random()
    concurrency = concurrency or CONCURRENCY
    episodes, ep_lock = {}, threading.Lock()
    for step in steps:  # verify joins before any call
        if step['episode'] not in episodes:
            episodes[step['episode']] = load_episode(step['episode'])
        if request_sha(episodes[step['episode']], step['request_idx']) != step['request_sha256']:
            raise ValueError(f"request_sha256 mismatch for {step['step_id']}")
    tasks = plan_tasks(steps, jobs, cache_dir)
    queues = defaultdict(list)
    for t in tasks:
        queues[t[1][0]].append(t)
    for q in queues.values():
        q.reverse()  # pop() from the end keeps step-major order
    state = {'calls': 0, 'stop': None, 'error': None, 'done': 0}
    lock = threading.Lock()
    limiters = {m: Limiter(*concurrency.get(m, (1, 1))) for m in queues}

    def next_task(monitor):
        with lock:
            if state['stop'] or state['error'] or not queues[monitor]:
                return None
            if max_calls is not None and state['calls'] >= max_calls:
                return None
            state['calls'] += 1
            return queues[monitor].pop()

    def one(task):
        step, (monitor, prompt_id, level), k, order = task
        ep = episodes[step['episode']]
        messages = target_messages(ep, step['request_idx'])
        url, body = build_call(monitor, prompt_id, messages, level, ep['scenario_spec'].get('metadata', {}), order)
        prompt_price, output_price = price_table[monitor]
        reserve = reserve_cost(body, prompt_price, output_price)
        if monitor == 'llm':  # judge_labels reserves 2048 output tokens; we allow more
            reserve += Decimal(LLM_MAX_TOKENS) * output_price * Decimal('1.2')
        attempts_log = []
        for parse_try in range(PARSE_ATTEMPTS):
            row = ledger.reserve(k, reserve)
            try:
                raw, attempts = post_with_retry(post, url, body, key, sleep=sleep, rng=rng, limiter=limiters[monitor])
            except CallFailed as exc:
                ledger.mark(row, 'failed_kept_reservation', error=str(exc)[:200])
                write_json_atomic(failed_dir / f'{k}.json', {'key': k, 'step_id': step['step_id'], 'monitor': monitor,
                                  'prompt': prompt_id, 'level': level, 'error': str(exc)[:500], 'status': exc.status,
                                  'attempts': exc.attempts, 'time': time.time()})
                print('FAILED', monitor, prompt_id, f'L{level}', step['step_id'][-40:], str(exc)[:120], flush=True)
                return False
            cost = (raw.get('usage') or {}).get('cost')
            ledger.settle(row, cost)
            if cost is not None and Decimal(str(cost)) > reserve:
                raise RuntimeError('Reservation exceeded; stopping')
            try:
                score = parse(monitor, prompt_id, raw); error = None
            except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
                score, error = None, str(exc)
            attempts_log.append({'attempts': attempts, 'cost': cost, 'parse_error': error})
            if error is None or parse_try == PARSE_ATTEMPTS - 1:
                break
        record = {'key': k, 'step_id': step['step_id'], 'row': step.get('row'), 'request_sha256': step['request_sha256'],
                  'monitor': monitor, 'model': MONITORS[monitor], 'prompt': prompt_id, 'prompt_sha': P.prompt_sha(prompt_id),
                  'level': level, 'option_order': list(order) if order else None, 'scenario': step.get('scenario'),
                  'request_url': url, 'request_body': body, 'response': raw,
                  'cost': sum(float(a['cost'] or 0) for a in attempts_log), 'attempts': attempts_log, 'score': score}
        if error is not None:
            record['parse_error'] = error
            write_json_atomic(unparsed_dir / f'{k}.json', {'key': k, 'parse_error': error})
        write_json_atomic(cache_dir / f'{k}.json', record)
        (failed_dir / f'{k}.json').unlink(missing_ok=True)
        with lock:
            state['done'] += 1; n = state['done']
        if n <= 20 or n % log_every == 0:
            print('SCORED', n, monitor, prompt_id, f'L{level}', step['step_id'][-40:], score, 'billed', ledger.data['billed'], flush=True)
        return True

    def worker(monitor):
        while True:
            task = next_task(monitor)
            if task is None:
                return
            limiters[monitor].acquire()
            ok = False
            try:
                ok = one(task)
            except BudgetStop as exc:
                with lock:
                    state['stop'] = state['stop'] or exc; state['calls'] -= 1
            except BaseException as exc:  # programming or data error: stop everything, re-raise
                with lock:
                    state['error'] = state['error'] or exc
            finally:
                limiters[monitor].release(ok)

    threads = [threading.Thread(target=worker, args=(m,), daemon=True)
               for m in queues for _ in range(concurrency.get(m, (1, 1))[1])]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if state['error']:
        raise state['error']
    if state['stop']:
        raise state['stop']
    return state['calls']


def collect(cache_dir):
    out = []
    for path in sorted(Path(cache_dir).glob('*.json')):
        r = json.loads(path.read_text())
        out.append({k: r.get(k) for k in ('key', 'step_id', 'row', 'request_sha256', 'monitor', 'model', 'prompt', 'level',
                                          'option_order', 'scenario', 'score', 'parse_error', 'cost')})
    return out


def status(directory, now=None):
    """Progress without API calls: done/failed/unparsed/remaining per monitor x prompt x level, cost, rate, ETA."""
    directory = Path(directory)
    now = time.time() if now is None else now
    meta = json.loads((directory / 'meta.json').read_text())
    jobs = [tuple(j) for j in meta['settings']['jobs']]
    steps = [json.loads(s) for s in (directory / 'steps.jsonl').read_text().splitlines()]
    cache = {p.stem: p for p in (directory / 'cache').glob('*.json')} if (directory / 'cache').exists() else {}
    failed = {p.stem for p in (directory / 'failed').glob('*.json')} if (directory / 'failed').exists() else set()
    unparsed = {p.stem for p in (directory / 'unparsed').glob('*.json')} if (directory / 'unparsed').exists() else set()
    rows = {}
    for job in jobs:
        c = Counter()
        for step in steps:
            k, _ = task_key(step, job)
            c['done' if k in cache else 'failed' if k in failed else 'remaining'] += 1
            c['unparsed'] += k in unparsed
        rows[job] = c
    billed = reserved = Decimal(0)
    for p in directory.glob('budget*.json'):
        d = json.loads(p.read_text()); billed += Decimal(d['billed']); reserved += Decimal(d['charged_or_reserved'])
    recent = sum(1 for p in cache.values() if now - p.stat().st_mtime <= 600)
    rate = recent / 10.0
    remaining = sum(c['remaining'] + c['failed'] for c in rows.values())
    lines = [f"run {directory.name}  steps {len(steps)}  jobs {len(jobs)}", '',
             f"{'monitor':6} {'prompt':10} {'L':>2} {'done':>6} {'failed':>6} {'unparsed':>8} {'remaining':>9}"]
    for (m, pid, lv), c in sorted(rows.items()):
        lines.append(f"{m:6} {pid:10} {lv:>2} {c['done']:>6} {c['failed']:>6} {c['unparsed']:>8} {c['remaining']:>9}")
    tot = Counter()
    for c in rows.values():
        tot.update(c)
    lines += ['', f"total done {tot['done']} failed {tot['failed']} unparsed {tot['unparsed']} remaining {tot['remaining']}",
              f"billed ${billed:.4f}  billed+reserved ${reserved:.4f}  cap ${meta['settings'].get('cap_usd')}",
              f"rate {rate:.1f} calls/min (last 10 min)  ETA " + (f"{remaining / rate / 60:.1f} h" if rate else 'n/a')]
    return '\n'.join(lines), {'rows': {'|'.join(map(str, k)): dict(v) for k, v in rows.items()}, 'billed': str(billed),
                              'reserved': str(reserved), 'rate_per_min': rate, 'remaining': remaining}


def parse_jobs(text):
    out = []
    for item in text.split(','):
        m, p, lv = item.split(':')
        if m not in MONITORS or p not in P.PROMPTS or int(lv) not in P.LEVELS:
            raise ValueError(f'Bad job {item}')
        out.append((m, p, int(lv)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--steps-file', type=Path, help='Score every eligible row of this step table (main run) instead of the E05 sample')
    ap.add_argument('--name', help='Run name (default e06-monitor-main with --steps-file, else e06-monitor-prelim)')
    ap.add_argument('--run', type=Path, help='Resume an existing run directory (same ledger and cache)')
    ap.add_argument('--status', action='store_true', help='With --run: print progress and exit; makes no API calls')
    ap.add_argument('--cap', type=Decimal, default=MAX_CAP)
    ap.add_argument('--n-pos', type=int, default=60)
    ap.add_argument('--n-held', type=int, default=60)
    ap.add_argument('--n-control', type=int, default=30)
    ap.add_argument('--monitors', default='llm,luna,jev')
    ap.add_argument('--prompts', default='forecaster,detector')
    ap.add_argument('--levels', default='1,2,3')
    ap.add_argument('--jobs', help='Explicit monitor:prompt:level list, overrides --monitors/--prompts/--levels')
    ap.add_argument('--scenario', help='Keep only steps of this scenario (comma list)')
    ap.add_argument('--max-calls', type=int)
    ap.add_argument('--max-steps', type=int, help='Score only the first N steps (smoke test)')
    ap.add_argument('--shard', default='0/1', help='i/n: score every n-th step starting at i')
    ap.add_argument('--ledger', default='budget.json', help='Ledger file in the run dir; the cap is global over all budget*.json files')
    ap.add_argument('--stale-minutes', type=float, default=30)
    args = ap.parse_args()
    if args.status:
        if not args.run:
            ap.error('--status needs --run')
        print(status(args.run)[0]); return
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    jobs = parse_jobs(args.jobs) if args.jobs else \
        [(m, p, int(lv)) for lv in args.levels.split(',') for p in args.prompts.split(',') for m in args.monitors.split(',')]
    if args.run:
        directory = args.run.resolve()
        meta = json.loads((directory / 'meta.json').read_text()); meta.update(status='running', error=None)
        if str(args.cap) != meta['settings'].get('cap_usd'):
            meta['settings'].setdefault('cap_history', []).append(meta['settings'].get('cap_usd'))
            meta['settings']['cap_usd'] = str(args.cap)
        write_json_atomic(directory / 'meta.json', meta); run = Run(directory.name, directory, meta)
        steps = [json.loads(s) for s in (directory / 'steps.jsonl').read_text().splitlines()]
        if not args.jobs and args.monitors == 'llm,luna,jev' and args.prompts == 'forecaster,detector' and args.levels == '1,2,3':
            jobs = [tuple(j) for j in meta['settings']['jobs']]
    else:
        name = args.name or ('e06-monitor-main' if args.steps_file else 'e06-monitor-prelim')
        steps = load_steps_file(args.steps_file) if args.steps_file else \
            sample_steps(load_step_table(), args.n_pos, args.n_held, args.n_control)
        if args.scenario:
            keep = set(args.scenario.split(','))
            steps = [s for s in steps if s.get('scenario') in keep]
        if args.max_steps:
            steps = steps[:args.max_steps]
        run = start_run(name, experiment='E06', parents=[str(args.steps_file) if args.steps_file else FIT_RUN],
                        settings={'monitors': MONITORS, 'jobs': jobs, 'cap_usd': str(args.cap), 'steps': len(steps),
                                  'concurrency': CONCURRENCY, 'max_attempts': MAX_ATTEMPTS,
                                  'sample': None if args.steps_file else [args.n_pos, args.n_held, args.n_control]})
        directory = run.dir
        (directory / 'steps.jsonl').write_text(''.join(json.dumps(s) + '\n' for s in steps))
    limit = MAX_CAP_MAIN if 'e06-monitor-main' in directory.name else MAX_CAP
    shard, n_shards = map(int, args.shard.split('/'))
    steps = steps[shard::n_shards]
    ledger = Ledger(directory / args.ledger, args.cap, limit=limit)
    print('RECONCILED', ledger.reconcile(directory / 'cache', args.stale_minutes), flush=True)
    price_table, snapshots = {}, {}
    for m in sorted({j[0] for j in jobs}):
        a, b, snap = prices(m); price_table[m] = (a, b); snapshots[m] = snap
    write_json_atomic(directory / f'model-prices-{"-".join(sorted(snapshots))}.json', snapshots)
    try:
        n = score_steps(steps, jobs, directory / 'cache', ledger, price_table, key=os.environ['OPENROUTER_API_KEY'], max_calls=args.max_calls)
        print('NEW_CALLS', n, 'BILLED', ledger.data['billed'], 'RESERVED', ledger.data['charged_or_reserved'], flush=True)
    except BudgetStop as exc:
        print('BUDGET_STOP', exc, flush=True)
    records = collect(directory / 'cache')
    write_json_atomic(directory / 'scores.json', records)
    print(status(directory)[0], flush=True)
    run.result(scored_calls=len(records)); run.finish()


if __name__ == '__main__':
    main()
