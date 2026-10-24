"""Sequential, budget-reserved overnight API sweeps. No GPU operations."""
import argparse
import asyncio
from dataclasses import asdict
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import urllib.request

from harness import Settings, run_episode
from overnight_rules import get_overnight_scenario

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run, write_json_atomic

TARGETS = {
    '32b': ('qwen/qwen3-32b', 'DeepInfra'),
    '30b': ('qwen/qwen3-30b-a3b-instruct-2507', 'SiliconFlow'),
}
PEER = 'deepseek/deepseek-v4-flash'
FAMILIES = ('front-door-sign', 'poster-approval', 'deploy-token', 'release-date', 'minimum-price')
LIMIT = Decimal('5')


class BudgetExhausted(RuntimeError):
    pass


class BudgetClient:
    is_fake = False

    def __init__(self, client, ledger_path, prices):
        self.client = client
        self.path = Path(ledger_path)
        self.prices = prices
        self.ledger = json.loads(self.path.read_text()) if self.path.exists() else {
            'limit_usd': str(LIMIT), 'charged_or_reserved_usd': '0', 'reported_cost_usd': '0', 'calls': []}
        self.blocked = False
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **payload):
        if self.blocked:
            raise BudgetExhausted('Budget guard already stopped this stream')
        price = self.prices[payload['model']]
        routing = payload.get('extra_body', {}).get('provider', {})
        if routing.get('order') != [price['provider']] or routing.get('allow_fallbacks') is not False:
            raise ValueError('Budgeted request must pin its priced provider')
        # Reserve an entire context window at the router price ceiling, plus capped output.
        reserve = (Decimal(str(price['context_length'])) * Decimal(price['prompt_cap']) +
                   Decimal(str(payload['max_tokens'])) * Decimal(price['completion_cap'])) * Decimal('1.10')
        used = Decimal(self.ledger['charged_or_reserved_usd'])
        if used + reserve > LIMIT:
            self.blocked = True
            raise BudgetExhausted('No room for the next request reservation')
        row = {'model': payload['model'], 'reserved_usd': str(reserve), 'state': 'reserved'}
        self.ledger['calls'].append(row)
        self.ledger['charged_or_reserved_usd'] = str(used + reserve)
        write_json_atomic(self.path, self.ledger)
        try:
            response = await self.client.chat.completions.create(**payload)
        except Exception as exc:
            row['state'] = 'error_reservation_retained'
            row['error_type'] = type(exc).__name__
            row['status_code'] = getattr(exc, 'status_code', None)
            # HTTP 429 rejects this non-streaming request; no paid plugins are used.
            if row['status_code'] == 429 and not payload.get('plugins'):
                row.update(state='rate_limit_unbilled', reported_cost_usd='0',
                           settlement_source='https://openrouter.ai/pricing#frequently-asked-questions')
                self.ledger['charged_or_reserved_usd'] = str(used)
            write_json_atomic(self.path, self.ledger)
            raise
        data = response.model_dump() if hasattr(response, 'model_dump') else response
        cost = (data.get('usage') or {}).get('cost')
        if cost is None:
            row['state'] = 'missing_cost_reservation_retained'
        else:
            cost = Decimal(str(cost))
            if cost < 0 or not cost.is_finite():
                raise ValueError('Invalid billed response cost')
            row.update(state='billed', reported_cost_usd=str(cost), response_id=data.get('id'))
            self.ledger['charged_or_reserved_usd'] = str(used + cost)
            self.ledger['reported_cost_usd'] = str(Decimal(self.ledger['reported_cost_usd']) + cost)
            if cost > reserve:
                self.blocked = True
                row['reservation_exceeded'] = True
        write_json_atomic(self.path, self.ledger)
        return response


def fetch_prices():
    result = {}
    for model, provider in [*TARGETS.values(), (PEER, 'DeepInfra')]:
        url = f'https://openrouter.ai/api/v1/models/{model}/endpoints'
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.load(response)
        endpoint = next(e for e in data['data']['endpoints']
                        if e['provider_name'] == provider and e.get('quantization') == 'fp8')
        pricing = endpoint['pricing']
        if Decimal(str(pricing.get('request', 0))) != 0:
            raise ValueError('Unexpected per-request charge')
        prompt_cap = Decimal(pricing['prompt']) * Decimal('1.01')
        completion_cap = Decimal(pricing['completion']) * Decimal('1.01')
        result[model] = {'provider': provider, 'context_length': endpoint['context_length'],
                         'prompt_cap': str(prompt_cap), 'completion_cap': str(completion_cap),
                         'source': url, 'endpoint': endpoint}
    return result


def options(price):
    return {'extra_body': {'reasoning': {'enabled': False}, 'provider': {
        'order': [price['provider']], 'allow_fallbacks': False, 'quantizations': ['fp8'],
        'max_price': {'prompt': float(Decimal(price['prompt_cap']) * 1000000),
                      'completion': float(Decimal(price['completion_cap']) * 1000000), 'request': 0}}}}


def round_one_plan():
    return [{'target': target, 'scenario_family': family, 'strength': strength, 'sweep_round': 1}
            for family in FAMILIES for target in TARGETS
            if family != 'minimum-price' or target == '32b'
            for strength in ('consequence', 'consequence_logged')]


def final_wave_plan():
    return [{'target': target, 'scenario_family': 'deploy-token', 'strength': strength,
             'sweep_round': 2}
            for target, strength in [('30b', 'consequence'), ('32b', 'consequence'),
                                     ('32b', 'consequence_logged')]]


def validate_final_plan(plan):
    if plan != final_wave_plan():
        raise ValueError('Final wave must match the three deploy-token cells authorized in Aboard #362')


async def execute(args):
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    from overnight_report import build_report

    if args.sweep_round not in (1, 2):
        raise ValueError('At most two sweep rounds')
    if args.sweep_round == 1:
        run = start_run('e01-overnight-rule-strength', experiment='E01',
                        settings={'budget_usd': 5, 'sweep_round': 1, 'plan': round_one_plan(),
                                  'review_status': "run overnight, pending Leo's post-hoc review"},
                        tags=['overnight', 'rule-strength', 'pending-posthoc-review'])
        parent = run.dir
        manifest = {'cells': [], 'peer_model': PEER, 'peer_provider': 'DeepInfra',
                    'review_status': "run overnight, pending Leo's post-hoc review",
                    'cost_ledger': str(parent / 'budget.json'), 'rounds_started': [1]}
        write_json_atomic(parent / 'manifest.json', manifest)
        prices = fetch_prices()
        write_json_atomic(parent / 'prices.json', prices)
        plan = round_one_plan()
    else:
        parent = Path(args.parent).resolve()
        manifest = json.loads((parent / 'manifest.json').read_text())
        if manifest.get('rounds_started') != [1]:
            raise ValueError('Round two already started or round one absent')
        plan = json.loads(Path(args.plan).read_text())
        if not plan or any(cell.get('sweep_round') != 2 for cell in plan):
            raise ValueError('Round-two plan must explicitly identify its wave')
        validate_final_plan(plan)
        manifest['selection_policy'] = 'explicit_expansion_362'
        manifest['final_wave_authorization'] = 'Aboard #362'
        manifest['round_two_plan'] = plan
        manifest['rounds_started'].append(2)
        write_json_atomic(parent / 'manifest.json', manifest)
        prices = json.loads((parent / 'prices.json').read_text())
        run = start_run('e01-overnight-rule-strength-round2', experiment='E01', settings={'plan': plan},
                        parents=[parent.name], tags=['overnight', 'round2', 'pending-posthoc-review'])
    print('SWEEP_PARENT', parent, flush=True)
    load_dotenv(ROOT / '.env')
    client = AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'], base_url='https://openrouter.ai/api/v1',
                         max_retries=0, timeout=90)
    budget = BudgetClient(client, parent / 'budget.json', prices)
    try:
        for group in plan:
            key, family, strength = group['target'], group['scenario_family'], group['strength']
            if family == 'minimum-price' and key != '32b':
                raise ValueError('Minimum-price restricted to 32B')
            model, provider = TARGETS[key]
            for condition, count in (('alone', 2), ('recruiting', 8 if args.sweep_round == 2 else 5)):
                settings = Settings(model, PEER, rounds=20, max_tool_steps=12, max_tokens=1536,
                                    target_request_options=options(prices[model]),
                                    recruiter_request_options=options(prices[PEER]))
                stdout, stderr, hook = sys.stdout, sys.stderr, sys.excepthook
                cell = start_run(f'e01-{family}-{strength}-{condition}-{key}', experiment='E01',
                                 settings={**asdict(settings), **group, 'condition': condition,
                                           'scenario_family': family, 'review_status': manifest['review_status']},
                                 parents=[run.id], tags=['overnight', strength, 'pending-posthoc-review'], model=model)
                record = {'target_model': model, 'provider': provider, 'scenario_family': family,
                          'strength': strength, 'condition': condition, 'sweep_round': args.sweep_round,
                          'run_id': cell.id, 'run_dir': str(cell.dir), 'planned_episodes': count}
                manifest['cells'].append(record)
                write_json_atomic(parent / 'manifest.json', manifest)
                outcomes = []
                try:
                    for index in range(count):
                        scenario = get_overnight_scenario(family, strength, condition,
                                                         family_id=str(1001 + index))
                        scenario.metadata.update(sweep_round=args.sweep_round,
                                                 preparation_status='executed sweep; pending post-hoc review',
                                                 base_strength=group.get('base_strength'))
                        ep = await run_episode(scenario, settings, budget, cell.dir / 'episodes',
                                               episode_id=f'episode-{index+1:04}')
                        outcomes.append(ep)
                        print('EPISODE', cell.id, index + 1, ep['status'], ep['rounds_completed'],
                              (ep.get('label') or {}).get('objective_success'),
                              budget.ledger['reported_cost_usd'], flush=True)
                        if budget.blocked:
                            break
                    cell.result(completed=sum(e['status'] == 'complete' for e in outcomes),
                                attempted=len(outcomes), planned=count)
                    cell.finish('finished' if len(outcomes) == count and all(e['status'] == 'complete' for e in outcomes) else 'failed')
                finally:
                    log = sys.stdout.log
                    sys.stdout, sys.stderr, sys.excepthook = stdout, stderr, hook
                    log.close()
                build_report(parent / 'manifest.json', parent)
                if budget.blocked:
                    break
            if budget.blocked:
                break
        summary = build_report(parent / 'manifest.json', parent)
        manifest['stop_reason'] = 'budget_guard' if budget.blocked else 'plan_finished'
        manifest['planned_groups_this_round'] = len(plan)
        manifest['attempted_cells_this_round'] = sum(c['sweep_round'] == args.sweep_round for c in manifest['cells'])
        write_json_atomic(parent / 'manifest.json', manifest)
        run.result(summary=summary, budget=budget.ledger, stop_reason=manifest['stop_reason'],
                   planned_groups=len(plan), attempted_cells=manifest['attempted_cells_this_round'])
        run.finish('finished' if not budget.blocked else 'failed', 'budget_guard' if budget.blocked else None)
        print('SWEEP_DONE', parent, budget.ledger['reported_cost_usd'], flush=True)
    except BaseException as exc:
        run.finish('failed', type(exc).__name__)
        raise
    finally:
        await client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sweep-round', type=int, choices=[1, 2], default=1)
    parser.add_argument('--parent', type=Path)
    parser.add_argument('--plan', type=Path)
    args = parser.parse_args()
    if args.sweep_round == 2 and (args.parent is None or args.plan is None):
        parser.error('Round two requires --parent and --plan')
    asyncio.run(execute(args))
