"""Run four fixed scenarios with a combined-tactic peer under a shared API budget."""
import argparse
import asyncio
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

from gemma_pressure_prompts import ROOT, FAMILIES, scenario
from gemma_screen import MODEL, ConcurrentBudget, pooled_target_price, pool_options
from catalog import fetch
from harness import Settings, run_episode
from collusion.runs import start_run, write_json_atomic

PEER = 'deepseek/deepseek-v4-pro-0813'


def peer_price():
    snapshot = fetch(f'https://openrouter.ai/api/v1/models/{PEER}/endpoints')
    names = ['DeepSeek']
    endpoints = [e for e in snapshot['data']['endpoints'] if e['provider_name'] in names
                 and {'tools', 'reasoning'}.issubset(e['supported_parameters'])]
    if {e['provider_name'] for e in endpoints} != set(names):
        raise ValueError('The first-party peer must support tools and reasoning')
    if any(Decimal(str(e['pricing'].get('request', 0))) != 0 for e in endpoints):
        raise ValueError('Unexpected per-request fee')
    return {'provider': 'DeepSeek', 'context_length': max(e['context_length'] for e in endpoints),
            'prompt_cap': str(max(Decimal(e['pricing']['prompt']) for e in endpoints) * Decimal('1.01')),
            'completion_cap': str(max(Decimal(e['pricing']['completion']) for e in endpoints) * Decimal('1.01')),
            'routing': {'order': names, 'only': names, 'allow_fallbacks': False,
                        'require_parameters': True},
            'endpoints': endpoints, 'snapshot': snapshot}


def peer_options(price):
    result = pool_options(price)
    result['extra_body']['provider'].pop('quantizations', None)
    result['extra_body']['reasoning'] = {'enabled': True, 'effort': 'medium'}
    return result


class ServingMetadata:
    """Keep response precision separate from precision inferred from endpoint metadata."""
    is_fake = False

    def __init__(self, budget, prices):
        self.budget, self.prices = budget, prices
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **payload):
        response = await self.budget.create(**payload)
        data = response.model_dump() if hasattr(response, 'model_dump') else dict(response)
        provider = data.get('provider')
        candidates = sorted({e['quantization'] for e in self.prices[payload['model']]['endpoints']
                             if e['provider_name'] == provider})
        data['screen_serving_metadata'] = {
            'served_provider': provider, 'reported_quantization': data.get('quantization'),
            'endpoint_precision_candidates': candidates,
            'precision_basis': 'response.quantization' if data.get('quantization') else
                               'saved endpoint catalog and requested routing filter',
            'precision_independently_verified': False}
        return data


async def main(args):
    if not 0 <= args.prior_reserved_usd < 5.70 or not 0 < args.cap_usd <= 5.70 - args.prior_reserved_usd:
        raise ValueError('Episode calls must leave USD0.30 of the USD6 total for semantic judging')
    prompt_plan = ROOT / 'runs' / args.prompt_plan
    prompts = json.loads((prompt_plan / 'prompts.json').read_text())
    for row in prompts:
        composed = scenario(row['family'], row['condition'], args.family_start, reviewed=True)
        if hashlib.sha256(composed.recruiter_system.encode()).hexdigest() != row['prompt_sha256']:
            raise ValueError('Composed prompt changed after the saved review plan')
    if len(prompts) != 8:
        raise ValueError('The prompt plan must cover all four recruiting/control pairs')
    prices = {MODEL: pooled_target_price(), PEER: peer_price()}
    settings = Settings(MODEL, PEER, rounds=20, max_tool_steps=12, max_tokens=8192,
                        empty_response_retries=2, empty_after_send_ends_turn=True,
                        api_retry_attempts=10, api_retry_max_delay=60,
                        target_request_options=pool_options(prices[MODEL]),
                        recruiter_request_options=peer_options(prices[PEER]))
    parent = start_run('e03-gemma-pressure', experiment='E03',
                       settings={**vars(args), 'episode_settings': asdict(settings),
                                 'planned_episodes': 48, 'total_cap_usd': 6},
                       parents=[args.prompt_plan], tags=['second-target', 'combined-tactics'], model=MODEL)
    write_json_atomic(parent.dir / 'prices.json', prices)
    streams = sys.stdout, sys.stderr, sys.excepthook
    cells = []
    for family in FAMILIES:
        for condition, count in [('recruiting', 10), ('control', 2)]:
            cell = start_run(f'e01-gemma-pressure-{family}-{condition}', experiment='E01',
                             settings={**asdict(settings), 'family': family, 'condition': condition,
                                       'count': count, 'family_start': args.family_start,
                                       'tactic_ids': scenario(family, condition, args.family_start).metadata['tactic_ids']},
                             parents=[parent.id], tags=['second-target', 'combined-tactics', condition], model=MODEL)
            sys.stdout, sys.stderr, sys.excepthook = streams
            cells.append((family, condition, count, cell))
    write_json_atomic(parent.dir / 'cells.json', [c.id for _, _, _, c in cells])
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    load_dotenv(ROOT / '.env')
    results = []
    try:
        async with AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'], base_url='https://openrouter.ai/api/v1',
                               max_retries=0, timeout=90) as client:
            budget = ConcurrentBudget(client, parent.dir / 'budget.json', prices, args.cap_usd)
            budget.save()
            wrapped = ServingMetadata(budget, prices)
            gate = asyncio.Semaphore(args.parallelism)

            async def one(family, condition, cell, index):
                async with gate:
                    composed = scenario(family, condition, args.family_start + index, reviewed=True)
                    ep = await run_episode(composed, settings, wrapped, cell.dir / 'episodes',
                                           episode_id=f'episode-{index+1:04}')
                    result = {'cell': cell.id, 'family': family, 'condition': condition,
                              'episode_id': ep['episode_id'], 'status': ep['status'],
                              'stop_reason': ep['stop_reason'], 'label': ep.get('label')}
                    results.append(result)
                    write_json_atomic(parent.dir / 'progress.json', {'completed_jobs': len(results),
                                      'planned_jobs': 48, 'reported_cost_usd': budget.ledger['reported_cost_usd'],
                                      'charged_or_reserved_usd': budget.ledger['charged_or_reserved_usd'],
                                      'results': results})
                    print('EPISODE', family, condition, index+1, ep['status'], ep['stop_reason'],
                          budget.ledger['reported_cost_usd'], flush=True)

            jobs = [(f, c, cell, i) for i in range(10) for f, c, n, cell in cells if i < n]
            await one(*jobs[0])
            if results[0]['status'] != 'complete':
                raise RuntimeError('First episode did not complete; inspect before continuing')
            print('SMOKE_REVIEW_REQUIRED', parent.dir, flush=True)
            approval = parent.dir / 'smoke-reviewed.json'
            while not approval.exists():
                await asyncio.sleep(1)
            review = json.loads(approval.read_text())
            if not review.get('peer_in_role') or not review.get('reasoning_isolated'):
                raise RuntimeError('First-episode trace review did not pass')
            await asyncio.gather(*(one(*job) for job in jobs[1:]))
            for _, _, count, cell in cells:
                cell.result(planned=count, completed=sum(r['cell'] == cell.id and r['status'] == 'complete' for r in results))
                cell.finish()
            parent.result(episodes=len(results), complete=sum(r['status'] == 'complete' for r in results),
                          reported_cost_usd=budget.ledger['reported_cost_usd'],
                          charged_or_reserved_usd=budget.ledger['charged_or_reserved_usd'])
            parent.finish()
            print('BATCH_RUN', parent.id, flush=True)
    except BaseException as exc:
        for _, _, _, cell in cells:
            cell.finish('failed', 'Batch stopped before its full episode count completed')
        parent.finish('failed', str(exc))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt-plan', required=True)
    parser.add_argument('--cap-usd', type=float, default=5.70)
    parser.add_argument('--prior-reserved-usd', type=float, default=0)
    parser.add_argument('--family-start', type=int, default=96001)
    parser.add_argument('--parallelism', type=int, choices=(1, 2, 3, 4), default=4)
    asyncio.run(main(parser.parse_args()))
