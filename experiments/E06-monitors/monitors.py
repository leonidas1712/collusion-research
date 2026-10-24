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
from collections import defaultdict
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
MAX_CAP = Decimal('2.50')
LLM_MAX_TOKENS = 3000


# ---------- step table ----------

def load_step_table(fit_run=FIT_RUN):
    """E05 rows restricted to the main variant's eligible set, with seed-42 fold and probe scores."""
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

def build_call(monitor, prompt_id, messages, level):
    model = MONITORS[monitor]
    if monitor == 'llm':
        body = {'model': model, 'messages': [{'role': 'user', 'content': P.llm_prompt(prompt_id, messages, level)}],
                'max_completion_tokens': LLM_MAX_TOKENS, 'reasoning': {'effort': 'low'},
                'provider': {'order': ['OpenAI'], 'allow_fallbacks': False,
                             'max_price': {'prompt': 0.05, 'completion': 0.40}}}
        return CHAT_URL, body
    return DECISION_URL, P.decision_payload(model, prompt_id, messages, level)


def cache_key(step_id, request_sha256, monitor, prompt_id, level):
    raw = json.dumps([step_id, request_sha256, MONITORS[monitor], prompt_id, P.prompt_sha(prompt_id), level])
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


# ---------- ledger ----------

class BudgetStop(Exception):
    pass


class Ledger:
    """Reserve a worst-case cost before each call; settle to the billed cost. Never exceed the cap."""

    def __init__(self, path, cap):
        if not Decimal('0') < cap <= MAX_CAP:
            raise ValueError(f'Cap must be in (0, {MAX_CAP}]')
        self.path, self.cap = Path(path), cap
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {'billed': '0', 'charged_or_reserved': '0', 'calls': []}

    def reserve(self, key, amount):
        used = Decimal(self.data['charged_or_reserved'])
        if used + amount > self.cap:
            raise BudgetStop(f'{used}+{amount}>{self.cap}')
        row = {'key': key, 'reserve': str(amount), 'state': 'reserved'}
        self.data['calls'].append(row)
        self.data['charged_or_reserved'] = str(used + amount)
        self.save()
        return row

    def settle(self, row, cost):
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
        self.save()

    def save(self):
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

def score_steps(steps, jobs, cache_dir, ledger, price_table, key=None, post=post_json, max_calls=None, load_episode=None):
    """jobs: list of (monitor, prompt_id, level). Returns number of new network calls."""
    cache_dir = Path(cache_dir); cache_dir.mkdir(parents=True, exist_ok=True)
    load_episode = load_episode or (lambda k: json.loads(episode_path(k).read_text()))
    episodes = {}
    calls = 0
    for step in steps:
        if step['episode'] not in episodes:
            episodes[step['episode']] = load_episode(step['episode'])
        ep = episodes[step['episode']]
        if request_sha(ep, step['request_idx']) != step['request_sha256']:
            raise ValueError(f"request_sha256 mismatch for {step['step_id']}")
        messages = target_messages(ep, step['request_idx'])
        for monitor, prompt_id, level in jobs:
            k = cache_key(step['step_id'], step['request_sha256'], monitor, prompt_id, level)
            path = cache_dir / f'{k}.json'
            if path.exists():
                continue
            if max_calls is not None and calls >= max_calls:
                return calls
            url, body = build_call(monitor, prompt_id, messages, level)
            prompt_price, output_price = price_table[monitor]
            reserve = reserve_cost(body, prompt_price, output_price)
            if monitor == 'llm':  # judge_labels reserves 2048 output tokens; we allow more
                reserve += Decimal(LLM_MAX_TOKENS) * output_price * Decimal('1.2')
            row = ledger.reserve(k, reserve)
            calls += 1
            try:
                raw = post(url, body, key)
            except Exception as exc:
                row['error_type'] = type(exc).__name__; ledger.save()
                raise
            cost = (raw.get('usage') or {}).get('cost')
            ledger.settle(row, cost)
            record = {'key': k, 'step_id': step['step_id'], 'row': step.get('row'), 'request_sha256': step['request_sha256'],
                      'monitor': monitor, 'model': MONITORS[monitor], 'prompt': prompt_id, 'prompt_sha': P.prompt_sha(prompt_id),
                      'level': level, 'request_url': url, 'request_body': body, 'response': raw, 'cost': cost}
            try:
                record['score'] = parse(monitor, prompt_id, raw)
            except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
                record['parse_error'] = str(exc)
            write_json_atomic(path, record)
            print('SCORED', monitor, prompt_id, f'L{level}', step['step_id'][-40:], record.get('score'), ledger.data['billed'], flush=True)
            if cost is not None and Decimal(str(cost)) > reserve:
                raise RuntimeError('Reservation exceeded; stopping')
    return calls


def collect(cache_dir):
    out = []
    for path in sorted(Path(cache_dir).glob('*.json')):
        r = json.loads(path.read_text())
        out.append({k: r.get(k) for k in ('key', 'step_id', 'row', 'request_sha256', 'monitor', 'model', 'prompt', 'level', 'score', 'parse_error', 'cost')})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', type=Path, help='Resume an existing run directory (same ledger and cache)')
    ap.add_argument('--cap', type=Decimal, default=MAX_CAP)
    ap.add_argument('--n-pos', type=int, default=60)
    ap.add_argument('--n-held', type=int, default=60)
    ap.add_argument('--n-control', type=int, default=30)
    ap.add_argument('--monitors', default='llm,luna,jev')
    ap.add_argument('--prompts', default='forecaster,detector')
    ap.add_argument('--levels', default='1,2,3')
    ap.add_argument('--max-calls', type=int)
    ap.add_argument('--max-steps', type=int, help='Score only the first N sampled steps (smoke test)')
    ap.add_argument('--shard', default='0/1', help='i/n: score every n-th sampled step starting at i')
    ap.add_argument('--ledger', default='budget.json', help='Ledger file in the run dir; parallel processes use separate ledgers whose caps sum to at most MAX_CAP')
    args = ap.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    jobs = [(m, p, int(lv)) for lv in args.levels.split(',') for p in args.prompts.split(',') for m in args.monitors.split(',')]
    if args.run:
        directory = args.run.resolve()
        meta = json.loads((directory / 'meta.json').read_text()); meta.update(status='running', error=None)
        write_json_atomic(directory / 'meta.json', meta); run = Run(directory.name, directory, meta)
        steps = [json.loads(s) for s in (directory / 'steps.jsonl').read_text().splitlines()]
    else:
        run = start_run('e06-monitor-prelim', experiment='E06', parents=[FIT_RUN],
                        settings={'monitors': MONITORS, 'jobs': jobs, 'cap_usd': str(args.cap),
                                  'sample': [args.n_pos, args.n_held, args.n_control]})
        directory = run.dir
        steps = sample_steps(load_step_table(), args.n_pos, args.n_held, args.n_control)
        (directory / 'steps.jsonl').write_text(''.join(json.dumps(s) + '\n' for s in steps))
    if args.max_steps:
        steps = steps[:args.max_steps]
    shard, n_shards = map(int, args.shard.split('/'))
    steps = steps[shard::n_shards]
    ledger = Ledger(directory / args.ledger, args.cap)
    price_table, snapshots = {}, {}
    for m in {j[0] for j in jobs}:
        a, b, snap = prices(m); price_table[m] = (a, b); snapshots[m] = snap
    write_json_atomic(directory / f'model-prices-{"-".join(sorted(snapshots))}.json', snapshots)
    try:
        n = score_steps(steps, jobs, directory / 'cache', ledger, price_table, key=os.environ['OPENROUTER_API_KEY'], max_calls=args.max_calls)
        print('NEW_CALLS', n, 'BILLED', ledger.data['billed'], 'RESERVED', ledger.data['charged_or_reserved'], flush=True)
    except BudgetStop as exc:
        print('BUDGET_STOP', exc, flush=True)
    records = collect(directory / 'cache')
    write_json_atomic(directory / 'scores.json', records)
    run.result(scored_calls=len(records)); run.finish()


if __name__ == '__main__':
    main()
