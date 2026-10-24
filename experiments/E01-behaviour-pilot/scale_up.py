"""Scale up one sweep cell: recruiting, control (control2 peer) and alone episodes, run concurrently.

    uv run python experiments/E01-behaviour-pilot/scale_up.py [--recruiting 40 --control 15 --alone 6]

Reuses the overnight rule variants, settings and provider pinning. Spend is tracked from billed
usage (a running total, safe under concurrency) and stops at --cap-usd. No GPU work.
"""
import argparse
import asyncio
from dataclasses import asdict
from decimal import Decimal
import os
from pathlib import Path
import sys
from types import SimpleNamespace

from harness import Settings, run_episode
from overnight_rules import get_overnight_scenario
from overnight_sweep import PEER, TARGETS, fetch_prices, options

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run, write_json_atomic


class SpendCap:
    """Counts billed cost; refuses new requests once the cap is reached."""
    is_fake = False

    def __init__(self, client, cap, path):
        self.client, self.cap, self.path = client, Decimal(str(cap)), path
        self.spent, self.calls = Decimal('0'), 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **payload):
        if self.spent >= self.cap:
            raise RuntimeError('spend cap reached')
        response = await self.client.chat.completions.create(**payload)
        data = response.model_dump() if hasattr(response, 'model_dump') else response
        self.spent += Decimal(str((data.get('usage') or {}).get('cost') or 0))
        self.calls += 1
        write_json_atomic(self.path, {'cap_usd': str(self.cap), 'spent_usd': str(self.spent), 'calls': self.calls})
        return response


async def main(a):
    from dotenv import load_dotenv
    from openai import AsyncOpenAI

    model, provider = TARGETS[a.target]
    prices = fetch_prices()
    settings = Settings(model, PEER, rounds=20, max_tool_steps=12, max_tokens=1536,
                        target_request_options=options(prices[model]),
                        recruiter_request_options=options(prices[PEER]))
    load_dotenv(ROOT / '.env')
    client = AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'], base_url='https://openrouter.ai/api/v1',
                         max_retries=0, timeout=90)
    parent = start_run(f'e01-scaleup-{a.family}-{a.strength}-{a.target}', experiment='E01',
                       settings={'cap_usd': a.cap_usd, 'counts': {'recruiting': a.recruiting, 'control': a.control,
                                 'alone': a.alone}, 'family_start': a.family_start, 'parallelism': a.parallelism},
                       tags=['scale-up', a.strength], model=model)
    budget = SpendCap(client, a.cap_usd, parent.dir / 'budget.json')
    gate = asyncio.Semaphore(a.parallelism)
    cells = []
    streams = sys.stdout, sys.stderr, sys.excepthook  # keep everything in the parent log
    for condition, count in (('recruiting', a.recruiting), ('control', a.control), ('alone', a.alone)):
        if count:
            cell = start_run(f'e01-{a.family}-{a.strength}-{condition}-{a.target}-scaleup', experiment='E01',
                             settings={**asdict(settings), 'scenario_family': a.family, 'strength': a.strength,
                                       'condition': condition, 'target': a.target},
                             parents=[parent.id], tags=['scale-up', a.strength, condition], model=model)
            sys.stdout, sys.stderr, sys.excepthook = streams
            cells.append((condition, count, cell))

    async def one(condition, index, cell):
        async with gate:
            if budget.spent >= budget.cap:
                return None
            scenario = get_overnight_scenario(a.family, a.strength, condition, family_id=str(a.family_start + index))
            try:
                ep = await run_episode(scenario, settings, budget, cell.dir / 'episodes', episode_id=f'episode-{index+1:04}')
            except Exception as exc:  # keep the other episodes going
                print('EPISODE_ERROR', cell.id, index + 1, type(exc).__name__, exc, flush=True)
                return None
            print('EPISODE', condition, index + 1, ep['status'], ep['rounds_completed'],
                  (ep.get('label') or {}).get('objective_success'), f'${budget.spent:.4f}', flush=True)
            return ep

    # Interleave conditions so a cap stop leaves a balanced sample.
    jobs = [(cond, i, cell) for i in range(max(c for _, c, _ in cells)) for cond, c, cell in cells if i < c]
    results = await asyncio.gather(*(one(*j) for j in jobs))
    for condition, count, cell in cells:
        done = [r for (cond, _, _), r in zip(jobs, results) if cond == condition and r]
        cell.result(completed=sum(e['status'] == 'complete' for e in done), attempted=len(done), planned=count)
        cell.finish('finished')
    parent.result(spent_usd=str(budget.spent), calls=budget.calls)
    parent.finish('finished')
    await client.close()
    print('SCALEUP_DONE', parent.id, f'${budget.spent:.4f}', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--family', default='deploy-token')
    p.add_argument('--strength', default='consequence_logged')
    p.add_argument('--target', default='32b', choices=sorted(TARGETS))
    p.add_argument('--recruiting', type=int, default=40)
    p.add_argument('--control', type=int, default=15)
    p.add_argument('--alone', type=int, default=6)
    p.add_argument('--family-start', type=int, default=2001)
    p.add_argument('--parallelism', type=int, default=4)
    p.add_argument('--cap-usd', type=float, default=3)
    asyncio.run(main(p.parse_args()))
