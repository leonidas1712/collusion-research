"""Report denominator, partial-evidence and adjustment-gate checks without API calls."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from overnight_report import build_report


class OvernightReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cells = []

    def add_cell(self, condition, values, *, partial=False, fake=False, strength="plain", round=1):
        directory = self.root / f"run-{len(self.cells)}"
        directory.mkdir()
        self.cells.append({"target_model": "target", "provider": "provider", "scenario_family": "scenario",
                           "strength": strength, "condition": condition, "sweep_round": round,
                           "run_id": directory.name, "run_dir": directory.name})
        for index, success in enumerate(values):
            episode = {"episode_id": f"episode-{index}", "status": "incomplete" if partial else "complete",
                       "fake": fake, "settings": {"target_model": "target", "recruiter_model": "peer"},
                       "scenario_spec": {"peer_enabled": condition != "alone"},
                       "requests": [{"actor": "target", "served_provider": "provider"}],
                       "_score": {"objective_success": success, "boundary_violation": success,
                                  "first_action_round": 2 if success else None,
                                  "setup_ready": not partial, "valid_for_comparison": not partial and not fake,
                                  "task_success": True, "control_task_success": True,
                                  "exposure_requirement_met": True, "eligible_resisted": not success}}
            suffix = ".partial.json" if partial else ".json"
            (directory / f"episode-{index}{suffix}").write_text(json.dumps(episode))
        return directory

    def report(self, **extra):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"cells": self.cells, "cost_ledger": {"spent_usd": 1.23},
                                        "reference_runs": ["old-explicit-pilot"], **extra}))
        with patch("overnight_report.score_episode", side_effect=lambda episode: episode["_score"]):
            return build_report(manifest, self.root / "report")

    def test_all_and_none_completed_with_clean_alone_allow_adjustment(self):
        for strength, successes in (("strong", [False] * 5), ("weak", [True] * 5)):
            self.add_cell("recruiting", successes, strength=strength)
            self.add_cell("alone", [False, False], strength=strength)
        report = self.report()
        self.assertEqual(len(report["round_two_candidates"]), 2)
        self.assertEqual({group["round_two"]["completed_recruiting_outcome"] for group in report["groups"]}, {"all", "none"})
        self.assertEqual(report["cost_ledger"]["spent_usd"], 1.23)
        self.assertIn("old-explicit-pilot", (self.root / "report/report.md").read_text())

    def test_mixed_or_alone_violation_blocks_adjustment(self):
        self.add_cell("recruiting", [True, False, False, False, False], strength="mixed")
        self.add_cell("alone", [False, False], strength="mixed")
        self.add_cell("recruiting", [True] * 5, strength="unclean")
        self.add_cell("alone", [True, False], strength="unclean")
        self.assertEqual(self.report()["round_two_candidates"], [])

    def test_incomplete_positive_is_separate_from_completed_denominator(self):
        self.add_cell("recruiting", [False] * 4)
        self.add_cell("recruiting", [True], partial=True)
        self.add_cell("alone", [False, False])
        report = self.report()
        stats = report["groups"][0]["conditions"]["recruiting"]
        self.assertEqual((stats["objective_success"], stats["completed"], stats["incomplete"], stats["observed_objective_incomplete"]), (0, 4, 1, 1))
        self.assertEqual(stats["incomplete_first_action_rounds"], [2])
        self.assertEqual(report["round_two_candidates"], [])

    def test_final_supersedes_partial_and_attempts_are_not_extra_episodes(self):
        directory = self.add_cell("recruiting", [False] * 5)
        original = (directory / "episode-0.json").read_text()
        (directory / "episode-0.partial.json").write_text(original)
        (directory / "episode-0.attempt-1.json").write_text(original)
        self.add_cell("alone", [False, False])
        report = self.report()
        self.assertEqual(report["groups"][0]["conditions"]["recruiting"]["episodes"], 5)
        self.assertEqual(len(report["round_two_candidates"]), 1)

    def test_fake_unreadable_and_round_two_do_not_trigger_more_runs(self):
        self.add_cell("recruiting", [False] * 5, fake=True, strength="fake")
        self.add_cell("alone", [False, False], strength="fake")
        directory = self.add_cell("recruiting", [False] * 5, strength="broken")
        (directory / "episode-0.json").write_text("broken json")
        self.add_cell("alone", [False, False], strength="broken")
        self.add_cell("recruiting", [False] * 5, strength="later", round=2)
        self.add_cell("alone", [False, False], strength="later", round=2)
        report = self.report()
        self.assertEqual(report["round_two_candidates"], [])
        self.assertTrue(report["warnings"])

    def test_review_metadata_and_absolute_budget_ledger(self):
        directory = self.add_cell("alone", [False, False])
        for index in range(2):
            path = directory / f"episode-{index}.json"
            episode = json.loads(path.read_text())
            if index == 0:
                episode["scenario_spec"]["metadata"] = {"review_status": "pending post-hoc review"}
            else:
                episode["condition"] = {"review_status": "pending post-hoc review"}
            path.write_text(json.dumps(episode))
        ledger = self.root / "budget.json"
        ledger.write_text(json.dumps({"reported_cost_usd": "0.25", "charged_or_reserved_usd": "0.50",
                                      "calls": [{"private_detail": "DO_NOT_DUMP_CALLS"}]}))
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"cells": self.cells, "cost_ledger": str(ledger)}))
        with patch("overnight_report.score_episode", side_effect=lambda episode: episode["_score"]):
            report = build_report(manifest, self.root / "report")
        self.assertEqual(report["reported_cost_usd"], "0.25")
        self.assertEqual(report["charged_or_reserved_usd"], "0.50")
        self.assertEqual(report["groups"][0]["conditions"]["alone"]["review_status"], {"pending post-hoc review": 2})
        self.assertNotIn("DO_NOT_DUMP_CALLS", (self.root / "report/report.md").read_text())
        ledger.unlink()
        with patch("overnight_report.score_episode", side_effect=lambda episode: episode["_score"]):
            missing = build_report(manifest, self.root / "report")
        self.assertIsNone(missing["reported_cost_usd"])
        self.assertTrue(any("cost_ledger_error" in warning for warning in missing["warnings"]))

    def test_disclosure_kind_is_only_counted_when_supplied_and_partials_separate(self):
        directory = self.add_cell("recruiting", [True, True, True, False])
        for index, kind in enumerate(("deliberate", "incidental", None, "none")):
            path = directory / f"episode-{index}.json"
            episode = json.loads(path.read_text())
            if kind is not None:
                episode["_score"].update(disclosure_kind=kind, disclosure_kind_method="context_heuristic")
            path.write_text(json.dumps(episode))
        partial = self.add_cell("recruiting", [True], partial=True) / "episode-0.partial.json"
        episode = json.loads(partial.read_text())
        episode["_score"]["disclosure_kind"] = "unclear"
        partial.write_text(json.dumps(episode))
        report = self.report()
        stats = report["groups"][0]["conditions"]["recruiting"]
        self.assertEqual(stats["objective_success"], 3)
        self.assertEqual(stats["disclosure_kind_counts"], {"deliberate": 1, "incidental": 1, "none": 1})
        self.assertEqual(stats["incomplete_disclosure_kind_counts"], {"unclear": 1})
        self.assertEqual(stats["disclosure_kind_methods"], {"context_heuristic": 3})
        text = (self.root / "report/report.md").read_text()
        self.assertIn("2 of 3", text)
        self.assertIn("1001–1005", text)
        self.assertIn("no control draws or peer-text fix", text)

    def test_explicit_362_expansion_supersedes_extreme_gate_and_preserves_waves(self):
        self.add_cell("recruiting", [True, False, False, False])
        self.add_cell("recruiting", [True], partial=True)
        self.add_cell("alone", [False, False])
        self.add_cell("recruiting", [True, False] * 4, round=2)
        self.add_cell("alone", [False, False], round=2)
        report = self.report(selection_policy="explicit_expansion_362", final_wave_authorization="explicit three-cell final-wave authorization",
                             round_two_plan=[{"target": "32b", "scenario_family": "deploy-token", "strength": "consequence", "sweep_round": 2}])
        self.assertEqual(report["round_two_candidates"], [])
        self.assertEqual(report["final_wave_design"]["planned_episodes"], 30)
        self.assertEqual(report["final_wave_design"]["recruiting_families"], list(range(1001, 1009)))
        first, second = report["groups"]
        self.assertEqual(first["conditions"]["recruiting"]["completed"], 4)
        self.assertEqual(first["conditions"]["recruiting"]["observed_objective_incomplete"], 1)
        self.assertEqual(second["conditions"]["recruiting"]["completed"], 8)
        self.assertEqual(second["conditions"]["recruiting"]["objective_success"], 4)
        self.assertIsNone(first["round_two"]["recommendation"])
        text = (self.root / "report/report.md").read_text()
        self.assertIn("mixed outcomes are permitted", text)
        self.assertIn("not replaced or overwritten", text)
        self.assertIn("explicit final-wave outcomes", text)


if __name__ == "__main__":
    unittest.main()
