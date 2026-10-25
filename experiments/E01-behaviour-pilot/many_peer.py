"""Pending-review two- and three-peer variants for the E01 shared channel."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from continuation import ActorConfig, run_continuation, scenario_tools


MANY_PEER_APPROVED = True  # approved after human review 2026-10-24
SUPPORTED_PEER_COUNTS = (2, 3)
REVIEW_OUTPUT = Path(__file__).with_name("MANY_TO_ONE_REVIEW.md")


def prepare_many_peer_scenario(scenario, peer_count):
    if peer_count not in SUPPORTED_PEER_COUNTS:
        raise ValueError("Many-to-one cells require two or three peers")
    if not scenario.peer_enabled:
        raise ValueError("Many-to-one does not apply to an alone cell")
    base_name = scenario.actor_names["recruiter"]
    peer_names = [base_name] + [f"{base_name}-{index}" for index in range(2, peer_count + 1)]
    prompts = []
    for name in peer_names:
        prompts.append(scenario.recruiter_system.replace(base_name, name))
    metadata = dict(scenario.metadata)
    metadata.update(
        peer_count=peer_count,
        peer_actor_ids=["recruiter"] + [f"recruiter-{index}"
                                          for index in range(2, peer_count + 1)],
        peer_display_names=peer_names,
        peer_prompts=prompts,
        many_to_one_review_status=("approved" if MANY_PEER_APPROVED
                                   else "pending Leo review; offline only"),
        many_to_one_approval_reference=None,
    )
    target_system = (scenario.target_system + " Additional teammates in this channel: "
                     + ", ".join(peer_names[1:]) + ".")
    return replace(
        scenario,
        target_system=target_system,
        recruiter_approved=MANY_PEER_APPROVED,
        scenario_version=scenario.scenario_version + f"-many-to-one-{peer_count}-1",
        metadata=metadata,
    )


def actor_configs(scenario, settings):
    peer_ids = scenario.metadata.get("peer_actor_ids")
    prompts = scenario.metadata.get("peer_prompts")
    names = scenario.metadata.get("peer_display_names")
    if not peer_ids or not prompts or not names or not (len(peer_ids) == len(prompts) == len(names)):
        raise ValueError("Scenario is missing many-to-one peer configuration")
    recruiter_tools = tuple(scenario.tool_access["recruiter"])
    actors = [
        ActorConfig(actor_id, display_name, prompt, settings.recruiter_model,
                    settings.recruiter_request_options, recruiter_tools)
        for actor_id, display_name, prompt in zip(peer_ids, names, prompts)
    ]
    actors.append(ActorConfig(
        "target", scenario.actor_names["target"], scenario.target_system,
        settings.target_model, settings.target_request_options,
        tuple(scenario.tool_access["target"]),
    ))
    return tuple(actors)


async def run_many_peer_episode(scenario, settings, client, output_dir,
                                episode_id="episode-0001", semaphore=None):
    peer_count = scenario.metadata.get("peer_count")
    if peer_count not in SUPPORTED_PEER_COUNTS:
        raise ValueError("Call prepare_many_peer_scenario before running")
    tools = scenario_tools(scenario)[0]
    configs = actor_configs(scenario, settings)
    peer_prompts = {actor.actor_id: actor.system_prompt for actor in configs
                    if actor.actor_id != "target"}
    from continuation import make_scenario_spec
    spec = make_scenario_spec(scenario, tools, configs, peer_prompts=peer_prompts)
    spec["metadata"]["recruiter_approved"] = scenario.recruiter_approved
    return await run_continuation(
        scenario, settings, client, output_dir, configs, episode_id=episode_id,
        scenario_spec=spec, live_approved=scenario.recruiter_approved,
        semaphore=semaphore,
    )


def render_review():
    from overnight_rules import get_overnight_scenario
    base = get_overnight_scenario(
        "deploy-token", "consequence_logged", "recruiting", "many-peer-review")
    lines = [
        "# Many-to-one review",
        "",
        "Approved by Leo on 2026-10-24. `MANY_PEER_APPROVED=True`.",
        "",
        "The existing one-peer scenario and `run_episode` path are unchanged. With `--peers 2` or",
        "`--peers 3`, peers speak in numbered order before the target each round. Every message is",
        "broadcast to every other actor. All peers use the existing pinned recruiter model and",
        "request options. The target, files, tools, and deterministic scorer are otherwise unchanged.",
        "The alone cell continues to use the existing no-peer runner.",
        "",
    ]
    for count in SUPPORTED_PEER_COUNTS:
        scenario = prepare_many_peer_scenario(base, count)
        lines.extend([f"## {count} peers", "", "### Target system prompt", "", "```text",
                      scenario.target_system, "```", ""])
        for index, (name, prompt) in enumerate(zip(
                scenario.metadata["peer_display_names"],
                scenario.metadata["peer_prompts"]), 1):
            lines.extend([f"### Peer {index}: {name}", "", "```text", prompt, "```", ""])
    lines.extend([
        "## Approval status",
        "",
        "The two- and three-peer cells are enabled. To retire approval, set",
        "`MANY_PEER_APPROVED=False`; non-fake continuation runs will then stop before requests.",
        "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    REVIEW_OUTPUT.write_text(render_review())
    print(REVIEW_OUTPUT)
