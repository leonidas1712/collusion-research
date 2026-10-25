import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "experiments/E01-behaviour-pilot"),
                str(ROOT / "experiments/E03-target-screen")]

from finalize_gpt_oss_collection import exclusion_reason


class FinalizeCollectionTests(unittest.TestCase):
    def test_exclusion_precedence(self):
        self.assertEqual(exclusion_reason({"status": "incomplete"}), "incomplete")
        self.assertIsNone(exclusion_reason({"status": "complete", "token_in_context": False}))
        self.assertIsNone(exclusion_reason({"status": "complete", "token_in_context": True,
                                            "valid_for_comparison": False}))
        self.assertIsNone(exclusion_reason({"status": "complete", "token_in_context": True,
                                            "valid_for_comparison": True}))


if __name__ == "__main__":
    unittest.main()
