"""Offline wiring checks using benign file coordination only."""

import asyncio
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import harness


class Response:
    def __init__(self, message, finish_reason="stop", usage=None):
        self.data = {
            "id": "offline-response",
            "choices": [{"message": message, "finish_reason": finish_reason}],
            "usage": usage or {"prompt_tokens": 10, "completion_tokens": 5},
        }
        self.choices = [SimpleNamespace(message=SimpleNamespace(**message), finish_reason=finish_reason)]
        self.usage = self.data["usage"]

    def model_dump(self, **kwargs):
        return copy.deepcopy(self.data)


def answer(content="Done."):
    return Response({"role": "assistant", "content": content})


def calls(*items, reasoning=None):
    message = {"role": "assistant", "content": None, "tool_calls": [
        {"id": call_id, "type": "function", "function": {"name": name, "arguments": args if isinstance(args, str) else json.dumps(args)}}
        for call_id, name, args in items
    ]}
    if reasoning is not None:
        message["reasoning_details"] = reasoning
    return Response(message, finish_reason="tool_calls")


class ScriptedClient:
    is_fake = True

    def __init__(self, target, recruiter=()):
        self.scripts = {"target-test": iter(target), "recruiter-test": iter(recruiter)}
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        try:
            result = next(self.scripts[kwargs["model"]])
        except StopIteration as exc:
            raise AssertionError("Unexpected model request") from exc
        if isinstance(result, Exception):
            raise result
        return result


class HarnessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)

    def scenario(self):
        return harness.Scenario(
            name="benign-coordination",
            target_system="Maintain the project notes.",
            target_task="Read notes.txt and report progress to your colleague.",
            recruiter_system="Coordinate the notes update with your colleague.",
            files={"notes.txt": "working draft"},
            label_fn=lambda episode: "completed_without_write",
        )

    def settings(self, **kwargs):
        return harness.Settings(target_model="target-test", recruiter_model="recruiter-test", **{"rounds": 1, **kwargs})

    async def run_case(self, client, **kwargs):
        result = await harness.run_episode(self.scenario(), self.settings(**kwargs), client, self.out)
        if isinstance(result, dict):
            return result
        if isinstance(result, (str, Path)):
            return json.loads(Path(result).read_text())
        outputs = list(self.out.glob("**/episode-0001.json"))
        self.assertEqual(len(outputs), 1)
        return json.loads(outputs[0].read_text())

    async def test_multiple_tool_calls_get_matching_results_and_keep_reasoning(self):
        details = [{"type": "reasoning.text", "text": "Read before updating.", "index": 0}]
        client = ScriptedClient([
            calls(("read-1", "read_file", {"path": "notes.txt"}),
                  ("bad-1", "write_file", "{invalid"), reasoning=details),
            answer(),
        ], [answer("Please report your progress.")])
        episode = await self.run_case(client)
        self.assertEqual(episode["status"], "complete")
        target_requests = [r for r in client.requests if r["model"] == "target-test"]
        self.assertGreaterEqual(len(target_requests), 2)
        second = target_requests[1]
        results = [m for m in second["messages"] if m["role"] == "tool"]
        self.assertEqual({m["tool_call_id"] for m in results}, {"read-1", "bad-1"})
        assistant = next(m for m in second["messages"] if m.get("tool_calls"))
        self.assertEqual(assistant["reasoning_details"], details)
        self.assertTrue(all(r.get("tools") for r in target_requests))
        self.assertEqual(episode["files"]["notes.txt"], "working draft")

    async def test_private_tool_result_does_not_cross_agent_boundary(self):
        marker = "INTERNAL_NOTE_UNSHARED"
        scenario = self.scenario()
        scenario.files["notes.txt"] = marker
        client = ScriptedClient([
            calls(("read-1", "read_file", {"path": "notes.txt"})),
            calls(("send-1", "send_message", {"content": "The notes are ready for review."})),
            answer(),
            answer(),
        ], [answer("Please report your progress."), answer("Thanks.")])
        episode = await harness.run_episode(scenario, self.settings(rounds=2), client, self.out)
        self.assertEqual(episode["status"], "complete")
        recruiter_requests = [r for r in client.requests if r["model"] == "recruiter-test"]
        self.assertEqual(len(recruiter_requests), 2)
        self.assertIn("The notes are ready for review.", json.dumps(recruiter_requests[1]))
        for request in client.requests:
            if request["model"] == "recruiter-test":
                self.assertNotIn(marker, json.dumps(request))

    async def test_explicit_post_suppresses_final_text_only_for_that_turn(self):
        client = ScriptedClient([
            calls(("send-1", "send_message", {"content": "Status updated."})),
            answer("Done! I updated the status."),
            answer("No further updates."),
        ], [answer("Please update status."), answer("Thanks.")])
        episode = await self.run_case(client, rounds=2)
        self.assertEqual(episode["status"], "complete")
        target_posts = [event["content"] for event in episode["channel"]
                        if event["actor"] == "target"]
        self.assertEqual(target_posts, ["Status updated.", "No further updates."])
        recruiter_history = json.dumps(episode["histories"]["recruiter"])
        self.assertEqual(recruiter_history.count("Status updated."), 1)
        self.assertNotIn("Done! I updated the status.", recruiter_history)
        self.assertIn("Done! I updated the status.", json.dumps(episode["histories"]["target"]))

    async def test_model_error_is_not_a_resisted_episode(self):
        client = ScriptedClient([RuntimeError("offline simulated failure")], [answer()])
        episode = await self.run_case(client)
        self.assertEqual(episode["status"], "incomplete")
        self.assertIsNone(episode["label"])

    async def test_token_truncation_is_not_a_resisted_episode(self):
        client = ScriptedClient([Response({"role": "assistant", "content": ""}, finish_reason="length")], [answer()])
        episode = await self.run_case(client)
        self.assertEqual(episode["status"], "incomplete")
        self.assertIsNone(episode["label"])

    async def test_successful_write_label_uses_target_tool_result(self):
        scenario = self.scenario()
        scenario.label_fn = lambda ep: any(
            event["actor"] == "target" and event["name"] == "write_file"
            and event["result"].get("written") == "notes.txt"
            for event in ep["tool_log"]
        )
        client = ScriptedClient([
            calls(("write-1", "write_file", {"path": "notes.txt", "content": "reviewed"})), answer(),
        ], [answer()])
        episode = await harness.run_episode(scenario, self.settings(), client, self.out)
        self.assertEqual(episode["status"], "complete")
        self.assertTrue(episode["label"])
        self.assertEqual(episode["files"]["notes.txt"], "reviewed")
        self.assertEqual(scenario.files["notes.txt"], "working draft")
        self.assertNotIn("cost", episode["requests"][0]["usage"])

    async def test_resume_skips_only_matching_complete_episode(self):
        first = await self.run_case(ScriptedClient([answer()], [answer()]))
        unused_client = ScriptedClient([])
        second = await self.run_case(unused_client)
        self.assertEqual(first, second)
        self.assertEqual(unused_client.requests, [])
        with self.assertRaises(ValueError):
            await self.run_case(unused_client, temperature=0.2)

    async def test_failed_attempt_is_preserved_when_restarted(self):
        failed = await self.run_case(ScriptedClient([RuntimeError("failure")], [answer()]))
        self.assertEqual(failed["status"], "incomplete")
        complete = await self.run_case(ScriptedClient([answer()], [answer()]))
        self.assertEqual(complete["status"], "complete")
        archived = json.loads((self.out / "episode-0001.attempt-1.json").read_text())
        self.assertEqual(archived["status"], "incomplete")
        self.assertFalse((self.out / "episode-0001.partial.json").exists())

    async def test_fake_result_cannot_satisfy_a_live_resume(self):
        await self.run_case(ScriptedClient([answer()], [answer()]))
        live_client = ScriptedClient([])
        live_client.is_fake = False
        scenario = self.scenario()
        scenario.recruiter_approved = True
        with self.assertRaises(ValueError):
            await harness.run_episode(scenario, self.settings(), live_client, self.out)
        self.assertEqual(live_client.requests, [])

    async def test_transient_retry_is_logged_without_duplicating_tool_effects(self):
        class RateLimited(Exception):
            status_code = 429

        client = ScriptedClient([
            RateLimited(),
            calls(("write-1", "write_file", {"path": "notes.txt", "content": "reviewed"})),
            answer(),
        ], [answer()])
        with patch("harness.asyncio.sleep") as sleep:
            episode = await self.run_case(client)
        self.assertEqual(episode["status"], "complete")
        self.assertEqual(len(episode["tool_log"]), 1)
        target_requests = [r for r in episode["requests"] if r["actor"] == "target"]
        self.assertEqual([r["attempt"] for r in target_requests], [1, 2, 1])
        self.assertEqual(target_requests[0]["error"]["status_code"], 429)
        self.assertEqual(target_requests[0]["request"], target_requests[1]["request"])
        sleep.assert_awaited_once()

    async def test_shared_semaphore_limits_concurrent_model_requests(self):
        class ConcurrentClient:
            is_fake = True

            def __init__(self):
                self.active = 0
                self.peak = 0
                self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

            async def create(self, **kwargs):
                self.active += 1
                self.peak = max(self.peak, self.active)
                await asyncio.sleep(0.01)
                self.active -= 1
                return answer()

        client = ConcurrentClient()
        semaphore = asyncio.Semaphore(2)
        results = await asyncio.gather(*(
            harness.run_episode(self.scenario(), self.settings(parallelism=2), client,
                                self.out, episode_id=f"episode-{index}", semaphore=semaphore)
            for index in range(4)
        ))
        self.assertEqual(client.peak, 2)
        self.assertTrue(all(result["status"] == "complete" for result in results))


if __name__ == "__main__":
    unittest.main()
