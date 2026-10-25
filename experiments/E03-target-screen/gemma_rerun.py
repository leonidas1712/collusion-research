"""Restart rate-limit and empty-after-send failures, preserving archived attempts."""
import argparse
import asyncio
from dataclasses import fields, replace
from decimal import Decimal
import json
import os
from pathlib import Path

from gemma_screen import ROOT, MODEL, PEER, ConcurrentBudget, price_for
from harness import Settings, run_episode
from scale_up import scale_up_scenario
from collusion.runs import start_run, write_json_atomic
from audit_empty_turns import audit


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
        for p in sorted((ROOT/'runs'/cell/'episodes').glob('*.partial.json')):
            ep = json.loads(p.read_text())
            empty_after_send = ep.get('stop_reason') == 'empty_assistant_message' and audit(p, ep)['same_turn_delivered_send_message']
            if ep.get('stop_reason') == 'api_error:RateLimitError' or empty_after_send:
                jobs.append((p, ep))
    run = start_run('e03-gemma-failed-episode-rerun', experiment='E03',
                    settings={**vars(a), 'parallelism': 1, 'cap_usd': str(remaining),
                              'empty_after_send_ends_turn': True},
                    parents=[parent.name], tags=['second-target', 'failed-episode-rerun'], model=MODEL)
    write_json_atomic(run.dir/'selected.json', [str(p.relative_to(ROOT)) for p, _ in jobs])
    prices = {MODEL: price_for(MODEL, 'Crusoe', 'bf16'), PEER: price_for(PEER, 'DeepInfra', 'fp8')}
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    load_dotenv(ROOT/'.env')
    async with AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'],
                           base_url='https://openrouter.ai/api/v1', max_retries=0, timeout=90) as client:
        budget = ConcurrentBudget(client, run.dir/'budget.json', prices, remaining)
        results = []
        for path, ep in jobs:
            meta = ep['scenario_spec']['metadata']
            family = meta.get('spray_row_id', 'deploy-token-v2')
            s = scale_up_scenario('deploy-token-v2' if family == 'deploy-token-v2' else 'deploy-token',
                'consequence', meta['peer_condition'], meta['family_id'], 'T0',
                spray_row=None if family == 'deploy-token-v2' else family)
            settings = Settings(**{f.name: ep['settings'][f.name] for f in fields(Settings) if f.name in ep['settings']})
            settings = replace(settings, empty_after_send_ends_turn=True)
            archived = None
            if not ep['settings'].get('empty_after_send_ends_turn', False):
                # Keep the failed attempt intact before changing turn-end semantics.
                number = 1
                archived = path.with_name(f"{ep['episode_id']}.attempt-{number}.json")
                while archived.exists():
                    number += 1
                    archived = path.with_name(f"{ep['episode_id']}.attempt-{number}.json")
                path.rename(archived)
            result = await run_episode(s, settings, budget, path.parent, episode_id=ep['episode_id'])
            results.append({'episode': str(path.relative_to(ROOT)), 'status': result['status'],
                            'stop_reason': result['stop_reason'],
                            'prior_attempt': str(archived.relative_to(ROOT)) if archived else None})
            write_json_atomic(run.dir/'results.json', results)
            print(path.parent.parent.name, ep['episode_id'], result['status'], result['stop_reason'], flush=True)
        run.result(planned=len(jobs), completed=sum(r['status'] == 'complete' for r in results),
                   spent_usd=budget.ledger['reported_cost_usd'])
        run.finish()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run')
    p.add_argument('--prior-budget', action='append', default=[], help='Additional preceding rerun ledgers')
    asyncio.run(main(p.parse_args()))
