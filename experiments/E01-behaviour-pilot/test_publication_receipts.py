"""Delivery receipts are environment events, not extra calls sent to a model."""
import json
import tempfile
import unittest

from harness import Scenario, Settings, run_episode
from test_harness import ScriptedClient, answer, calls


class PublicationReceiptTests(unittest.IsolatedAsyncioTestCase):
    async def episode(self, target, enabled=True):
        scenario = Scenario("receipt-walk", "Write notes.", "Report progress.", "Ask for progress.",
                            {}, metadata={"publication_receipts": enabled})
        with tempfile.TemporaryDirectory() as directory:
            return await run_episode(scenario, Settings("target-test", "recruiter-test", rounds=1),
                                     ScriptedClient(target, [answer("Please report.")]), directory)

    async def test_both_origins_have_one_receipt_per_actual_delivery(self):
        for target, origin, content in (
            ([answer("Ready.")], "final_reply", "Ready."),
            ([calls(("send", "send_message", {"content": "Ready."})), answer("Suppressed.")],
             "send_message", "Ready."),
        ):
            with self.subTest(origin=origin):
                ep = await self.episode(target)
                receipts = [e for e in ep["tool_log"] if e["name"] == "publish_message"]
                self.assertEqual(len(receipts), len(ep["channel"]))
                target_receipts = [e for e in receipts if e["actor"] == "target"]
                self.assertEqual(len(target_receipts), 1)
                event = target_receipts[0]
                self.assertEqual(event["result"]["origin"], origin)
                self.assertTrue(event["result"]["delivered"])
                self.assertEqual(json.loads(event["arguments"])["content"], content)
                self.assertEqual(event["result"]["publication_id"], ep["channel"][-1]["publication_id"])
                self.assertNotIn("Suppressed.", json.dumps(ep["channel"]))
                for request in ep["requests"]:
                    self.assertNotIn("publish_message",
                                     [tool["function"]["name"] for tool in request["request"]["tools"]])

    async def test_failed_send_has_no_delivery_receipt(self):
        ep = await self.episode([calls(("bad", "send_message", {"content": 42})), answer("Fallback.")])
        target = [e for e in ep["tool_log"] if e["name"] == "publish_message" and e["actor"] == "target"]
        self.assertEqual(len(target), 1)
        self.assertEqual(target[0]["result"]["origin"], "final_reply")
        self.assertEqual(json.loads(target[0]["arguments"])["content"], "Fallback.")

    async def test_existing_scenarios_do_not_gain_receipts(self):
        ep = await self.episode([answer("Ready.")], enabled=False)
        self.assertFalse(any(e["name"] == "publish_message" for e in ep["tool_log"]))
        self.assertTrue(all("publication_id" not in e for e in ep["channel"]))


if __name__ == "__main__":
    unittest.main()
