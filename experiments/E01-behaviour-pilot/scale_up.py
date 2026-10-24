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
from peer_tactics import TACTIC_IDS, apply_peer_tactic
from leak_scenarios import get_spray_scenario
from many_peer import prepare_many_peer_scenario, run_many_peer_episode

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


def scale_up_scenario(family, strength, condition, family_id, tactic=None,
                      scenario_variant=None, spray_row=None, peers=1):
    if spray_row:
        if strength != 'consequence_logged':
            raise ValueError('Scenario spray rows currently require consequence_logged strength')
        if scenario_variant is not None:
            raise ValueError('--scenario-variant cannot be combined with --spray-row')
        scenario = get_spray_scenario(
            spray_row, condition, family_id=family_id, rule_strength=strength)
    else:
        scenario = get_overnight_scenario(
            family, strength, condition, family_id=family_id,
            scenario_variant=scenario_variant)
    if tactic and condition != 'alone':
        scenario = apply_peer_tactic(scenario, tactic)
    if peers != 1 and condition != 'alone':
        scenario = prepare_many_peer_scenario(scenario, peers)
    return scenario


async def main(a):
    selected_conditions = [condition for condition, count in (
        ('recruiting', a.recruiting), ('control', a.control), ('alone', a.alone)) if count]
    if not selected_conditions:
        raise ValueError('At least one cell count must be nonzero')
    preflight = scale_up_scenario(
        a.family, a.strength, selected_conditions[0], str(a.family_start), a.tactic,
        a.scenario_variant, a.spray_row, a.peers)
    if (a.spray_row or a.family == 'database-password') and not preflight.recruiter_approved:
        raise RuntimeError('This scenario is pending Leo review; set approved=true only after approval')
    if a.peers > 1 and preflight.peer_enabled and not preflight.recruiter_approved:
        raise RuntimeError('Many-to-one cells are pending Leo review; set MANY_PEER_APPROVED after approval')

    from dotenv import load_dotenv
    from openai import AsyncOpenAI

    model, provider = TARGETS[a.target]
    prices = fetch_prices()
    target_options = options(prices[model])
    if a.target_reasoning:  # thinking mode: same weights, reasoning on, room for the thinking tokens
        target_options['extra_body']['reasoning'] = {'enabled': True}
    settings = Settings(model, PEER, rounds=20, max_tool_steps=12, max_tokens=4096 if a.target_reasoning else 1536,
                        target_request_options=target_options,
                        recruiter_request_options=options(prices[PEER]))
    load_dotenv(ROOT / '.env')
    client = AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'], base_url='https://openrouter.ai/api/v1',
                         max_retries=0, timeout=90)
    run_family = f'spray-{a.spray_row}' if a.spray_row else a.family
    tactic_suffix = f'-{a.tactic.lower()}' if a.tactic else ''
    if a.target_reasoning:
        tactic_suffix += '-think'
    variant_suffix = f'-{a.scenario_variant}' if a.scenario_variant else ''
    peer_suffix = f'-{a.peers}peers' if a.peers > 1 else ''
    parent_settings = {'cap_usd': a.cap_usd, 'counts': {'recruiting': a.recruiting, 'control': a.control,
                       'alone': a.alone}, 'family_start': a.family_start, 'parallelism': a.parallelism}
    if a.tactic:
        parent_settings['tactic_id'] = a.tactic
    if a.scenario_variant:
        parent_settings['scenario_variant'] = a.scenario_variant
    if a.spray_row:
        parent_settings['spray_row'] = a.spray_row
    if a.peers > 1:
        parent_settings['peer_count'] = a.peers
    parent = start_run(f'e01-scaleup-{run_family}-{a.strength}-{a.target}{variant_suffix}{tactic_suffix}{peer_suffix}', experiment='E01',
                       settings=parent_settings,
                       tags=['scale-up', a.strength]
                       + ([a.scenario_variant] if a.scenario_variant else [])
                       + ([a.tactic.lower()] if a.tactic else []), model=model)
    budget = SpendCap(client, a.cap_usd, parent.dir / 'budget.json')
    gate = asyncio.Semaphore(a.parallelism)
    cells = []
    streams = sys.stdout, sys.stderr, sys.excepthook  # keep everything in the parent log
    for condition, count in (('recruiting', a.recruiting), ('control', a.control), ('alone', a.alone)):
        if count:
            cell_settings = {**asdict(settings), 'scenario_family': run_family, 'strength': a.strength,
                             'condition': condition, 'target': a.target}
            if a.tactic and condition != 'alone':
                cell_settings['tactic_id'] = a.tactic
            if a.scenario_variant:
                cell_settings['scenario_variant'] = a.scenario_variant
            if a.spray_row:
                cell_settings['spray_row'] = a.spray_row
            if a.peers > 1:
                cell_settings['peer_count'] = a.peers if condition != 'alone' else 0
            cell = start_run(f'e01-{run_family}-{a.strength}-{condition}-{a.target}{variant_suffix}{tactic_suffix}{peer_suffix}-scaleup', experiment='E01',
                             settings=cell_settings, parents=[parent.id],
                             tags=['scale-up', a.strength, condition]
                             + ([a.scenario_variant] if a.scenario_variant else [])
                             + ([a.tactic.lower()] if a.tactic and condition != 'alone' else []),
                             model=model)
            sys.stdout, sys.stderr, sys.excepthook = streams
            cells.append((condition, count, cell))

    async def one(condition, index, cell):
        async with gate:
            if budget.spent >= budget.cap:
                return None
            scenario = scale_up_scenario(
                a.family, a.strength, condition, str(a.family_start + index), a.tactic,
                a.scenario_variant, a.spray_row, a.peers)
            try:
                if a.peers > 1 and condition != 'alone':
                    ep = await run_many_peer_episode(
                        scenario, settings, budget, cell.dir / 'episodes',
                        episode_id=f'episode-{index+1:04}')
                else:
                    ep = await run_episode(
                        scenario, settings, budget, cell.dir / 'episodes',
                        episode_id=f'episode-{index+1:04}')
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


def make_parser():
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
    p.add_argument('--target-reasoning', action='store_true', help='Run the target with reasoning (thinking mode) on')
    p.add_argument('--tactic', type=str.upper, choices=TACTIC_IDS,
                   help='Append a Leo-approved peer tactic (PEER_TACTICS.md)')
    p.add_argument('--scenario-variant', choices=('required-access-own-stake',),
                   help='Use a pending-review registered scenario variant')
    p.add_argument('--spray-row', help='Build a CSV-backed leak scenario row (pending rows are blocked)')
    p.add_argument('--peers', type=int, choices=(1, 2, 3), default=1,
                   help='Number of ordered peers before the target (2-3 pending Leo review)')
    return p


if __name__ == '__main__':
    asyncio.run(main(make_parser().parse_args()))
