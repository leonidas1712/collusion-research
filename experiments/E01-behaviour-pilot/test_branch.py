"""Offline exact-reconstruction and forced-continuation tests."""

import asyncio
import copy
import json
from pathlib import Path
import tempfile
import unittest

from branch import (
    estimate_cost, load_parent, reconstruct_checkpoint, resolve_scenario,
    run_branches, select_branch_points,
    validate_branch_point,
)
from harness import Settings, run_episode
from scenarios import get_scenario
from test_harness import ScriptedClient, answer, calls


class BranchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_parent(self):
        scenario = get_scenario(
            "deploy-token_explicit_related_control_required-access", "71")
        settings = Settings(
            "target-test", "recruiter-test", rounds=3, early_stop=False,
            target_request_options={"extra_body": {"provider": {
                "order": ["TargetPin"], "allow_fallbacks": False}}},
            recruiter_request_options={"extra_body": {"provider": {
                "order": ["PeerPin"], "allow_fallbacks": False}}},
        )
        client = ScriptedClient([
            calls(("write-1", "write_file", {
                "path": "handoff/status.txt", "content": "round-one"})),
            answer("I updated the summary."),
            answer("Round two target."),
            answer("Round three target."),
        ], [answer("Round one peer."), answer("Round two peer."), answer("Round three peer.")])
        episode = asyncio.run(run_episode(
            scenario, settings, client, self.root / "parent", episode_id="episode-parent"))
        path = self.root / "parent" / "episode-parent.json"
        return path, episode

    def test_checkpoint_restores_histories_channel_files_and_provider_settings(self):
        path, parent = self.make_parent()
        _, loaded = load_parent(path)
        scenario = resolve_scenario(loaded)
        checkpoint = reconstruct_checkpoint(loaded, 2, scenario)
        self.assertEqual(checkpoint["round"], 1)
        self.assertEqual(checkpoint["files"]["handoff/status.txt"], "round-one")
        self.assertTrue(all(event["round"] < 2 for event in checkpoint["channel"]))
        self.assertTrue(all(event["round"] < 2 for event in checkpoint["tool_log"]))
        target = checkpoint["histories"]["target"]
        self.assertIn("Round one peer.", json.dumps(target))
        self.assertNotIn("Round two peer.", json.dumps(target))
        final_checkpoint = reconstruct_checkpoint(loaded, 4, scenario)
        self.assertEqual(final_checkpoint["files"], loaded["files"])
        self.assertEqual(final_checkpoint["histories"], loaded["histories"])
        estimate = estimate_cost(parent, 3, 5)
        self.assertEqual(estimate["actor_turns"], 30)

    def test_replay_drift_is_rejected(self):
        path, parent = self.make_parent()
        drifted = copy.deepcopy(parent)
        write = next(event for event in drifted["tool_log"] if event["name"] == "write_file")
        write["result"] = {"written": "different.txt"}
        with self.assertRaisesRegex(ValueError, "Tool replay drift"):
            reconstruct_checkpoint(drifted, 2, resolve_scenario(drifted))
        self.assertTrue(path.exists())

    def test_forced_branches_save_parent_links_and_exact_window(self):
        path, parent = self.make_parent()
        client = ScriptedClient(
            [answer("branch target one"), answer("branch target two")],
            [answer("branch peer one"), answer("branch peer two")])
        output = self.root / "branches"
        summary = asyncio.run(run_branches(path, parent, 2, 1, 2, output, client))
        self.assertEqual(summary["branches_complete"], 2)
        self.assertEqual(summary["share_forbidden_within_window"], 0)
        for index in (1, 2):
            branch = json.loads((output / f"branch-r0002-n{index:04}.json").read_text())
            self.assertEqual(branch["branch"]["parent_episode_id"], "episode-parent")
            self.assertEqual(branch["branch"]["branch_round"], 2)
            self.assertEqual(branch["rounds_completed"], 2)
            self.assertEqual(branch["stop_reason"], "forced_continuation_complete")
            peer_request = next(record for record in branch["requests"]
                                if record["actor"] == "recruiter")
            target_request = next(record for record in branch["requests"]
                                  if record["actor"] == "target")
            self.assertEqual(peer_request["request_body"]["provider"]["order"], ["PeerPin"])
            self.assertEqual(target_request["request_body"]["provider"]["order"], ["TargetPin"])

    def test_selection_stratifies_outcome_and_phase(self):
        paths = []
        for index, (condition, positive) in enumerate((
                ("recruiting", False), ("recruiting", True), ("control", False))):
            for copy_index in range(2):
                path = self.root / f"episode-{index}-{copy_index}.json"
                payload = {
                    "status": "complete", "rounds_completed": 12,
                    "scenario_spec": {"peer_enabled": True},
                    "condition": {"peer_condition": condition},
                    "label": {"objective_success": positive,
                              "first_action_round": 7 if positive else None},
                }
                path.write_text(json.dumps(payload))
                paths.append(path)
        selected = select_branch_points(paths, limit=12, seed=4)
        self.assertEqual(len(selected), 12)
        self.assertEqual({item["outcome"] for item in selected},
                         {"held", "give-in", "control"})
        self.assertEqual({item["phase"] for item in selected}, {"early", "late"})
        self.assertTrue(all(item["round"] <= 7 for item in selected
                            if item["outcome"] == "give-in"))

    def test_branch_point_after_parent_action_is_rejected(self):
        episode = {"label": {"objective_success": True, "first_action_round": 4}}
        validate_branch_point(episode, 4)
        with self.assertRaisesRegex(ValueError, "after the parent's first forbidden action"):
            validate_branch_point(episode, 5)


if __name__ == "__main__":
    unittest.main()
