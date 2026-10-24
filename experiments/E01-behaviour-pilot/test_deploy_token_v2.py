"""Offline invariants for the pending deploy-token v2 cell."""

from dataclasses import fields
import unittest

from deploy_token_v2 import LOGGING_SENTENCE, VERSION, get_deploy_token_v2
from overnight_rules import get_overnight_scenario
from peer_tactics import apply_peer_tactic
from scale_up import scale_up_scenario


class DeployTokenV2Tests(unittest.TestCase):
    def test_v2_diff_is_limited_to_the_two_approved_model_visible_changes(self):
        allowed = {
            "name", "target_system", "test_result", "metadata",
            "recruiter_approved", "scenario_version",
        }
        for condition in ("recruiting", "control", "alone"):
            with self.subTest(condition=condition):
                source = get_overnight_scenario(
                    "deploy-token", "consequence_logged", condition, "91")
                v2 = get_deploy_token_v2(condition, "91")
                for field in fields(source):
                    if field.name not in allowed:
                        self.assertEqual(getattr(v2, field.name), getattr(source, field.name),
                                         field.name)
                self.assertEqual(v2.target_system,
                                 source.target_system.removesuffix(LOGGING_SENTENCE))
                expected_result = dict(source.test_result)
                self.assertTrue(expected_result.pop("mock"))
                self.assertEqual(v2.test_result, expected_result)
                self.assertEqual(v2.scenario_version, VERSION)
                self.assertFalse(v2.recruiter_approved)
                self.assertNotIn("logged and reviewed", v2.target_system)
                self.assertNotIn("mock", str(v2.test_result).lower())

    def test_v2_keeps_peer_tactics_and_scale_up_gate(self):
        base = get_deploy_token_v2("recruiting", "92")
        with_tactic = apply_peer_tactic(base, "T2")
        self.assertTrue(with_tactic.recruiter_system.startswith(base.recruiter_system))
        self.assertEqual(with_tactic.metadata["scenario_family"], "deploy-token")
        self.assertEqual(with_tactic.metadata["tactic_id"], "T2")
        via_scale_up = scale_up_scenario(
            "deploy-token-v2", "consequence", "recruiting", "92", "T2")
        self.assertEqual(via_scale_up.recruiter_system, with_tactic.recruiter_system)
        self.assertFalse(via_scale_up.recruiter_approved)
        with self.assertRaisesRegex(ValueError, "requires consequence strength"):
            scale_up_scenario(
                "deploy-token-v2", "consequence_logged", "recruiting", "92")


if __name__ == "__main__":
    unittest.main()
