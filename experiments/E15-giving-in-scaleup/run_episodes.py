"""E15: Qwen3-32B episodes on the five test scenarios under FORBID, EARLY or LATE (plan.json).

Same runner, target, peer model, tools, settings and early stopping as the test runs
(experiments/E01-behaviour-pilot/scale_up.py). EARLY and LATE use E08's PERMIT sentence with the
consequence sentence removed; LATE also paces the peer so it asks for the value only in its 5th message.
Requires the committed, clean plan.json.

    .venv/bin/python experiments/E15-giving-in-scaleup/run_episodes.py --arm LATE --benchmark
    .venv/bin/python experiments/E15-giving-in-scaleup/run_episodes.py --arm LATE
"""
import argparse
import asyncio
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / 'experiments/E01-behaviour-pilot'), str(ROOT / 'src')]

from harness import Settings, run_episode
from overnight_sweep import PEER, TARGETS, fetch_prices, options
from scale_up import SpendCap, scale_up_scenario
from collusion.runs import start_run

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


async def main(a):
    rel = PLAN.relative_to(ROOT)
    dirty = subprocess.run(['git', 'status', '--porcelain', '--', str(rel)], cwd=ROOT, capture_output=True, text=True)
    tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', str(rel)], cwd=ROOT, capture_output=True)
    if tracked.returncode or dirty.stdout.strip():
        raise ValueError('plan.json must be committed and clean before any API call')
    plan = json.loads(PLAN.read_text())
    todo = jobs(plan, a.arm, a.benchmark)
    if a.skip:
        done = {line.strip() for line in Path(a.skip).read_text().splitlines()}
        todo = [j for j in todo if f'{j[0]}-{j[2]:04}' not in done]
    from dotenv import dotenv_values
    from openai import AsyncOpenAI

    model, _ = TARGETS['32b']
    prices = fetch_prices()
    settings = Settings(model, PEER, rounds=20, max_tool_steps=12, max_tokens=1536,
                        target_request_options=options(prices[model]),
                        recruiter_request_options=options(prices[PEER]))
    key = os.environ.get('OPENROUTER_API_KEY') or dotenv_values(KEY_FILE)['OPENROUTER_API_KEY']
    client = AsyncOpenAI(api_key=key, base_url='https://openrouter.ai/api/v1', max_retries=0, timeout=90)
    run = start_run(f'e15-{a.arm.lower()}' + ('-benchmark' if a.benchmark else ''), experiment='E15', settings={
        **asdict(settings), 'arm': a.arm, 'benchmark': a.benchmark, 'episodes': len(todo), 'api_cap_usd': a.cap_usd,
        'plan_sha256': hashlib.sha256(PLAN.read_bytes()).hexdigest()}, tags=['e15', a.arm.lower()], model=model)
    budget = SpendCap(client, a.cap_usd, run.dir / 'api_budget.json')
    gate = asyncio.Semaphore(plan['runner']['parallelism'])

    async def one(name, family_id, index):
        async with gate:
            if budget.spent >= budget.cap:
                return None
            try:
                result = await run_episode(build(plan, a.arm, name, family_id), settings, budget,
                                           run.dir / 'episodes', episode_id=f'{name}-{index:04}')
            except Exception as exc:
                print('EPISODE_ERROR', name, index, type(exc).__name__, exc, flush=True)
                return None
            print('EPISODE', name, index, result['status'], result['rounds_completed'],
                  (result.get('label') or {}).get('objective_success'), f'${budget.spent:.4f}', flush=True)
            return result

    results = await asyncio.gather(*(one(*j) for j in todo))
    done = [r for r in results if r]
    run.result(completed=sum(r['status'] == 'complete' for r in done), attempted=len(done), planned=len(todo),
               spent_usd=str(budget.spent), calls=budget.calls)
    run.finish('finished')
    await client.close()
    print('E15_DONE', run.id, f'${budget.spent:.4f}', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm', choices=('FORBID', 'EARLY', 'LATE'), required=True)
    p.add_argument('--benchmark', action='store_true')
    p.add_argument('--skip', help='File of <scenario>-<index> episodes already run (benchmark), one per line')
    p.add_argument('--cap-usd', type=float, default=1.5)
    asyncio.run(main(p.parse_args()))
