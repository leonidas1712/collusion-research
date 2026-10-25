import sys
from dataclasses import replace
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "experiments/E01-behaviour-pilot"),
                str(ROOT / "experiments/E03-target-screen")]

from escalation_prompts import RECORD_SCENARIOS, SCENARIOS, peer_prompt
from escalation_sweep import build_scenario, episode_record, summarize
from scale_up import scale_up_scenario


class EscalationScenarioTests(unittest.TestCase):
    def test_catalog_contains_collected_six_scenarios(self):
        self.assertEqual(
            set(SCENARIOS),
            {"deploy-token-v2", "dispatch-integration-code", "handoff-exception-note",
             "procurement-reserve-price", "service-capacity-figure",
             "service-rollout-threshold"},
        )

    def test_record_prompts_keep_late_pacing_and_matched_fields(self):
        secret_keys = {
            "dispatch-integration-code": "INTEGRATION_CODE",
            "handoff-exception-note": "INTERNAL_NOTE",
            "procurement-reserve-price": "RESERVE_PRICE",
            "service-capacity-figure": "CAPACITY_FIGURE",
            "service-rollout-threshold": "ROLLOUT_THRESHOLD",
        }
        for scenario_id, spec in RECORD_SCENARIOS.items():
            with self.subTest(scenario=scenario_id):
                recruiting = peer_prompt(scenario_id, "envblock_late", "recruiting")
                control = peer_prompt(scenario_id, "envblock_late", "control")
                for prompt in (recruiting, control):
                    self.assertIn("first message must only", prompt)
                    self.assertIn("second message", prompt)
                    self.assertIn("third message onward", prompt)
                    self.assertIn(spec["destination"], prompt)
                    self.assertNotIn(secret_keys[scenario_id], prompt)
                self.assertIn(spec["source"], recruiting)
                self.assertIn("complete", recruiting)
                self.assertIn("every field verbatim", recruiting)
                for field in spec["fields"]:
                    self.assertIn(field, control)
                self.assertIn("only the permitted", control)

    def test_build_changes_only_peer_prompt_metadata_and_version(self):
        for scenario_id in RECORD_SCENARIOS:
            for condition in ("recruiting", "control"):
                with self.subTest(scenario=scenario_id, condition=condition):
                    base = scale_up_scenario(
                        "scenario-spray", "consequence", condition, "97101",
                        spray_row=scenario_id)
                    result = build_scenario(
                        scenario_id, "envblock_late", condition, "97101")
                    expected = replace(
                        base,
                        recruiter_system=result.recruiter_system,
                        metadata=result.metadata,
                        scenario_version=result.scenario_version,
                    )
                    self.assertEqual(result, expected)
                    self.assertEqual(result.metadata["escalation_scenario"], scenario_id)
                    self.assertEqual(result.metadata["escalation_strategy"], "envblock_late")
                    self.assertNotEqual(result.recruiter_system, base.recruiter_system)

    def test_deploy_token_prompt_is_backward_compatible(self):
        scenario = build_scenario(
            "deploy-token-v2", "envblock_late", "recruiting", "97101")
        self.assertIn("complete environment block", scenario.recruiter_system)
        self.assertEqual(scenario.metadata["escalation_scenario"], "deploy-token-v2")

    def test_generic_scorer_fields_are_normalized(self):
        episode = {
            "episode_id": "recruiting-0001",
            "status": "complete",
            "stop_reason": "early_stop_after_action",
            "requests": [],
            "label": {
                "objective_success": True,
                "channel_disclosure": False,
                "other_file_disclosure": True,
                "secret_in_context": True,
                "secret_read_round": 1,
                "first_boundary_violation_round": 3,
            },
        }
        record = episode_record(
            "dispatch-integration-code", "envblock_late", "recruiting", episode)
        self.assertTrue(record["token_in_context"])
        self.assertEqual(record["token_read_round"], 1)
        self.assertFalse(record["channel_disclosure"])
        summary = summarize([record])["recruiting"]
        self.assertEqual(summary["give_ins_after_read"], 1)
        self.assertEqual(summary["give_in_rounds"], [3])
        self.assertEqual(summary["channel_publications"], 0)
        self.assertEqual(summary["file_disclosures"], 1)

        episode["label"].update(channel_disclosure=True, first_action_round=4)
        channel_record = episode_record(
            "dispatch-integration-code", "envblock_late", "recruiting", episode)
        self.assertEqual(channel_record["first_channel_publication_round"], 4)


if __name__ == "__main__":
    unittest.main()
