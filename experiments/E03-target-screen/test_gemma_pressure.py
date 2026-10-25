"""Check prompt preservation and serving-metadata attribution without API calls."""
from dataclasses import fields
from types import SimpleNamespace
import unittest

from gemma_pressure_prompts import FAMILIES, scenario
from gemma_pressure import ServingMetadata, peer_options
from gemma_pressure_audit import audit
from peer_tactics import filled_tactic, filled_tactic_from_slots
from scale_up import scale_up_scenario


class PromptTests(unittest.TestCase):
    def test_only_peer_text_and_provenance_change(self):
        for family in FAMILIES:
            for condition in ('recruiting', 'control'):
                base = scale_up_scenario('deploy-token-v2' if family == 'deploy-token-v2' else 'deploy-token',
                                        'consequence', condition, '96001',
                                        spray_row=None if family == 'deploy-token-v2' else family)
                combined = scenario(family, condition, 96001, reviewed=True)
                for field in fields(base):
                    if field.name in ('recruiter_system', 'metadata', 'scenario_version'):
                        continue
                    self.assertEqual(getattr(combined, field.name), getattr(base, field.name),
                                     (family, condition, field.name))
                expected_ids = [f'T{i}' for i in range(1, 8)
                                if not (family == 'dispatch-integration-code' and i == 6)]
                self.assertEqual(combined.metadata['tactic_ids'], expected_ids)
                slots = base.metadata.get('tactic_slots')
                texts = [filled_tactic_from_slots(slots, t, condition) if slots is not None else
                         filled_tactic(base.metadata['scenario_family'], t, condition) for t in expected_ids]
                self.assertEqual(combined.recruiter_system, base.recruiter_system + '\n\n' + '\n\n'.join(texts))
                if condition == 'control' and slots:
                    self.assertNotIn(slots['forbidden_ask'], '\n\n'.join(texts))

    def test_preview_is_not_live_approved(self):
        for family in FAMILIES:
            self.assertFalse(scenario(family, 'recruiting', 96001).recruiter_approved)
            self.assertTrue(scenario(family, 'recruiting', 96001, reviewed=True).recruiter_approved)


class RuntimeTests(unittest.TestCase):
    def test_peer_route_does_not_inherit_target_precision(self):
        price = {'provider': 'DeepSeek', 'prompt_cap': '.000001',
                 'completion_cap': '.000002', 'routing': {'order': ['DeepSeek'],
                 'only': ['DeepSeek'], 'allow_fallbacks': False, 'require_parameters': True}}
        opts = peer_options(price)['extra_body']
        self.assertNotIn('quantizations', opts['provider'])
        self.assertEqual(opts['reasoning'], {'enabled': True, 'effort': 'medium'})

    def test_reasoning_copy_is_detected(self):
        ep = {'status': 'complete', 'rounds_completed': 1, 'channel': [],
              'histories': {'target': []}, 'requests': [{'actor': 'recruiter',
              'response': {'provider': 'DeepSeek', 'choices': [{'message': {
              'reasoning': 'Private peer analysis.'}}]}}]}
        self.assertTrue(audit(ep)['reasoning_isolated'])
        ep['channel'].append({'content': 'Private peer analysis.'})
        self.assertFalse(audit(ep)['reasoning_isolated'])


class ProvenanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_precision_is_not_reported_as_response_precision(self):
        async def create(**payload):
            return {'provider': 'Example', 'usage': {'cost': .01}}
        wrapper = ServingMetadata(SimpleNamespace(create=create),
                                  {'model': {'endpoints': [{'provider_name': 'Example', 'quantization': 'fp8'}]}})
        response = await wrapper.create(model='model')
        self.assertNotIn('quantization', response)
        meta = response['screen_serving_metadata']
        self.assertIsNone(meta['reported_quantization'])
        self.assertEqual(meta['endpoint_precision_candidates'], ['fp8'])
        self.assertFalse(meta['precision_independently_verified'])

    async def test_unreported_provider_has_no_inferred_precision(self):
        async def create(**payload):
            return {'usage': {'cost': .01}}
        wrapper = ServingMetadata(SimpleNamespace(create=create), {'model': {'endpoints': []}})
        response = await wrapper.create(model='model')
        self.assertEqual(response['screen_serving_metadata']['endpoint_precision_candidates'], [])


if __name__ == '__main__':
    unittest.main()
