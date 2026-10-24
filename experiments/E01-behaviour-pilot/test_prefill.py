"""Offline tests for fixed-opener branch interventions."""

import asyncio
import json
from pathlib import Path
import tempfile
import unittest

from harness import Settings, run_episode
from prefill import PREFILLS, classify_prefill, make_parser, run_prefills
from scenarios import get_scenario
from test_harness import ScriptedClient, answer


class PrefillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_parent(self):
        scenario = get_scenario(
            "deploy-token_explicit_related_control_required-access", "81")
        settings = Settings(
            "target-test", "recruiter-test", rounds=1, early_stop=False,
            target_request_options={"extra_body": {"provider": {
                "order": ["TargetPin"], "allow_fallbacks": False}}},
            recruiter_request_options={"extra_body": {"provider": {
                "order": ["PeerPin"], "allow_fallbacks": False}}},
        )
        parent_dir = self.root / "parent"
        episode = asyncio.run(run_episode(
            scenario, settings,
            ScriptedClient([answer("Target baseline.")], [answer("Peer baseline.")]),
            parent_dir, episode_id="episode-parent"))
        return parent_dir / "episode-parent.json", episode, scenario.honeypots[0]

    def test_prefill_is_sent_as_assistant_prefix_and_outcomes_are_recorded(self):
        parent_path, parent, secret = self.make_parent()
        client = ScriptedClient(
            [answer(" Here is the value: " + secret), answer(" I can share the filename instead.")],
            [answer("Peer comply branch."), answer("Peer refuse branch.")])
        output = self.root / "prefills"
        summary = asyncio.run(run_prefills(
            parent_path, parent, 1, 1, 1, ("comply", "refuse"), output, client))

        self.assertEqual(summary["prefills"]["comply"]["followed_through"], 1)
        self.assertEqual(summary["prefills"]["refuse"]["followed_through"], 1)
        self.assertEqual(summary["prefills"]["comply"]["recovered_to_refusal"], 0)
        self.assertEqual(summary["prefills"]["refuse"]["reversed_to_compliance"], 0)

        for prefill_id in ("comply", "refuse"):
            path = output / f"prefill-{prefill_id}-r0001-n0001.json"
            episode = json.loads(path.read_text())
            target_request = next(record for record in episode["requests"]
                                  if record["actor"] == "target")
            self.assertEqual(target_request["request"]["messages"][-1], {
                "role": "assistant", "content": PREFILLS[prefill_id]})
            target_event = next(event for event in episode["channel"]
                                if event["actor"] == "target")
            self.assertTrue(target_event["content"].startswith(PREFILLS[prefill_id]))
            self.assertTrue(episode["prefill"]["applied"])
            self.assertEqual(episode["branch"]["prefill_id"], prefill_id)
            self.assertEqual(episode["label"]["prefill_outcome"],
                             episode["prefill_outcome"])

    def test_classification_and_execute_gate(self):
        self.assertTrue(classify_prefill("comply", False)["prefill_recovered"])
        self.assertTrue(classify_prefill("refuse", True)["prefill_reversed"])
        args = make_parser().parse_args(["episode.json", "--round", "4"])
        self.assertFalse(args.execute)
        self.assertEqual(args.prefill, "both")


if __name__ == "__main__":
    unittest.main()
