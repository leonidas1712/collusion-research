import asyncio
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from harness import Settings, run_episode
from policy_sweep import prepare, ROOT
from scenarios import PRIVATE
from test_harness import ScriptedClient, answer, calls

SOURCE = ROOT / 'runs/20261024-0032-e01-harness/episodes/episode-0001.json'


class SweepTests(unittest.TestCase):
    def test_only_system_rule_changes_and_target_tools_execute(self):
        source = json.loads(SOURCE.read_text())
        original = next(r['request']['messages'] for r in source['requests'] if r['actor'] == 'target')
        scenario, prefix = prepare(SOURCE, 'soft')
        self.assertEqual(prefix['messages'][1:], original[1:])
        self.assertEqual(scenario.files, source['scenario_spec']['files'])
        self.assertFalse(scenario.peer_enabled)
        client = ScriptedClient([calls(('read', 'read_file', {'path': PRIVATE})), answer('I cannot share it.')])
        with tempfile.TemporaryDirectory() as directory:
            result = asyncio.run(run_episode(scenario, Settings('target-test', 'recruiter-test'),
                                             client, directory, target_prefix=prefix))
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(client.requests[0]['messages'], prefix['messages'])
        self.assertEqual(len(client.requests), 2)
        self.assertTrue(result['label']['token_in_context'])
        self.assertEqual(result['label']['first_peer_ask_round'], 1)
        self.assertEqual(result['condition']['execution'], 'frozen_peer_first_ask_target_turn')

    def test_target_history_and_resume_prefix_mismatches_are_rejected(self):
        scenario, prefix = prepare(SOURCE, 'firm')
        with tempfile.TemporaryDirectory() as directory:
            bad = copy.deepcopy(prefix)
            bad['messages'].append({'role': 'assistant', 'content': 'Earlier refusal'})
            with self.assertRaises(ValueError):
                asyncio.run(run_episode(scenario, Settings('target-test','recruiter-test'),
                                        ScriptedClient([]), directory, target_prefix=bad))
            asyncio.run(run_episode(scenario, Settings('target-test','recruiter-test'),
                                    ScriptedClient([answer()]), directory, target_prefix=prefix))
            changed = copy.deepcopy(prefix)
            changed['messages'][2]['content'] = 'Changed peer ask'
            with self.assertRaises(ValueError):
                asyncio.run(run_episode(scenario, Settings('target-test','recruiter-test'),
                                        ScriptedClient([]), directory, target_prefix=changed))
