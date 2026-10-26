import importlib.util
import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("e08_counterfactual", HERE / "counterfactual.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class CounterfactualTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads((HERE / "plan.json").read_text())
        cls.scenario = "dispatch-integration-code"
        forbid = cls.plan["rule_texts_by_scenario"][cls.scenario]["FORBID"]
        cls.request = {
            "model": "qwen/qwen3-32b",
            "messages": [{"role": "system", "content": "Prefix. " + forbid + " Consequence."}, {"role": "user", "content": "Task"}],
        }

    def test_forbid_is_identity_and_other_edits_are_scoped(self):
        forbid = module.edit_request(self.request, self.scenario, "FORBID", self.plan)
        self.assertEqual(forbid, self.request)
        for condition in ("PERMIT", "NEUTRAL_EDIT"):
            edited = module.edit_request(self.request, self.scenario, condition, self.plan)
            expected = self.plan["rule_texts_by_scenario"][self.scenario][condition]
            self.assertIn(expected, edited["messages"][0]["content"])
            self.assertEqual(edited["messages"][1:], self.request["messages"][1:])
            restored = json.loads(json.dumps(edited))
            restored["messages"][0]["content"] = self.request["messages"][0]["content"]
            self.assertEqual(restored, self.request)

    def test_plan_is_frozen_and_balanced(self):
        self.assertEqual(self.plan["status"], "frozen_before_gpu")
        calls = self.plan["calls"]
        self.assertEqual(len(calls), 150)
        self.assertEqual(sum(call["class"] == "leaking" for call in calls), 38)
        self.assertEqual(sum(call["class"] == "non_leaking" for call in calls), 112)
        self.assertEqual(len({call["call_id"] for call in calls}), 150)
        positives = {(call["scenario"], call["round"]) for call in calls if call["class"] == "leaking"}
        self.assertTrue(all((call["scenario"], call["round"]) in positives for call in calls if call["class"] == "non_leaking"))


if __name__ == "__main__":
    unittest.main()
