import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from overnight_sweep import BudgetClient, BudgetExhausted, options, round_one_plan

PRICES = {'m': {'provider': 'DeepInfra', 'context_length': 1000,
                'prompt_cap': '0.000001', 'completion_cap': '0.000002'}}


class Transport:
    def __init__(self, response=None, error=None):
        self.response = response if response is not None else {'usage': {'cost': 0.0001}}
        self.error = error
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self.response


class BudgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_reservation_settles_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'budget.json'
            transport = Transport()
            client = BudgetClient(transport, path, PRICES)
            await client.create(model='m', max_tokens=10, **options(PRICES['m']))
            self.assertEqual(client.ledger['reported_cost_usd'], '0.0001')
            restored = BudgetClient(transport, path, PRICES)
            self.assertEqual(restored.ledger['charged_or_reserved_usd'], '0.0001')

    async def test_limit_refuses_before_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'budget.json'
            path.write_text(json.dumps({'limit_usd': '5', 'charged_or_reserved_usd': '4.9995',
                                        'reported_cost_usd': '4.9995', 'calls': []}))
            transport = Transport()
            client = BudgetClient(transport, path, PRICES)
            with self.assertRaises(BudgetExhausted):
                await client.create(model='m', max_tokens=10, **options(PRICES['m']))
            self.assertEqual(transport.calls, 0)
            self.assertTrue(client.blocked)

    async def test_missing_cost_and_errors_keep_reservation(self):
        for transport in (Transport({'usage': {}}), Transport(error=TimeoutError())):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'budget.json'
                client = BudgetClient(transport, path, PRICES)
                try:
                    await client.create(model='m', max_tokens=10, **options(PRICES['m']))
                except TimeoutError:
                    pass
                saved = json.loads(path.read_text())
                self.assertGreater(float(saved['charged_or_reserved_usd']), 0)
                self.assertEqual(saved['reported_cost_usd'], '0')

    async def test_unpinned_provider_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = Transport()
            client = BudgetClient(transport, Path(directory) / 'budget.json', PRICES)
            with self.assertRaises(ValueError):
                await client.create(model='m', max_tokens=10)
            self.assertEqual(transport.calls, 0)

    async def test_blocked_stream_cannot_issue_another_call(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = Transport()
            client = BudgetClient(transport, Path(directory) / 'budget.json', PRICES)
            client.blocked = True
            with self.assertRaises(BudgetExhausted):
                await client.create(model='m', max_tokens=10, **options(PRICES['m']))
            self.assertEqual(transport.calls, 0)

    def test_first_round_is_126_episodes_with_minimum_price_restriction(self):
        plan = round_one_plan()
        self.assertEqual(len(plan), 18)
        self.assertEqual(len(plan) * 7, 126)
        self.assertTrue(all(g['target'] == '32b' for g in plan if g['scenario_family'] == 'minimum-price'))


if __name__ == '__main__':
    unittest.main()
