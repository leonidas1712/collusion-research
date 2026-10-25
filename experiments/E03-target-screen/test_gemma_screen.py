"""Check concurrent budget settlement and smoke-gate rejection offline."""
import asyncio
from decimal import Decimal
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from gemma_screen import ConcurrentBudget, validate_gate, pooled_target_price, pool_options


class ScreenTests(unittest.IsolatedAsyncioTestCase):
    async def test_pool_excludes_fp4_unknown_and_toolless_routes(self):
        endpoints = [{'provider_name': name, 'quantization': 'bf16' if name in ('Novita', 'Crusoe') else 'fp8',
                      'supported_parameters': ['tools'], 'context_length': 100,
                      'pricing': {'prompt': '.01', 'completion': '.02'}}
                     for name in ('Crusoe', 'Novita', 'Parasail', 'DeepInfra')]
        endpoints += [{**endpoints[0], 'quantization': q} for q in ('fp4', 'unknown')]
        endpoints.append({**endpoints[-1], 'quantization': 'fp8', 'supported_parameters': []})
        with patch('gemma_screen.fetch', return_value={'data': {'endpoints': endpoints}}):
            price = pooled_target_price()
        self.assertEqual(len(price['endpoints']), 4)
        route = pool_options(price)['extra_body']['provider']
        self.assertEqual(set(route['only']), {'Crusoe', 'Novita', 'Parasail', 'DeepInfra'})
        self.assertEqual(route['quantizations'], ['bf16', 'fp8'])
        self.assertTrue(route['allow_fallbacks'])
        self.assertTrue(route['require_parameters'])

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
