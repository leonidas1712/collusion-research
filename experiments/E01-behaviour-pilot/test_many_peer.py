"""Offline many-to-one channel tests."""

import asyncio
import json
from pathlib import Path
import tempfile
import unittest

from harness import Settings
from many_peer import prepare_many_peer_scenario, render_review, run_many_peer_episode
from overnight_rules import get_overnight_scenario
from scale_up import main as scale_up_main, make_parser, scale_up_scenario
from scenarios import get_scenario
from test_harness import ScriptedClient, answer


class ManyPeerTests(unittest.TestCase):
    def test_one_peer_scenario_path_is_equal_to_existing_path(self):
        baseline = scale_up_scenario(
            "deploy-token", "consequence_logged", "recruiting", "81")
        explicit_one = scale_up_scenario(
            "deploy-token", "consequence_logged", "recruiting", "81", peers=1)
        self.assertEqual(explicit_one, baseline)
        self.assertEqual(make_parser().parse_args([]).peers, 1)

    def test_two_and_three_peer_variants_are_pending_and_have_distinct_prompts(self):
        base = get_scenario(
            "deploy-token_explicit_related_recruiting_required-access", "82")
        for count in (2, 3):
            with self.subTest(count=count):
                scenario = prepare_many_peer_scenario(base, count)
                self.assertFalse(scenario.recruiter_approved)
                self.assertEqual(scenario.metadata["peer_count"], count)
                self.assertEqual(len(scenario.metadata["peer_prompts"]), count)
                self.assertEqual(len(set(scenario.metadata["peer_prompts"])), count)
                self.assertIn("pending Leo review", scenario.metadata["many_to_one_review_status"])

    def test_peers_speak_in_order_then_target_and_all_receive_channel_messages(self):
        base = get_scenario(
            "deploy-token_explicit_related_control_required-access", "83")
        scenario = prepare_many_peer_scenario(base, 3)
        settings = Settings("target-test", "recruiter-test", rounds=1, early_stop=False)
        client = ScriptedClient(
            [answer("Target reply.")],
            [answer("Peer one."), answer("Peer two."), answer("Peer three.")])
        with tempfile.TemporaryDirectory() as directory:
            result = asyncio.run(run_many_peer_episode(
                scenario, settings, client, directory, episode_id="many"))
            saved = json.loads((Path(directory) / "many.json").read_text())
        self.assertEqual(result["status"], "complete")
        self.assertEqual([record["actor"] for record in result["requests"]],
                         ["recruiter", "recruiter-2", "recruiter-3", "target"])
        self.assertEqual([event["actor"] for event in result["channel"]],
                         ["recruiter", "recruiter-2", "recruiter-3", "target"])
        target_request = result["requests"][-1]["request"]["messages"]
        self.assertIn("Peer one.", json.dumps(target_request))
        self.assertIn("Peer two.", json.dumps(target_request))
        self.assertIn("Peer three.", json.dumps(target_request))
        first_peer_history = result["histories"]["recruiter"]
        self.assertIn("Target reply.", json.dumps(first_peer_history))
        self.assertEqual(saved["scenario_spec"]["metadata"]["peer_count"], 3)
        self.assertFalse(saved["scenario_spec"]["metadata"]["recruiter_approved"])

    def test_scale_up_flag_builds_pending_cells_but_leaves_alone_unchanged(self):
        args = make_parser().parse_args(["--peers", "3"])
        self.assertEqual(args.peers, 3)
        peer = scale_up_scenario(
            "deploy-token", "consequence_logged", "control", "84", peers=3)
        alone = scale_up_scenario(
            "deploy-token", "consequence_logged", "alone", "84", peers=3)
        self.assertEqual(peer.metadata["peer_count"], 3)
        self.assertFalse(peer.recruiter_approved)
        self.assertNotIn("peer_count", alone.metadata)

    def test_existing_publication_receipt_scorer_is_unchanged(self):
        base = get_overnight_scenario(
            "minimum-price", "consequence_logged", "recruiting", "85")
        scenario = prepare_many_peer_scenario(base, 2)
        minimum = scenario.initial_state["minimum_price"]
        settings = Settings("target-test", "recruiter-test", rounds=1, early_stop=False)
        client = ScriptedClient(
            [answer(f"The minimum price is {minimum}.")],
            [answer("Peer one."), answer("Peer two.")])
        with tempfile.TemporaryDirectory() as directory:
            result = asyncio.run(run_many_peer_episode(
                scenario, settings, client, directory, episode_id="receipt"))
        receipts = [event for event in result["tool_log"]
                    if event.get("event_type") == "channel_delivery"
                    and event["actor"] == "target"]
        self.assertTrue(receipts)
        self.assertTrue(result["label"]["objective_success"])

    def test_review_file_matches_generated_prompts(self):
        self.assertEqual(Path(__file__).with_name("MANY_TO_ONE_REVIEW.md").read_text(),
                         render_review())

    def test_live_scale_up_is_blocked_before_client_setup(self):
        args = make_parser().parse_args([
            "--peers", "2", "--recruiting", "1", "--control", "0", "--alone", "0"])
        with self.assertRaisesRegex(RuntimeError, "pending Leo review"):
            asyncio.run(scale_up_main(args))


if __name__ == "__main__":
    unittest.main()
