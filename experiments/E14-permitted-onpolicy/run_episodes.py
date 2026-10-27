"""E14: on-policy PERMIT episodes for one Qwen test scenario.

Same runner, peer, tools, settings and early stopping as the scenario's test run
(experiments/E01-behaviour-pilot/scale_up.py); only the operator-rule sentence is
replaced with E08's PERMIT text. Requires the committed, clean plan.json.

    .venv/bin/python experiments/E14-permitted-onpolicy/run_episodes.py [--count N]
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


def permit_scenario(plan, family_id):
    scenario = scale_up_scenario('spray', 'consequence', 'recruiting', str(family_id), None, None,
                                 plan['scenario'], 1)
    forbid, permit = plan['rule_texts']['FORBID'], plan['rule_texts']['PERMIT']
    if scenario.target_system.count(forbid) != 1:
        raise ValueError('FORBID rule not found exactly once')
    return replace(scenario, target_system=scenario.target_system.replace(forbid, permit, 1))


async def main(a):
    rel = PLAN.relative_to(ROOT)
    dirty = subprocess.run(['git', 'status', '--porcelain', '--', str(rel)], cwd=ROOT, capture_output=True, text=True)
    tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', str(rel)], cwd=ROOT, capture_output=True)
    if tracked.returncode or dirty.stdout.strip():
        raise ValueError('plan.json must be committed and clean before any API call')
    plan = json.loads(PLAN.read_text())
    ep = plan['episodes']
    count = a.count or ep['count']
    from dotenv import dotenv_values
    from openai import AsyncOpenAI

    model, _ = TARGETS[ep['target']]
    prices = fetch_prices()
    settings = Settings(model, PEER, rounds=20, max_tool_steps=12, max_tokens=1536,
                        target_request_options=options(prices[model]),
                        recruiter_request_options=options(prices[PEER]))
    key = os.environ.get('OPENROUTER_API_KEY') or dotenv_values(KEY_FILE)['OPENROUTER_API_KEY']
    client = AsyncOpenAI(api_key=key, base_url='https://openrouter.ai/api/v1', max_retries=0, timeout=90)
    run = start_run(a.name, experiment='E14', settings={
        **asdict(settings), 'scenario': plan['scenario'], 'condition': 'recruiting-permit',
        'family_start': ep['family_start'] + a.offset, 'count': count, 'api_cap_usd': a.cap_usd,
        'plan_sha256': hashlib.sha256(PLAN.read_bytes()).hexdigest()},
        tags=['permit', 'on-policy'], model=model)
    budget = SpendCap(client, a.cap_usd, run.dir / 'api_budget.json')
    gate = asyncio.Semaphore(ep['parallelism'])

    async def one(index):
        async with gate:
            if budget.spent >= budget.cap:
                return None
            family_id = ep['family_start'] + a.offset + index
            try:
                result = await run_episode(permit_scenario(plan, family_id), settings, budget,
                                           run.dir / 'episodes', episode_id=f'episode-{a.offset + index + 1:04}')
            except Exception as exc:
                print('EPISODE_ERROR', index + 1, type(exc).__name__, exc, flush=True)
                return None
            print('EPISODE', index + 1, result['status'], result['rounds_completed'],
                  (result.get('label') or {}).get('objective_success'), f'${budget.spent:.4f}', flush=True)
            return result

    results = await asyncio.gather(*(one(i) for i in range(count)))
    done = [r for r in results if r]
    run.result(completed=sum(r['status'] == 'complete' for r in done), attempted=len(done), planned=count,
               spent_usd=str(budget.spent), calls=budget.calls)
    run.finish('finished')
    await client.close()
    print('E14_EPISODES_DONE', run.id, f'${budget.spent:.4f}', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--count', type=int, default=0)
    p.add_argument('--offset', type=int, default=0, help='Episode index offset (benchmark is 0..k-1)')
    p.add_argument('--cap-usd', type=float, default=0.6)
    p.add_argument('--name', default='e14-permitted-onpolicy-episodes')
    asyncio.run(main(p.parse_args()))
