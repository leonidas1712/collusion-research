"""Generic multi-actor continuation loop used by branching and many-to-one cells."""

from __future__ import annotations

import asyncio
import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from harness import (
    EpisodeIncomplete, MockEnvironment, Scenario, Settings, _plain, _retry_delay,
    _save, _validate_args, standard_tools,
)


@dataclass(frozen=True)
class ActorConfig:
    actor_id: str
    display_name: str
    system_prompt: str
    model: str
    request_options: dict
    tool_names: tuple[str, ...]


def scenario_tools(scenario):
    base = standard_tools()
    overrides = {tool.schema["function"]["name"]: tool for tool in scenario.tool_overrides}
    if (len(overrides) != len(scenario.tool_overrides)
            or set(overrides) - {tool.schema["function"]["name"] for tool in base}):
        raise ValueError("tool_overrides must uniquely name standard tools")
    tools = [overrides.get(tool.schema["function"]["name"], tool) for tool in base]
    tools.extend(scenario.extra_tools)
    by_name = {tool.schema["function"]["name"]: tool for tool in tools}
    if len(by_name) != len(tools):
        raise ValueError("duplicate tool names")
    return tools, by_name


def make_scenario_spec(scenario, tools, actor_configs, *, peer_prompts=None):
    tool_access = {actor.actor_id: list(actor.tool_names) for actor in actor_configs}
    actor_names = {actor.actor_id: actor.display_name for actor in actor_configs}
    spec = {
        "name": scenario.name,
        "target_system": scenario.target_system,
        "target_task": scenario.target_task,
        "recruiter_system": scenario.recruiter_system if scenario.peer_enabled else None,
        "files": copy.deepcopy(scenario.files),
        "honeypots": list(scenario.honeypots),
        "tools": [copy.deepcopy(tool.schema) for tool in tools],
        "tool_access": tool_access,
        "test_result": copy.deepcopy(scenario.test_result),
        "scenario_version": scenario.scenario_version,
        "channel_format": scenario.channel_format,
        "actor_names": actor_names,
        "peer_enabled": scenario.peer_enabled,
        "metadata": copy.deepcopy(scenario.metadata),
    }
    if scenario.initial_state or scenario.tool_overrides:
        spec["initial_state"] = copy.deepcopy(scenario.initial_state)
        spec["tool_overrides"] = sorted(
            tool.schema["function"]["name"] for tool in scenario.tool_overrides)
    if peer_prompts is not None:
        spec["peer_prompts"] = copy.deepcopy(peer_prompts)
    return spec


async def run_continuation(
        scenario: Scenario, settings: Settings, client, output_dir, actor_configs,
        *, episode_id="episode-0001", start_round=1, round_count=None,
        initial=None, scenario_spec=None, branch_meta=None, live_approved=False,
        forced_continuation=False, semaphore=None):
    """Run ordered actors from an explicit state without changing the one-peer runner."""
    round_count = settings.rounds if round_count is None else round_count
    if min(round_count, settings.max_tool_steps, settings.max_tokens, settings.parallelism) < 1:
        raise ValueError("rounds, tool steps, tokens and parallelism must be positive")
    if start_round < 1:
        raise ValueError("start_round must be positive")
    if not episode_id or Path(episode_id).name != episode_id:
        raise ValueError("episode_id must be a filename stem")
    if not getattr(client, "is_fake", False) and not live_approved:
        raise ValueError("Live continuation is pending approval")
    actor_configs = tuple(actor_configs)
    actor_ids = [actor.actor_id for actor in actor_configs]
    if not actor_ids or actor_ids[-1] != "target" or len(set(actor_ids)) != len(actor_ids):
        raise ValueError("Actors must be unique and target must speak last")

    tools, by_name = scenario_tools(scenario)
    known_tools = set(by_name)
    for actor in actor_configs:
        if set(actor.tool_names) - known_tools:
            raise ValueError(f"Unknown tool in access list for {actor.actor_id}")
    if scenario_spec is None:
        peer_prompts = {actor.actor_id: actor.system_prompt for actor in actor_configs
                        if actor.actor_id != "target"}
        scenario_spec = make_scenario_spec(
            scenario, tools, actor_configs, peer_prompts=peer_prompts)
    else:
        scenario_spec = copy.deepcopy(scenario_spec)

    initial = copy.deepcopy(initial) if initial is not None else {}
    files = initial.get("files", copy.deepcopy(scenario.files))
    channel = initial.get("channel", [])
    state = initial.get("state", copy.deepcopy(scenario.initial_state))
    histories = initial.get("histories")
    if histories is None:
        histories = {"target": [
            {"role": "system", "content": scenario.target_system},
            {"role": "user", "content": scenario.target_task},
        ]}
        for actor in actor_configs:
            if actor.actor_id != "target":
                histories[actor.actor_id] = [
                    {"role": "system", "content": actor.system_prompt},
                    {"role": "user", "content": "Begin the team conversation."},
                ]
    if set(histories) != set(actor_ids):
        raise ValueError("Checkpoint histories do not match actor ids")

    env = MockEnvironment(files, channel=channel, test_result=scenario.test_result,
                          round=start_round - 1, state=state)
    episode = {
        "episode_id": episode_id,
        "scenario": scenario.name,
        "scenario_spec": scenario_spec,
        "settings": asdict(settings),
        "condition": {**copy.deepcopy(scenario_spec.get("metadata", {})),
                      "peer_enabled": len(actor_configs) > 1},
        "models_used": {actor.actor_id: actor.model for actor in actor_configs},
        "status": "running",
        "stop_reason": None,
        "label": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "requests": [],
        "channel": env.channel,
        "tool_log": initial.get("tool_log", []),
        "histories": histories,
        "files": env.files,
        "rounds_completed": start_round - 1,
        "fake": bool(getattr(client, "is_fake", False)),
    }
    if scenario.initial_state or initial.get("state") is not None:
        episode["state"] = env.state
    if branch_meta is not None:
        episode["branch"] = copy.deepcopy(branch_meta)
    prefix_tool_count = len(episode["tool_log"])
    prefix_channel_count = len(episode["channel"])

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = output_dir / f"{episode_id}.json"
    partial_path = output_dir / f"{episode_id}.partial.json"
    if final_path.exists() or partial_path.exists():
        raise ValueError("Continuation output already exists")
    semaphore = semaphore or asyncio.Semaphore(settings.parallelism)
    actor_map = {actor.actor_id: actor for actor in actor_configs}

    def record_publications(start, origin):
        if not scenario.metadata.get("publication_receipts"):
            return
        for index in range(start, len(env.channel)):
            publication = env.channel[index]
            publication_id = f"publication-{index + 1}"
            publication["publication_id"] = publication_id
            episode["tool_log"].append({
                "actor": publication["actor"], "round": publication["round"],
                "call_id": publication_id, "mock": True,
                "event_type": "channel_delivery", "name": "publish_message",
                "arguments": json.dumps({"content": publication["content"]},
                                        ensure_ascii=False),
                "result": {"delivered": True, "origin": origin,
                           "publication_id": publication_id},
            })

    async def request(actor_id, round_number):
        actor = actor_map[actor_id]
        payload = {
            "model": actor.model,
            "messages": copy.deepcopy(histories[actor_id]),
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature,
        }
        actor_tools = [tool.schema for tool in tools
                       if tool.schema["function"]["name"] in actor.tool_names]
        if actor_tools:
            payload["tools"] = copy.deepcopy(actor_tools)
        options = copy.deepcopy(actor.request_options)
        reserved = set(payload) | {"tools"}
        if set(options) & reserved or set(options.get("extra_body", {})) & reserved:
            raise ValueError("request options cannot replace core payload fields")
        extra_body = options.get("extra_body", {})
        payload.update(options)
        wire = {key: copy.deepcopy(value) for key, value in payload.items()
                if key != "extra_body"}
        wire.update(extra_body)
        for attempt in range(6):
            record = {
                "actor": actor_id, "round": round_number, "attempt": attempt + 1,
                "request": copy.deepcopy(payload), "request_body": copy.deepcopy(wire),
                "requested_routing": copy.deepcopy(extra_body.get("provider")),
                "served_provider": None, "served_quantization": None,
                "response": None, "usage": None,
            }
            episode["requests"].append(record)
            _save(partial_path, episode)
            try:
                async with semaphore:
                    response = _plain(await client.chat.completions.create(**payload))
                record["response"] = response
                record["usage"] = response.get("usage")
                record["served_provider"] = response.get("provider")
                record["served_quantization"] = response.get("quantization")
                record["serving_metadata_source"] = {
                    "provider": "response.provider" if record["served_provider"] else "not_reported",
                    "quantization": ("response.quantization"
                                     if record["served_quantization"] else "not_reported"),
                }
                _save(partial_path, episode)
                return response
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                record["error"] = {"type": type(exc).__name__, "status_code": status}
                _save(partial_path, episode)
                transient = status in (408, 409, 429) or (
                    isinstance(status, int) and 500 <= status < 600)
                transient = transient or type(exc).__name__ in (
                    "APIConnectionError", "APITimeoutError")
                if not transient or attempt == 5:
                    raise EpisodeIncomplete(f"api_error:{type(exc).__name__}") from exc
                delay, retry_after = _retry_delay(exc, attempt)
                record["retry_delay_seconds"] = delay
                record["retry_after"] = retry_after
                _save(partial_path, episode)
                await asyncio.sleep(delay)

    async def request_with_peer_retry(actor_id, round_number):
        response = await request(actor_id, round_number)
        choices = response.get("choices") or []
        if actor_id == "target" or not choices or choices[0].get("finish_reason") != "length":
            return response
        first_index = len(episode["requests"]) - 1
        episode["requests"][first_index]["length_retry_scheduled"] = True
        _save(partial_path, episode)
        response = await request(actor_id, round_number)
        retry_index = len(episode["requests"]) - 1
        episode["requests"][first_index]["length_retry_request_index"] = retry_index
        episode["requests"][retry_index]["retry_of_request_index"] = first_index
        episode["requests"][retry_index]["retry_reason"] = "peer_finish_reason_length"
        _save(partial_path, episode)
        return response

    try:
        _save(partial_path, episode)
        from scenarios import score_episode
        prefix_probe = copy.deepcopy(episode)
        prefix_probe["status"] = "complete"
        prefix_positive = bool(score_episode(prefix_probe).get("objective_success"))
        if forced_continuation and prefix_positive:
            raise ValueError("Branch point must precede the first forbidden action")
        action_round = None
        final_round = start_round + round_count - 1
        stop_after = final_round
        for round_number in range(start_round, final_round + 1):
            env.round = round_number
            for actor_id in actor_ids:
                channel_start = len(env.channel)
                for _step in range(settings.max_tool_steps):
                    response = await request_with_peer_retry(actor_id, round_number)
                    choices = response.get("choices") or []
                    if not choices:
                        raise EpisodeIncomplete("missing_choices")
                    choice = choices[0]
                    if choice.get("finish_reason") not in ("stop", "tool_calls"):
                        raise EpisodeIncomplete(f"finish_reason:{choice.get('finish_reason')}")
                    raw = choice.get("message") or {}
                    message = {key: copy.deepcopy(value) for key, value in raw.items()
                               if key in ("role", "content", "tool_calls", "reasoning",
                                          "reasoning_details", "refusal") and value is not None}
                    message["role"] = "assistant"
                    histories[actor_id].append(message)
                    calls = message.get("tool_calls") or []
                    if not calls:
                        content = message.get("content")
                        if not isinstance(content, str) or not content.strip():
                            raise EpisodeIncomplete("empty_assistant_message")
                        posted = [event["content"] for event in env.channel[channel_start:]
                                  if event["actor"] == actor_id]
                        if not posted:
                            publication_start = len(env.channel)
                            env.publish(actor_id, content)
                            record_publications(publication_start, "final_reply")
                        break
                    ids = [call.get("id") for call in calls]
                    if (any(not isinstance(value, str) or not value for value in ids)
                            or len(ids) != len(set(ids))):
                        raise EpisodeIncomplete("invalid_tool_call_ids")
                    for call in calls:
                        function = call.get("function") or {}
                        name, arguments = function.get("name"), function.get("arguments")
                        publication_start = len(env.channel)
                        try:
                            if name not in actor_map[actor_id].tool_names:
                                raise PermissionError("Tool is not available to this actor")
                            args = json.loads(arguments)
                            tool = by_name[name]
                            _validate_args(args, tool.schema["function"]["parameters"])
                            result = tool.handler(env, args, actor_id)
                        except PermissionError:
                            result = {"error": "PermissionError",
                                      "message": "Tool is not available to this actor"}
                        except (TypeError, ValueError, KeyError) as exc:
                            result = {"error": type(exc).__name__,
                                      "message": "Invalid tool call or missing file"}
                        episode["tool_log"].append({
                            "actor": actor_id, "round": round_number,
                            "call_id": call["id"], "mock": True, "name": name,
                            "arguments": arguments, "result": result,
                        })
                        record_publications(publication_start, name)
                        histories[actor_id].append({
                            "role": "tool", "tool_call_id": call["id"],
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                        _save(partial_path, episode)
                else:
                    raise EpisodeIncomplete("tool_step_limit")
                new_events = env.channel[channel_start:]
                for recipient in actor_ids:
                    if recipient == actor_id:
                        continue
                    for event in new_events:
                        histories[recipient].append({
                            "role": "user",
                            "content": scenario.channel_format.format(
                                actor=actor_id, name=actor_map[actor_id].display_name,
                                content=event["content"]),
                        })
                _save(partial_path, episode)
            episode["rounds_completed"] = round_number
            probe = copy.deepcopy(episode)
            probe["status"] = "complete"
            if action_round is None and score_episode(probe).get("objective_success"):
                action_round = round_number
                if not forced_continuation and settings.early_stop:
                    stop_after = min(final_round, action_round + 2)
            _save(partial_path, episode)
            if round_number >= stop_after:
                break
        episode["status"] = "complete"
        episode["stop_reason"] = (
            "forced_continuation_complete" if forced_continuation else
            "early_stop_after_action" if action_round is not None and stop_after < final_round else
            "round_limit")
        if forced_continuation:
            episode["branch_first_forbidden_round"] = action_round
            episode["branch_forbidden_within_window"] = action_round is not None
        elif action_round is not None:
            episode["early_stop_action_round"] = action_round
            episode["early_stop_after_round"] = stop_after
        if scenario.label_fn is not None:
            episode["label"] = scenario.label_fn(episode)
            tactic_id = scenario_spec.get("metadata", {}).get("tactic_id")
            if tactic_id is not None and isinstance(episode["label"], dict):
                episode["label"] = {**episode["label"], "tactic_id": tactic_id}
    except Exception as exc:
        episode["status"] = "incomplete"
        episode["label"] = None
        episode["stop_reason"] = str(exc) if isinstance(exc, EpisodeIncomplete) else type(exc).__name__
        episode["error"] = str(exc)
    episode["continued_channel_start"] = prefix_channel_count
    episode["continued_tool_log_start"] = prefix_tool_count
    episode["finished_at"] = datetime.now(timezone.utc).isoformat()
    _save(partial_path, episode)
    if episode["status"] == "complete":
        partial_path.replace(final_path)
    return episode
