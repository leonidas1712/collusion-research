"""Load approved peer tactics from Markdown and apply them to E01 scenarios."""

from dataclasses import replace
from pathlib import Path
import re


SOURCE = Path(__file__).with_name("PEER_TACTICS.md")
REVIEW_OUTPUT = Path(__file__).with_name("PEER_TACTICS_FILLED.md")
TACTIC_IDS = tuple(f"T{index}" for index in range(8))


def _table(markdown, heading):
    try:
        section = markdown.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
    except IndexError as exc:
        raise ValueError(f"Missing {heading!r} table in {SOURCE.name}") from exc
    rows = [line for line in section.splitlines() if line.startswith("|")]
    if len(rows) < 3:
        raise ValueError(f"Malformed {heading!r} table in {SOURCE.name}")

    def cells(row):
        return [cell.strip().strip("`").strip("{}")
                for cell in row.strip().strip("|").split("|")]

    headers = cells(rows[0])
    return [dict(zip(headers, cells(row), strict=True)) for row in rows[2:]]


def load_catalog(path=SOURCE):
    """Return slot rows, fit decisions and exact blockquote bodies from the approved file."""
    markdown = Path(path).read_text()
    slots = {row["Scenario"].split(" (", 1)[0]: row for row in _table(markdown, "Slot values")}
    fit = {}
    for row in _table(markdown, "Fit"):
        tactic_id = row["Tactic"].split()[0]
        fit[tactic_id] = {family: re.match(r"\**skip\b", value.lower()) is None
                          for family, value in row.items() if family != "Tactic"}

    templates = {"T0": ""}
    pattern = re.compile(r"^### (T[1-7]):[^\n]*\n(?P<section>.*?)(?=^### |\Z)", re.M | re.S)
    for match in pattern.finditer(markdown):
        quote_lines = [line[2:] if line.startswith("> ") else line[1:]
                       for line in match.group("section").splitlines() if line.startswith(">")]
        templates[match.group(1)] = "\n".join(quote_lines)
    if tuple(sorted(templates)) != TACTIC_IDS:
        raise ValueError(f"Expected {', '.join(TACTIC_IDS)} in {SOURCE.name}")
    return slots, fit, templates


def filled_tactic(family, tactic_id, condition="recruiting", path=SOURCE):
    """Fill one approved tactic for a recruiting or matched-control peer."""
    tactic_id = tactic_id.upper()
    if tactic_id not in TACTIC_IDS:
        raise ValueError(f"Unknown tactic {tactic_id!r}; choose one of {', '.join(TACTIC_IDS)}")
    if condition not in {"recruiting", "control"}:
        raise ValueError("Peer tactics apply only to recruiting and control conditions")
    slots, fit, templates = load_catalog(path)
    if family not in slots or family not in fit[tactic_id]:
        raise ValueError(f"No tactic slots registered for {family!r}")
    if not fit[tactic_id][family]:
        raise ValueError(f"{tactic_id} is marked skip for {family} in {Path(path).name}")
    values = dict(slots[family])
    values["forbidden_ask"] = values["forbidden_ask" if condition == "recruiting" else "in_scope_ask"]
    return templates[tactic_id].format_map(values)


def apply_peer_tactic(scenario, tactic_id, path=SOURCE):
    """Append a tactic to an existing peer prompt (wording approved by Leo, 2026-10-24, PEER_TACTICS.md v3)."""
    family = scenario.metadata.get("scenario_family")
    condition = scenario.metadata.get("peer_condition")
    text = filled_tactic(family, tactic_id, condition, path)
    tactic_id = tactic_id.upper()
    metadata = dict(scenario.metadata)
    metadata.update(tactic_id=tactic_id, tactic_source=Path(path).name,
                    tactic_review_status="approved by Leo 2026-10-24 (softened v3)")
    if tactic_id != "T0":
        metadata["levers"] = sorted(set(metadata.get("levers", [])) | {"L10"})
    if metadata.get("variant_id"):
        metadata["variant_id"] += f"_{tactic_id.lower()}"
    prompt = scenario.recruiter_system + ("\n\n" + text if text else "")
    return replace(scenario, recruiter_system=prompt, metadata=metadata,
                   scenario_version=scenario.scenario_version + f"-peer-{tactic_id.lower()}-1",
                   recruiter_approved=scenario.recruiter_approved)


def render_deploy_token_review(path=SOURCE):
    """Render both deploy-token peer conditions for review without changing source wording."""
    lines = [
        "# Filled deploy-token peer tactics",
        "",
        f"Generated from `{Path(path).name}`. These cells remain `recruiter_approved=False`.",
        "",
    ]
    for tactic_id in TACTIC_IDS:
        lines.extend([f"## {tactic_id}", ""])
        for condition, title in (("recruiting", "Recruiting"), ("control", "Matched control")):
            text = filled_tactic("deploy-token", tactic_id, condition, path)
            lines.extend([f"### {title}", "", text or "(Nothing appended.)", ""])
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    REVIEW_OUTPUT.write_text(render_deploy_token_review())
    print(REVIEW_OUTPUT)
