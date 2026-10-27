"""E16: ask Qwen3-32B the self-forecast / self-assessment questions in a side branch.

    python3 experiments/E16-self-report/run.py --out RUN_DIR [--limit 5]

Requires the committed, clean plan.json. Writes RUN_DIR/raw.jsonl (one line per prompt,
all samples) and RUN_DIR/spend.json. Resumable: prompts already in raw.jsonl are skipped.
"""
import argparse
import asyncio
import copy
import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD_ROOT = Path('/Users/leo/collusion-research')  # read-only: saved test episodes and API key
PLAN = HERE / 'plan.json'
CAP_USD = 2.0


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_episode(rel, expected_sha):
    run, name = rel.split('/', 1)
    for root in (ROOT, OLD_ROOT):
        path = root / 'runs' / run / 'episodes' / name
        if path.exists():
            raw = path.read_bytes()
            if sha(raw) != expected_sha:
                raise ValueError(f'Episode hash mismatch: {rel}')
            return json.loads(raw)
    raise FileNotFoundError(rel)


def build_prompts(plan):
    prompts = []
    for c in plan['part1_calls']:
        ep = load_episode(c['episode'], c['episode_sha256'])
        request = ep['requests'][c['request_idx']]['request']
        if sha(json.dumps(request, ensure_ascii=False, separators=(',', ':')).encode()) != c['request_sha256']:
            raise ValueError(f"Request hash mismatch: {c['call_id']}")
        text = plan['prompts']['part1_appended_user_message'].replace('<FIELD>', c['field'])
        body = copy.deepcopy(request)
        body['messages'] = body['messages'] + [{'role': 'user', 'content': text}]
        prompts.append({'key': 'p1|' + c['call_id'], 'part': 1, 'call': c, 'body': body})
    for c in plan['part2_calls']:
        ep = load_episode(c['episode'], c['episode_sha256'])
        request = ep['requests'][c['request_idx']]['request']
        history = ep['histories']['target']
        n = len(request['messages'])
        if history[:n] != request['messages'] or history[n]['role'] != 'assistant':
            raise ValueError(f"History does not extend the request: {c['call_id']}")
        reply = history[n]
        ids = {t['id'] for t in reply.get('tool_calls') or []}
        tools = []
        for m in history[n + 1:]:
            if m['role'] != 'tool' or m.get('tool_call_id') not in ids:
                break
            tools.append(m)
        if len(tools) != len(ids):
            raise ValueError(f"Missing tool results: {c['call_id']}")
        body = copy.deepcopy(request)
        body['messages'] = body['messages'] + [reply] + tools + [
            {'role': 'user', 'content': plan['prompts']['part2_appended_user_message']}]
        prompts.append({'key': f"p2|{c['group']}|{c['call_id']}", 'part': 2, 'call': c, 'body': body,
                        'reply': reply})
    return prompts


def parse(text):
    if not isinstance(text, str):
        return None
    words = re.sub(r'[^a-z ]', ' ', text.lower()).split()
    return words[0] if words and words[0] in ('yes', 'no') else None


def first_token_yes_no(choice):
    lp = (choice.get('logprobs') or {}).get('content') or []
    if not lp:
        return None
    top = lp[0].get('top_logprobs') or []
    py = sum(math.exp(t['logprob']) for t in top if t['token'].strip().lower() == 'yes')
    pn = sum(math.exp(t['logprob']) for t in top if t['token'].strip().lower() == 'no')
    return {'token': lp[0].get('token'), 'p_yes': py, 'p_no': pn, 'n_top': len(top)}


async def one(client, sem, body, overrides):
    payload = {**body, **overrides}
    async with sem:
        for attempt in range(5):
            try:
                resp = await client.chat.completions.create(**payload)
                return resp.model_dump()
            except Exception as exc:  # retry transient provider errors
                last = exc
                await asyncio.sleep(2 ** attempt)
        return {'error': f'{type(last).__name__}: {last}'}


async def main(a):
    rel = PLAN.relative_to(ROOT)
    dirty = subprocess.run(['git', 'status', '--porcelain', '--', str(rel)], cwd=ROOT, capture_output=True, text=True)
    tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', str(rel)], cwd=ROOT, capture_output=True)
    if tracked.returncode or dirty.stdout.strip():
        raise ValueError('plan.json must be committed and clean before any API call')
    plan = json.loads(PLAN.read_text())
    prompts = build_prompts(plan)
    if a.limit:
        prompts = prompts[:a.limit]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    raw_path = out / 'raw.jsonl'
    done = set()
    spent = 0.0
    if raw_path.exists():
        for line in raw_path.read_text().splitlines():
            row = json.loads(line)
            done.add(row['key'])
            spent += row['cost_usd']
    from openai import AsyncOpenAI
    key = next(l.split('=', 1)[1].strip().strip('"\'') for l in (OLD_ROOT / '.env').read_text().splitlines()
               if l.startswith('OPENROUTER_API_KEY='))
    client = AsyncOpenAI(api_key=key, base_url='https://openrouter.ai/api/v1', max_retries=0, timeout=90)
    overrides = plan['model']['overridden']
    samples = plan['scoring']['samples_per_prompt']
    sem = asyncio.Semaphore(a.parallel)
    todo = [p for p in prompts if p['key'] not in done]
    print(f'{len(todo)} prompts to run ({len(done)} done, ${spent:.4f} spent)')
    with raw_path.open('a') as fh:
        for start in range(0, len(todo), a.parallel):
            if spent > CAP_USD:
                raise SystemExit(f'Spend cap reached: ${spent:.4f}')
            batch = todo[start:start + a.parallel]
            results = await asyncio.gather(*(asyncio.gather(*(one(client, sem, p['body'], overrides)
                                                               for _ in range(samples))) for p in batch))
            for p, resps in zip(batch, results):
                outs = []
                cost = 0.0
                for r in resps:
                    if 'error' in r:
                        outs.append({'error': r['error']})
                        continue
                    ch = (r.get('choices') or [{}])[0]
                    msg = ch.get('message') or {}
                    usage = r.get('usage') or {}
                    cost += float(usage.get('cost') or 0)
                    outs.append({'content': msg.get('content'), 'tool_calls': bool(msg.get('tool_calls')),
                                 'finish_reason': ch.get('finish_reason'), 'parsed': parse(msg.get('content')),
                                 'first_token': first_token_yes_no(ch), 'provider': r.get('provider'),
                                 'prompt_tokens': usage.get('prompt_tokens'),
                                 'completion_tokens': usage.get('completion_tokens')})
                spent += cost
                fh.write(json.dumps({'key': p['key'], 'part': p['part'], 'call': p['call'], 'cost_usd': cost,
                                     'samples': outs}, ensure_ascii=False) + '\n')
            fh.flush()
            print(f'{start + len(batch)}/{len(todo)} ${spent:.4f}', flush=True)
    await client.close()
    (out / 'spend.json').write_text(json.dumps({'api_usd': spent, 'gpu_usd': 0.0, 'cap_usd': CAP_USD,
                                                'source': 'sum of OpenRouter usage.cost over all requests'}, indent=1) + '\n')
    print(f'Total ${spent:.4f}')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True)
    p.add_argument('--limit', type=int)
    p.add_argument('--parallel', type=int, default=8)
    asyncio.run(main(p.parse_args()))
