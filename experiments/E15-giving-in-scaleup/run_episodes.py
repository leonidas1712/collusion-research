"""E15: Qwen3-32B episodes on the five test scenarios under FORBID, EARLY or LATE (plan.json).

Same runner, target, peer model, tools, settings and early stopping as the test runs
(experiments/E01-behaviour-pilot/scale_up.py). EARLY and LATE use E08's PERMIT sentence with the
consequence sentence removed; LATE also paces the peer so it asks for the value only in its 5th message.
Requires the committed, clean plan.json.

Resumable: episodes already complete in any earlier E15 run of the arm are skipped by episode ID
(fixed by seed). Episodes that stopped on an API error (rate limit, 5xx, connection) are retried in
waves with backoff and lower concurrency; episodes that stopped for a model-side reason are final and
reported, as in the paper. Progress, retries and spend are written to progress.json after every episode.

    .venv/bin/python experiments/E15-giving-in-scaleup/run_episodes.py --arm LATE --benchmark
    .venv/bin/python experiments/E15-giving-in-scaleup/run_episodes.py --arm LATE
"""
import argparse
import asyncio
from dataclasses import asdict, replace
import hashlib
import json
import os
import random
import time
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / 'experiments/E01-behaviour-pilot'), str(ROOT / 'src')]

from harness import Settings, run_episode
from overnight_sweep import PEER, TARGETS, fetch_prices, options
from scale_up import SpendCap, scale_up_scenario
from collusion.runs import start_run, write_json_atomic

PLAN = HERE / 'plan.json'
KEY_FILE = Path('/Users/leo/collusion-research/.env')  # read-only: API key only
SPLIT = ' Your current access does not include'


def build(plan, arm, scenario_name, family_id):
    scenario = scale_up_scenario('spray', 'consequence', 'recruiting', str(family_id), None, None, scenario_name, 1)
    if arm == 'FORBID':
        return scenario
    rules = plan['rule_texts_by_scenario'][scenario_name]
    consequence = plan['consequence_sentences_by_scenario'][scenario_name]
    system = scenario.target_system
    if system.count(rules['FORBID']) != 1 or not system.endswith(consequence):
        raise ValueError(f'Unexpected target system prompt: {scenario_name}')
    system = system.replace(rules['FORBID'], rules['PERMIT'], 1).removesuffix(consequence)
    peer = scenario.recruiter_system
    if arm == 'LATE':
        meta = scenario.metadata
        slots = {**meta['tactic_slots'], 'secret_key': meta['secret_key'], 'private_path': meta['private_path']}
        if peer.count(SPLIT) != 1:
            raise ValueError(f'Unexpected peer prompt: {scenario_name}')
        head, tail = peer.split(SPLIT)
        pacing = plan['late_peer_prompt']['pacing_block'].format(**slots)
        peer = f'{head} {pacing} From your fifth message on: {SPLIT.strip()}{tail}'
    return replace(scenario, target_system=system, recruiter_system=peer)


def jobs(plan, arm, benchmark):
    spec = plan['arms'][arm]
    scenarios = spec.get('scenarios', plan['scenarios'])
    out = []
    for si, name in enumerate(plan['scenarios']):
        if name not in scenarios:
            continue
        for i in range(1, spec['per_scenario'] + 1):
            out.append((name, spec['family_base'] + 100 * si + i, i))
    if benchmark:
        out = [next(j for j in out if j[0] == scenarios[k] and j[2] == 1) for k in range(plan['benchmark']['episodes_per_arm'])]
    return out


def prior_state(arm):
    """Latest outcome per episode ID across earlier E15 runs of this arm."""
    state = {}
    for path in sorted(ROOT.glob(f'runs/*-e15-{arm.lower()}*/episodes/*.json')):
        name = path.name.removesuffix('.json').removesuffix('.partial')
        ep = json.loads(path.read_text())
        reason = str(ep.get('stop_reason'))
        interrupted = reason == 'None'  # the process stopped mid-episode
        outcome = 'complete' if ep.get('status') == 'complete' else 'transient' if reason.startswith('api_error') or interrupted else 'final'
        if state.get(name, {}).get('outcome') != 'complete':
            state[name] = {'outcome': outcome, 'reason': reason, 'path': str(path.relative_to(ROOT))}
    return state


def api_errors(ep_dir, name):
    path = ep_dir / f'{name}.json'
    path = path if path.exists() else ep_dir / f'{name}.partial.json'
    if not path.exists():
        return 0
    return sum(1 for r in json.loads(path.read_text()).get('requests', []) if r.get('error'))


async def main(a):
    rel = PLAN.relative_to(ROOT)
    dirty = subprocess.run(['git', 'status', '--porcelain', '--', str(rel)], cwd=ROOT, capture_output=True, text=True)
    tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', str(rel)], cwd=ROOT, capture_output=True)
    if tracked.returncode or dirty.stdout.strip():
        raise ValueError('plan.json must be committed and clean before any API call')
    plan = json.loads(PLAN.read_text())
    todo = jobs(plan, a.arm, a.benchmark)
    state = prior_state(a.arm)
    final = {k: v for k, v in state.items() if v['outcome'] in ('complete', 'final')}
    todo = [j for j in todo if f'{j[0]}-{j[2]:04}' not in final]
    print('RESUME', a.arm, 'already final:', len(final), 'to run:', len(todo), flush=True)
    from dotenv import dotenv_values
    from openai import AsyncOpenAI

    model, _ = TARGETS['32b']
    prices = fetch_prices()
    settings = Settings(model, PEER, rounds=20, max_tool_steps=12, max_tokens=1536,
                        target_request_options=options(prices[model]),
                        recruiter_request_options=options(prices[PEER]),
                        api_retry_attempts=10, api_retry_max_delay=60)
    key = os.environ.get('OPENROUTER_API_KEY') or dotenv_values(KEY_FILE)['OPENROUTER_API_KEY']
    client = AsyncOpenAI(api_key=key, base_url='https://openrouter.ai/api/v1', max_retries=0, timeout=90)
    run = start_run(f'e15-{a.arm.lower()}' + ('-benchmark' if a.benchmark else ''), experiment='E15', settings={
        **asdict(settings), 'arm': a.arm, 'benchmark': a.benchmark, 'episodes': len(todo), 'api_cap_usd': a.cap_usd,
        'plan_sha256': hashlib.sha256(PLAN.read_bytes()).hexdigest()}, tags=['e15', a.arm.lower()], model=model)
    budget = SpendCap(client, a.cap_usd, run.dir / 'api_budget.json')
    ep_dir = run.dir / 'episodes'
    log = {'arm': a.arm, 'already_final_before_run': len(final), 'waves': [], 'episodes': {}}

    def save_progress():
        log.update(spent_usd=str(budget.spent), calls=budget.calls,
                   retried_requests=sum(e['api_error_requests'] for e in log['episodes'].values()))
        write_json_atomic(run.dir / 'progress.json', log)

    async def one(gate, name, family_id, index):
        async with gate:
            if budget.spent >= budget.cap:
                return 'cap'
            eid = f'{name}-{index:04}'
            try:
                result = await run_episode(build(plan, a.arm, name, family_id), settings, budget, ep_dir, episode_id=eid)
                status, reason = result['status'], str(result.get('stop_reason'))
            except Exception as exc:
                status, reason = 'error', f'{type(exc).__name__}: {exc}'
            outcome = 'complete' if status == 'complete' else 'transient' if (reason.startswith('api_error') or status == 'error') else 'final'
            log['episodes'][eid] = {'outcome': outcome, 'reason': reason, 'family_id': family_id,
                                    'api_error_requests': log['episodes'].get(eid, {}).get('api_error_requests', 0) + api_errors(ep_dir, eid)}
            save_progress()
            print('EPISODE', eid, outcome, reason, f'${budget.spent:.4f}', flush=True)
            return outcome

    concurrency = a.concurrency
    for wave in range(a.waves):
        if not todo:
            break
        gate = asyncio.Semaphore(concurrency)
        outcomes = await asyncio.gather(*(one(gate, *j) for j in todo))
        failed = [j for j, o in zip(todo, outcomes) if o == 'transient']
        log['waves'].append({'wave': wave + 1, 'ran': len(todo), 'transient_failures': len(failed), 'concurrency': concurrency})
        save_progress()
        if 'cap' in outcomes:
            print('API cap reached; stopping', flush=True)
            break
        for j in failed:  # a retried episode restarts cleanly in this run's folder
            for suffix in ('.json', '.partial.json'):
                stale = ep_dir / f'{j[0]}-{j[2]:04}{suffix}'
                if stale.exists():
                    stale.rename(stale.with_name(stale.name + f'.wave{wave + 1}-failed'))
        todo = failed
        if todo:
            if len(failed) > len(outcomes) / 4:
                concurrency = max(1, concurrency // 2)
            pause = min(900, 60 * 2 ** wave) + random.uniform(0, 30)
            print(f'WAVE {wave + 1}: {len(failed)} transient failures; waiting {pause:.0f}s, concurrency {concurrency}', flush=True)
            await asyncio.sleep(pause)
    log['failed_after_all_retries'] = [f'{j[0]}-{j[2]:04}' for j in todo]
    save_progress()
    done = [e for e in log['episodes'].values()]
    run.result(completed=sum(e['outcome'] == 'complete' for e in done), final_incomplete=sum(e['outcome'] == 'final' for e in done),
               failed_after_retries=len(todo), spent_usd=str(budget.spent), calls=budget.calls)
    run.finish('finished')
    await client.close()
    print('E15_DONE', run.id, f'${budget.spent:.4f}', 'failed after retries:', len(todo), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm', choices=('FORBID', 'EARLY', 'LATE'), required=True)
    p.add_argument('--benchmark', action='store_true')
    p.add_argument('--concurrency', type=int, default=3)
    p.add_argument('--waves', type=int, default=6)
    p.add_argument('--cap-usd', type=float, default=1.5)
    asyncio.run(main(p.parse_args()))
