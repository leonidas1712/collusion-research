"""Check concurrent budget settlement and smoke-gate rejection offline."""
import asyncio
from decimal import Decimal
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from gemma_screen import ConcurrentBudget, validate_gate


class ScreenTests(unittest.IsolatedAsyncioTestCase):
    async def test_reservations_settle_without_losing_concurrent_cost(self):
        async def create(**payload):
            await asyncio.sleep(.001)
            return {'usage': {'cost': .02}, 'provider': 'test'}
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        with tempfile.TemporaryDirectory() as tmp:
            b = ConcurrentBudget(client, Path(tmp)/'ledger.json',
                {'m': {'provider': 'test', 'context_length': 100, 'prompt_cap': '.001',
                       'completion_cap': '.001'}}, '.3')
            payload = {'model': 'm', 'max_tokens': 1,
                       'extra_body': {'provider': {'order': ['test'], 'allow_fallbacks': False}}}
            await asyncio.gather(b.create(**payload), b.create(**payload))
            self.assertAlmostEqual(float(b.ledger['charged_or_reserved_usd']), .04)
            self.assertEqual(Decimal(b.ledger['charged_or_reserved_usd']), Decimal(b.ledger['reported_cost_usd']))

    async def test_cap_blocks_before_network(self):
        async def create(**payload):
            self.fail('Over-cap request reached network')
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        with tempfile.TemporaryDirectory() as tmp:
            b = ConcurrentBudget(client, Path(tmp)/'ledger.json',
                {'m': {'provider': 'test', 'context_length': 100, 'prompt_cap': '.001',
                       'completion_cap': '.001'}}, '.01')
            with self.assertRaisesRegex(RuntimeError, 'reservation'):
                await b.create(model='m', max_tokens=1,
                               extra_body={'provider': {'order': ['test'], 'allow_fallbacks': False}})

    async def test_gate_rejects_reasoning_and_missing_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'smoke.json'
            p.write_text('[]')
            with self.assertRaises(ValueError):
                validate_gate(tmp)
            row = {'status': 'complete', 'tool_errors': [], 'label': {'task_success': True,
                   'exposure_requirement_met': True, 'objective_success': False},
                   'calls': [{'provider': 'Crusoe', 'raw_tool_text': False, 'reasoning_text': False,
                              'reasoning_tokens': 2, 'relative_token_error': 0, 'finish_reason': 'stop'}]}
            p.write_text(json.dumps([{**row, 'family': f} for f in
                                    ('deploy-token-v2', 'handoff-exception-note')]))
            with self.assertRaises(ValueError):
                validate_gate(tmp)


if __name__ == '__main__':
    unittest.main()
