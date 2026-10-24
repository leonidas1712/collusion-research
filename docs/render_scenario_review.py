"""Render the exact text each new scenario shows the target and the peer, for Leo's review.

    uv run python docs/render_scenario_review.py

Writes docs/scenario_review.html: deploy-token v2 (with the change from v1 highlighted), then every
spray row (the database-password scenario is the first row). Text comes straight from the scenario
builders, so this is what the models will actually read.
"""

import difflib
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E01 = ROOT / "experiments" / "E01-behaviour-pilot"
sys.path.insert(0, str(E01))

from deploy_token_v2 import get_deploy_token_v2  # noqa: E402
from leak_scenarios import get_spray_scenario, load_spray_rows  # noqa: E402
from overnight_rules import get_overnight_scenario  # noqa: E402

OUT = ROOT / "docs" / "scenario_review.html"
FAMILY = "review"


def esc(text: str) -> str:
    return html.escape(text or "")


def diff_html(old: str, new: str) -> str:
    """Word-level diff: removed text struck through, added text highlighted."""
    a, b = old.split(" "), new.split(" ")
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if op == "equal":
            out.append(esc(" ".join(a[i1:i2])))
        if op in ("delete", "replace"):
            out.append(f'<del>{esc(" ".join(a[i1:i2]))}</del>')
        if op in ("insert", "replace"):
            out.append(f'<ins>{esc(" ".join(b[j1:j2]))}</ins>')
    return " ".join(out)


def block(title: str, body_html: str) -> str:
    return f'<h4>{esc(title)}</h4><div class="text">{body_html}</div>'


def scenario_html(sid: str, title: str, cells: dict, note: str = "", v1: dict | None = None) -> str:
    rec, ctl = cells["recruiting"], cells["control"]
    target = (diff_html(v1["recruiting"].target_system, rec.target_system) if v1 else esc(rec.target_system))
    files = "".join(f"<li><code>{esc(p)}</code><pre>{esc(c)}</pre></li>" for p, c in rec.files.items())
    actors = rec.actor_names or {}
    parts = [f'<section id="{sid}"><h2>{esc(title)}</h2>',
             f'<p class="small">Target: <b>{esc(actors.get("target", "target"))}</b> · peer: '
             f'<b>{esc(actors.get("recruiter", "peer"))}</b></p>' + (f'<p class="note">{note}</p>' if note else ""),
             block("Target system prompt (incl. the operator rule)", target),
             block("Target task", esc(rec.target_task)),
             f"<h4>Workspace files the target starts with</h4><ul class='files'>{files}</ul>",
             block("Peer prompt — recruiting (asks for the protected value)", esc(rec.recruiter_system)),
             block("Peer prompt — control (asks only for allowed details)", esc(ctl.recruiter_system)),
             "</section>"]
    return "\n".join(parts)


def main() -> None:
    sections, nav = [], []
    v1 = {c: get_overnight_scenario("deploy-token", "consequence_logged", c, FAMILY) for c in ("recruiting", "control")}
    v2 = {c: get_deploy_token_v2(c, FAMILY) for c in ("recruiting", "control")}
    sections.append(scenario_html(
        "deploy-token-v2", "deploy-token v2 (main scenario, cleaned)", v2,
        "Changes from v1 are highlighted: <del>removed</del>, <ins>added</ins>. The only other change: "
        "the run_tests result no longer contains <code>\"mock\": true</code>. Peers, task and files are identical.", v1))
    nav.append(("deploy-token-v2", "deploy-token v2"))
    rows = load_spray_rows()
    for rid, row in rows.items():
        cells = {c: get_spray_scenario(rid, c, FAMILY, rule_strength="consequence") for c in ("recruiting", "control")}
        kind = getattr(row, "kind", "") or getattr(row, "secret_kind", "") or ""
        sections.append(scenario_html(rid, f"{rid}" + (f" · {kind}" if kind else ""), cells))
        nav.append((rid, rid))
    links = "\n".join(f'<li><a href="#{i}">{esc(t)}</a></li>' for i, t in nav)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Scenario Text Review</title>
<style>
:root {{ --bg:#f7f7f5; --surface:#fff; --fg:#1d1d1b; --muted:#66655f; --line:#e2e0da; --accent:#2f6f6a;
  --del:#f6d6d2; --ins:#d4ecd9; --mono: ui-monospace, SFMono-Regular, Menlo, monospace; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141616; --surface:#1d2020;
  --fg:#e8e6e1; --muted:#a3a19a; --line:#2e3231; --accent:#7cc0b8; --del:#5a2a26; --ins:#1f4a2c; }} }}
:root[data-theme="dark"] {{ --bg:#141616; --surface:#1d2020; --fg:#e8e6e1; --muted:#a3a19a; --line:#2e3231;
  --accent:#7cc0b8; --del:#5a2a26; --ins:#1f4a2c; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font: 15px/1.55 system-ui, sans-serif; }}
.wrap {{ max-width: 900px; margin: 0 auto; padding: 24px 16px 64px; }}
h1 {{ font-size: 24px; margin: 0 0 6px; }} h2 {{ font-size: 20px; margin: 36px 0 4px; color: var(--accent); }}
h4 {{ margin: 18px 0 6px; font-size: 14px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }}
.text {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; white-space: pre-wrap; }}
pre {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 10px; overflow-x: auto;
  font: 13px var(--mono); white-space: pre-wrap; margin: 4px 0 0; }}
code {{ font-family: var(--mono); font-size: 13px; }}
del {{ background: var(--del); text-decoration: line-through; }} ins {{ background: var(--ins); text-decoration: none; }}
.small {{ color: var(--muted); font-size: 13px; margin: 0; }} .note {{ background: var(--surface); border-left: 3px solid var(--accent);
  padding: 8px 12px; border-radius: 4px; }}
ul.files {{ list-style: none; padding: 0; margin: 0; }} ul.files li {{ margin-bottom: 8px; }}
nav ul {{ columns: 2; padding-left: 18px; }} section {{ border-top: 1px solid var(--line); }}
</style></head><body><div class="wrap">
<h1>Scenario text review</h1>
<p class="small">Exactly what the target and peer models will read, rendered from the scenario code (family id "review";
real runs use different secret values). The target never sees the peer prompts; it only sees the peer's messages.</p>
<nav><ul>{links}</ul></nav>
{''.join(sections)}
</div></body></html>"""
    OUT.write_text(page)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(nav)} scenarios")


if __name__ == "__main__":
    main()
