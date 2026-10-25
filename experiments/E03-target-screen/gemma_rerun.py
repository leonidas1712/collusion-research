"""Restart rate-limit and empty-after-send failures, preserving archived attempts."""
import argparse
import asyncio
from dataclasses import fields, replace
from decimal import Decimal
import json
import os
from pathlib import Path

from gemma_screen import ROOT, MODEL, PEER, ConcurrentBudget, price_for, pooled_target_price, pool_options
from overnight_sweep import options
from harness import Settings, run_episode, standard_tools
from scale_up import scale_up_scenario
from collusion.runs import start_run, write_json_atomic
from audit_empty_turns import audit


def check_scenario(s, ep):
    spec = ep['scenario_spec']
    for key in ('name', 'target_system', 'target_task', 'files', 'test_result',
                'scenario_version', 'channel_format', 'actor_names', 'peer_enabled'):
        if getattr(s, key) != spec[key]:
            raise ValueError(f'Rerun scenario changed: {key}')
    if (s.recruiter_system if s.peer_enabled else None) != spec['recruiter_system']:
        raise ValueError('Rerun peer text changed')
    if list(s.honeypots) != spec['honeypots']:
        raise ValueError('Rerun protected values changed')
    if {actor: sorted(set(names)) for actor, names in s.tool_access.items()} != spec['tool_access']:
        raise ValueError('Rerun tool access changed')
    overrides = {t.schema['function']['name']: t for t in s.tool_overrides}
    tools = [overrides.get(t.schema['function']['name'], t) for t in standard_tools()] + list(s.extra_tools)
    if [t.schema for t in tools] != spec['tools']:
        raise ValueError('Rerun tool schemas changed')


async def main(a):
    parent = Path(a.run).resolve()
    if json.loads((parent/'meta.json').read_text())['status'] == 'running':
        raise ValueError('Wait for the batch to finish before restarting failures')
    ledgers = [parent/'budget.json', *[Path(p) for p in a.prior_budget]]
    used = sum(Decimal(json.loads(p.read_text())['charged_or_reserved_usd']) for p in ledgers)
    remaining = Decimal('2.90') - used
    if remaining <= 0:
        raise ValueError('Screen budget is exhausted')
    jobs = []
    for cell in json.loads((parent/'cells.json').read_text()):
        directory = ROOT/'runs'/cell
        cell_settings = json.loads((directory/'meta.json').read_text())['settings']
        for number in range(1, cell_settings['count'] + 1):
            final = directory/'episodes'/f'episode-{number:04}.json'
            p = final if final.exists() else final.with_name(f'episode-{number:04}.partial.json')
            if not p.exists():
                if a.complete_plan:
                    jobs.append((p, None, cell_settings, number))
                continue
            ep = json.loads(p.read_text())
            empty_after_send = ep.get('stop_reason') == 'empty_assistant_message' and audit(p, ep)['same_turn_delivered_send_message']
            recovered_after_send = ep.get('status') == 'complete' and any(
                r.get('empty_retry_scheduled') and audit(p, {**ep, 'requests': ep['requests'][:i+1]})['same_turn_delivered_send_message']
                for i, r in enumerate(ep['requests']))
            if (ep.get('stop_reason') == 'api_error:RateLimitError' or empty_after_send
                    or recovered_after_send or a.complete_plan and ep.get('status') == 'running'):
                jobs.append((p, ep, cell_settings, number))
    # Interleave families and conditions instead of completing one whole cell first.
    jobs.sort(key=lambda job: (job[3], job[2]['family'], job[2]['condition']))
    run = start_run('e03-gemma-failed-episode-rerun', experiment='E03',
                    settings={**vars(a), 'cap_usd': str(remaining),
                              'empty_after_send_ends_turn': True},
                    parents=[parent.name], tags=['second-target', 'failed-episode-rerun'], model=MODEL)
    write_json_atomic(run.dir/'selected.json', [str(job[0].relative_to(ROOT)) for job in jobs])
    prices = {MODEL: pooled_target_price() if a.provider_pool else price_for(MODEL, 'Crusoe', 'bf16'),
              PEER: price_for(PEER, 'DeepInfra', 'fp8')}
    write_json_atomic(run.dir/'prices.json', prices)
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    load_dotenv(ROOT/'.env')
    async with AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'],
                           base_url='https://openrouter.ai/api/v1', max_retries=0, timeout=90) as client:
        budget = ConcurrentBudget(client, run.dir/'budget.json', prices, remaining)
        budget.save()
        results = []
        gate = asyncio.Semaphore(a.parallelism)
        async def one(path, ep, cell_settings, index):
            async with gate:
                family, condition = cell_settings['family'], cell_settings['condition']
                family_id = str(cell_settings['family_start'] + index - 1)
                episode_id = f'episode-{index:04}'
                s = scale_up_scenario('deploy-token-v2' if family == 'deploy-token-v2' else 'deploy-token',
                    'consequence', condition, family_id, 'T0',
                    spray_row=None if family == 'deploy-token-v2' else family)
                if ep:
                    check_scenario(s, ep)
                source_settings = ep['settings'] if ep else cell_settings
                settings = Settings(**{f.name: source_settings[f.name] for f in fields(Settings) if f.name in source_settings})
                settings = replace(settings, empty_after_send_ends_turn=True, empty_response_retries=2,
                                   api_retry_attempts=10, api_retry_max_delay=60,
                                   recruiter_request_options=options(prices[PEER]))
                if a.provider_pool:
                    settings = replace(settings, target_request_options=pool_options(prices[MODEL]))
                archived = None
                if ep:
                    number = 1
                    archived = path.with_name(f'{episode_id}.attempt-{number}.json')
                    while archived.exists():
                        number += 1
                        archived = path.with_name(f'{episode_id}.attempt-{number}.json')
                    path.rename(archived)
                result = await run_episode(s, settings, budget, path.parent, episode_id=episode_id)
                results.append({'episode': str(path.relative_to(ROOT)), 'status': result['status'],
                                'stop_reason': result['stop_reason'],
                                'final_episode': str((path.parent / (episode_id +
                                    ('.json' if result['status'] == 'complete' else '.partial.json'))).relative_to(ROOT)),
                                'prior_attempt': str(archived.relative_to(ROOT)) if archived else None})
                write_json_atomic(run.dir/'results.json', results)
                print(family, condition, episode_id, result['status'], result['stop_reason'],
                      (result.get('label') or {}).get('objective_success'), budget.ledger['reported_cost_usd'], flush=True)
        await asyncio.gather(*(one(*job) for job in jobs))
        run.result(planned=len(jobs), completed=sum(r['status'] == 'complete' for r in results),
                   spent_usd=budget.ledger['reported_cost_usd'])
        run.finish()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run')
    p.add_argument('--prior-budget', action='append', default=[], help='Additional preceding rerun ledgers')
    p.add_argument('--complete-plan', action='store_true', help='Also run missing or interrupted planned episodes')
    p.add_argument('--provider-pool', action='store_true', help='Use only approved bf16/fp8 tool providers')
    p.add_argument('--parallelism', type=int, choices=(1, 2, 3, 4), default=1)
    asyncio.run(main(p.parse_args()))
