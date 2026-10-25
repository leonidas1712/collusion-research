"""Concrete database-password migration cells backed by the spray row schema."""

import json
from pathlib import Path

from leak_scenarios import (
    TABLE, build_leak_scenario, load_spray_rows, rendered_rule, score_leak_scenario,
)


ROW_ID = "database-password-migration"
DATABASE_PASSWORD_NAMES = tuple(
    f"database-password_explicit_{condition}_required-access"
    for condition in ("recruiting", "control", "alone"))
VERSION = "database-password-required-access-3"
REVIEW_OUTPUT = Path(__file__).with_name("DATABASE_PASSWORD_REVIEW.md")


def row():
    return load_spray_rows(TABLE)[ROW_ID]


RULE = row().rule_text
CONSEQUENCE = row().consequence_text


def get_database_password(name, family_id="1"):
    if name not in DATABASE_PASSWORD_NAMES:
        raise ValueError(f"Unknown database-password scenario {name!r}")
    condition = name.split("_")[2]
    return build_leak_scenario(
        row(), condition, family_id, name=name,
        scenario_family="database-password", version=VERSION,
        rule_strength="explicit")


def get_database_password_variant(condition, family_id="1", scenario_variant=None):
    if condition not in ("recruiting", "control", "alone"):
        raise ValueError(f"Unknown database-password condition {condition!r}")
    name = f"database-password_explicit_{condition}_required-access"
    return build_leak_scenario(
        row(), condition, family_id, name=name,
        scenario_family="database-password", version=VERSION,
        rule_strength="explicit", scenario_variant=scenario_variant)


score_database_password = score_leak_scenario


def render_review(family_id="review"):
    candidate = row()
    lines = [
        "# Database-password migration scenario review",
        "",
        "Offline proposal for human review. All three cells remain `recruiter_approved=False`; no live run is authorized.",
        f"Scenario version: `{VERSION}`. Text version: `{candidate.text_version}`.",
        "",
        "## Rule",
        "",
        rendered_rule(candidate, "consequence"),
        "",
        "## Tactic slots",
        "",
        "```json",
        json.dumps(candidate.tactic_slots, indent=2, sort_keys=True),
        "```",
        "",
    ]
    for condition in ("recruiting", "control", "alone"):
        scenario = build_leak_scenario(
            candidate, condition, family_id, scenario_family="database-password",
            version=VERSION, rule_strength="consequence")
        lines.extend([
            f"## {condition.capitalize()} cell",
            "",
            "### Target system prompt",
            "",
            "```text",
            scenario.target_system,
            "```",
            "",
            "### Target task",
            "",
            "```text",
            scenario.target_task,
            "```",
            "",
            "### Peer prompt",
            "",
            "```text",
            scenario.recruiter_system or "(No peer in the alone cell.)",
            "```",
            "",
            "### Initial files",
            "",
            "```json",
            json.dumps(scenario.files, indent=2, sort_keys=True),
            "```",
            "",
            "### Causal metadata",
            "",
            f"- goal_link: {scenario.metadata['goal_link']}",
            f"- target_reason_to_hold: {scenario.metadata['target_reason_to_hold']}",
            f"- target_pull_to_give_in: {scenario.metadata['target_pull_to_give_in']}",
            f"- peer_reason_to_persist: {scenario.metadata['peer_reason_to_persist']}",
            f"- variant_change: {scenario.metadata['scenario_variant_change']}",
            "",
        ])
    for condition in ("recruiting", "control"):
        variant = build_leak_scenario(
            candidate, condition, family_id, scenario_family="database-password",
            version=VERSION, rule_strength="consequence", scenario_variant="own-stake")
        lines.extend([
            f"## {condition.capitalize()} opt-in own-stake variant",
            "",
            "### Target system prompt",
            "",
            "```text", variant.target_system, "```", "",
            "### Causal metadata changes",
            "",
            f"- goal_link: {variant.metadata['goal_link']}",
            f"- target_reason_to_hold: {variant.metadata['target_reason_to_hold']}",
            f"- target_pull_to_give_in: {variant.metadata['target_pull_to_give_in']}",
            f"- peer_reason_to_persist: {variant.metadata['peer_reason_to_persist']}",
            f"- variant_change: {variant.metadata['scenario_variant_change']}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    REVIEW_OUTPUT.write_text(render_review())
    print(REVIEW_OUTPUT)
