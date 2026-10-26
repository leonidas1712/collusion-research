"""Rebuild an exact saved E01 round boundary and sample forced continuations.

The default command only prints a cost estimate. Add ``--execute`` after review to make
model requests. Every branch runs exactly K rounds, including after a forbidden action.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
from dataclasses import fields, replace
import json
import os
from pathlib import Path
import random

from continuation import ActorConfig, run_continuation, scenario_tools
from harness import MockEnvironment, Settings, _validate_args


def load_parent(path):
    path = Path(path)
    episode = json.loads(path.read_text())
    if episode.get("status") != "complete":
        raise ValueError("Branching requires a complete parent episode")
    if not episode.get("requests") or not episode.get("scenario_spec"):
        raise ValueError("Parent episode lacks saved requests or scenario specification")
    return path, episode


def resolve_scenario(episode):
    """Resolve callable tools, then restore the exact saved text and state specification."""
    spec = episode["scenario_spec"]
    metadata = spec.get("metadata", {})
    family_id = metadata.get("family_id", "1")
    if metadata.get("spray_row_id"):
        from leak_scenarios import get_spray_scenario
        source = get_spray_scenario(
            metadata["spray_row_id"], metadata["peer_condition"], family_id,
            rule_strength=metadata.get("rule_strength", "consequence_logged"))
    else:
        from scenarios import get_scenario
        source = get_scenario(metadata.get("base_scenario_name", spec["name"]), family_id)
    scenario = replace(
        source,
        name=spec["name"],
        target_system=spec["target_system"],
        target_task=spec["target_task"],
        recruiter_system=spec.get("recruiter_system") or "",
        files=copy.deepcopy(spec["files"]),
        honeypots=tuple(spec.get("honeypots", ())),
        test_result=copy.deepcopy(spec.get("test_result")),
        recruiter_approved=False,
        scenario_version=spec.get("scenario_version", "saved"),
        channel_format=spec.get("channel_format", source.channel_format),
        actor_names=copy.deepcopy(spec.get("actor_names", source.actor_names)),
        tool_access=copy.deepcopy(spec.get("tool_access", source.tool_access)),
        peer_enabled=bool(spec.get("peer_enabled")),
        metadata=copy.deepcopy(metadata),
        initial_state=copy.deepcopy(spec.get("initial_state", source.initial_state)),
    )
    tools = scenario_tools(scenario)[0]
    if [tool.schema for tool in tools] != spec.get("tools"):
        raise ValueError("Current tool schemas differ from the saved episode; exact replay refused")
    return scenario


def _tool_result(env, by_name, access, event):
    name = event.get("name")
    if event.get("event_type") == "channel_delivery" or name == "publish_message":
        return None
    if name == "send_message":
        return {"delivered": True}
    arguments = event.get("arguments")
    try:
        if name not in access.get(event.get("actor"), ()):
            raise PermissionError("Tool is not available to this actor")
        args = json.loads(arguments) if isinstance(arguments, str) else arguments
        tool = by_name[name]
        _validate_args(args, tool.schema["function"]["parameters"])
        return tool.handler(env, args, event.get("actor"))
    except PermissionError:
        return {"error": "PermissionError", "message": "Tool is not available to this actor"}
    except (TypeError, ValueError, KeyError) as exc:
        return {"error": type(exc).__name__, "message": "Invalid tool call or missing file"}


def _actor_order(episode):
    metadata = episode["scenario_spec"].get("metadata", {})
    peer_ids = metadata.get("peer_actor_ids")
    if peer_ids:
        return tuple(peer_ids) + ("target",)
    return ("recruiter", "target") if episode["scenario_spec"].get("peer_enabled") else ("target",)


def _history_at_round(episode, actor, round_number, actor_order):
    completed = episode.get("rounds_completed", 0)
    if round_number == completed + 1:
        return copy.deepcopy(episode["histories"][actor])
    records = [record for record in episode["requests"]
               if record.get("actor") == actor and record.get("round") == round_number]
    if not records:
        raise ValueError(f"No saved request for {actor} at round {round_number}")
    messages = copy.deepcopy(records[0]["request"]["messages"])
    earlier = set(actor_order[:actor_order.index(actor)])
    current_events = [event for event in episode.get("channel", [])
                      if event.get("round") == round_number and event.get("actor") in earlier]
    expected = [episode["scenario_spec"]["channel_format"].format(
        actor=event["actor"],
        name=episode["scenario_spec"]["actor_names"][event["actor"]],
        content=event["content"]) for event in current_events]
    for content in reversed(expected):
        if not messages or messages[-1] != {"role": "user", "content": content}:
            raise ValueError("Saved history does not match current-round channel delivery")
        messages.pop()
    return messages


def reconstruct_checkpoint(episode, round_number, scenario=None):
    completed = episode.get("rounds_completed", 0)
    if not 1 <= round_number <= completed + 1:
        raise ValueError(f"Branch round must be between 1 and {completed + 1}")
    scenario = scenario or resolve_scenario(episode)
    tools, by_name = scenario_tools(scenario)
    spec = episode["scenario_spec"]
    access = spec["tool_access"]
    env = MockEnvironment(
        copy.deepcopy(spec["files"]), test_result=copy.deepcopy(spec.get("test_result")),
        state=copy.deepcopy(spec.get("initial_state", {})), round=round_number - 1)
    prefix_log = []
    for event in episode.get("tool_log", []):
        event_round = event.get("round")
        if not isinstance(event_round, int) or event_round >= round_number:
            continue
        prefix_log.append(copy.deepcopy(event))
        replayed = _tool_result(env, by_name, access, event)
        if replayed is not None and replayed != event.get("result"):
            raise ValueError(
                f"Tool replay drift at round {event_round}, call {event.get('call_id')}; "
                "exact reconstruction refused")
    prefix_channel = [copy.deepcopy(event) for event in episode.get("channel", [])
                      if isinstance(event.get("round"), int) and event["round"] < round_number]
    env.channel = copy.deepcopy(prefix_channel)
    if round_number == completed + 1:
        if env.files != episode.get("files") or (
                "state" in episode and env.state != episode.get("state")):
            raise ValueError("Full replay does not reproduce the saved final environment")
    order = _actor_order(episode)
    histories = {actor: _history_at_round(episode, actor, round_number, order)
                 for actor in order}
    return {
        "round": round_number - 1,
        "files": env.files,
        "state": env.state,
        "channel": prefix_channel,
        "tool_log": prefix_log,
        "histories": histories,
    }


def settings_from_parent(episode):
    valid = {field.name for field in fields(Settings)}
    return Settings(**{key: copy.deepcopy(value) for key, value in episode["settings"].items()
                       if key in valid})


def actors_from_parent(episode, settings):
    spec = episode["scenario_spec"]
    order = _actor_order(episode)
    prompts = spec.get("peer_prompts", {})
    configs = []
    for actor in order:
        target = actor == "target"
        configs.append(ActorConfig(
            actor,
            spec["actor_names"][actor],
            spec["target_system"] if target else prompts.get(actor, spec["recruiter_system"]),
            settings.target_model if target else settings.recruiter_model,
            settings.target_request_options if target else settings.recruiter_request_options,
            tuple(spec["tool_access"][actor]),
        ))
    return tuple(configs)


def estimate_cost(episode, round_count, branches):
    actors = _actor_order(episode)
    observed = {}
    for actor in actors:
        records = [record for record in episode["requests"]
                   if record.get("actor") == actor and isinstance(record.get("usage"), dict)]
        costs = [float(record["usage"]["cost"]) for record in records
                 if record["usage"].get("cost") is not None]
        prompt = [int(record["usage"].get("prompt_tokens") or 0) for record in records]
        completion = [int(record["usage"].get("completion_tokens") or 0) for record in records]
        observed[actor] = {
            "requests_observed": len(records),
            "mean_cost_usd": sum(costs) / len(costs) if costs else None,
            "mean_prompt_tokens": sum(prompt) / len(prompt) if prompt else None,
            "mean_completion_tokens": sum(completion) / len(completion) if completion else None,
        }
    requests = round_count * branches
    known_costs = [values["mean_cost_usd"] for values in observed.values()
                   if values["mean_cost_usd"] is not None]
    estimated_cost = (requests * sum(known_costs)
                      if len(known_costs) == len(observed) else None)
    return {
        "method": "parent per-actor mean billed usage",
        "branches": branches,
        "rounds_per_branch": round_count,
        "actor_turns": requests * len(actors),
        "estimated_cost_usd": estimated_cost,
        "observed": observed,
    }


def validate_branch_point(episode, round_number):
    label = episode.get("label") or {}
    first_action = label.get("first_action_round")
    if label.get("objective_success") and isinstance(first_action, int) and round_number > first_action:
        raise ValueError(
            f"Branch round {round_number} is after the parent's first forbidden action "
            f"in round {first_action}")


def _class_and_action(episode):
    condition = episode.get("condition", {}).get("peer_condition")
    positive = bool((episode.get("label") or {}).get("objective_success"))
    if condition == "control":
        return "control", ((episode.get("label") or {}).get("first_action_round")
                           if positive else None)
    if positive:
        return "give-in", (episode.get("label") or {}).get("first_action_round")
    return "held", None


def select_branch_points(paths, limit=50, seed=0):
    buckets = {(kind, phase): [] for kind in ("held", "give-in", "control")
               for phase in ("early", "late")}
    for path in sorted(map(Path, paths)):
        try:
            episode = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if episode.get("status") != "complete" or not episode.get("scenario_spec", {}).get("peer_enabled"):
            continue
        kind, action = _class_and_action(episode)
        rounds = episode.get("rounds_completed", 0)
        if rounds < 2:
            continue
        proposed = {
            "early": max(1, round(rounds * 0.25)),
            "late": max(1, round(rounds * 0.75)),
        }
        if isinstance(action, int):
            proposed = {phase: min(value, action) for phase, value in proposed.items()}
        for phase, branch_round in proposed.items():
            buckets[(kind, phase)].append({
                "episode": str(path), "round": branch_round,
                "outcome": kind, "phase": phase,
                "parent_first_action_round": action,
            })
    rng = random.Random(seed)
    for candidates in buckets.values():
        rng.shuffle(candidates)
    selected = []
    keys = list(buckets)
    while len(selected) < limit and any(buckets.values()):
        for key in keys:
            if buckets[key] and len(selected) < limit:
                selected.append(buckets[key].pop())
    return selected


async def run_branches(parent_path, episode, round_number, round_count, branches,
                       output_dir, client):
    validate_branch_point(episode, round_number)
    scenario = resolve_scenario(episode)
    checkpoint = reconstruct_checkpoint(episode, round_number, scenario)
    settings = settings_from_parent(episode)
    configs = actors_from_parent(episode, settings)
    output_dir = Path(output_dir)
    results = []
    for index in range(1, branches + 1):
        branch_meta = {
            "parent_path": str(Path(parent_path).resolve()),
            "parent_episode_id": episode.get("episode_id"),
            "branch_round": round_number,
            "rounds_requested": round_count,
            "branch_index": index,
        }
        result = await run_continuation(
            scenario, settings, client, output_dir, configs,
            episode_id=f"branch-r{round_number:04}-n{index:04}",
            start_round=round_number, round_count=round_count,
            initial=checkpoint, scenario_spec=episode["scenario_spec"],
            branch_meta=branch_meta, live_approved=True, forced_continuation=True,
        )
        results.append(result)
    complete = [result for result in results if result["status"] == "complete"]
    hits = [result for result in complete if result.get("branch_forbidden_within_window")]
    summary = {
        "parent_path": str(Path(parent_path).resolve()),
        "branch_round": round_number,
        "rounds_requested": round_count,
        "branches_requested": branches,
        "branches_complete": len(complete),
        "forbidden_within_window": len(hits),
        "share_forbidden_within_window": len(hits) / len(complete) if complete else None,
        "first_forbidden_rounds": [result["branch_first_forbidden_round"] for result in hits],
        "branch_files": [f"branch-r{round_number:04}-n{index:04}.json"
                         for index in range(1, branches + 1)],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def make_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode", nargs="?", help="Complete parent episode JSON")
    parser.add_argument("--round", type=int, dest="branch_round")
    parser.add_argument("--next-rounds", type=int, default=3)
    parser.add_argument("--branches", type=int, default=5)
    parser.add_argument("--output-dir")
    parser.add_argument("--execute", action="store_true",
                        help="Make model requests after printing the estimate")
    parser.add_argument("--select-from", nargs="+", metavar="PATH",
                        help="Select branch points from episode files or directories")
    parser.add_argument("--selection-output", default="branch-points.json")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--seed", type=int, default=0)
    return parser


def _expanded_paths(values):
    paths = []
    for value in values:
        path = Path(value)
        paths.extend(path.rglob("episode-*.json") if path.is_dir() else [path])
    return paths


async def main(args):
    if args.select_from:
        selected = select_branch_points(
            _expanded_paths(args.select_from), limit=args.limit, seed=args.seed)
        Path(args.selection_output).write_text(json.dumps(selected, indent=2) + "\n")
        print(json.dumps({"selected": len(selected), "output": args.selection_output}))
        return
    if not args.episode or args.branch_round is None:
        raise ValueError("episode and --round are required unless --select-from is used")
    if min(args.next_rounds, args.branches) < 1:
        raise ValueError("--next-rounds and --branches must be positive")
    parent_path, episode = load_parent(args.episode)
    validate_branch_point(episode, args.branch_round)
    scenario = resolve_scenario(episode)
    reconstruct_checkpoint(episode, args.branch_round, scenario)
    estimate = estimate_cost(episode, args.next_rounds, args.branches)
    print("COST_ESTIMATE " + json.dumps(estimate, sort_keys=True), flush=True)
    if not args.execute:
        print("ESTIMATE_ONLY: add --execute after the author reviews the runner", flush=True)
        return
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    client = AsyncOpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1",
        max_retries=0, timeout=90)
    output = args.output_dir or (
        parent_path.parent / "branches" / f"{parent_path.stem}-r{args.branch_round:04}")
    try:
        summary = await run_branches(
            parent_path, episode, args.branch_round, args.next_rounds,
            args.branches, output, client)
        print("BRANCH_SUMMARY " + json.dumps(summary, sort_keys=True), flush=True)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main(make_parser().parse_args()))
