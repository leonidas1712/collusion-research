"""Render E01 episodes as readable markdown.

    uv run python experiments/E01-behaviour-pilot/view.py runs/<run-id>            # writes runs/<run-id>/views/
    uv run python experiments/E01-behaviour-pilot/view.py runs/<run-id>/episodes/episode-0001.json   # prints one

Per episode: the label, then the target's conversation exactly as the target saw it (system prompt,
task, channel messages, its own tool calls and their results), then the peer's private side.
For a run folder, also writes views/index.md: one row per episode with condition, status and label.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _fmt_args(raw) -> str:
    try:
        args = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return str(raw)
    return ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in args.items()) if isinstance(args, dict) else str(args)


def _quote(text: str) -> str:
    return "\n".join("> " + line for line in (text or "").splitlines()) or "> (empty)"


def render_history(history: list[dict]) -> str:
    out = []
    for m in history:
        role, content = m.get("role"), m.get("content")
        if isinstance(content, list):  # content parts
            content = "\n".join(p.get("text", "") for p in content if isinstance(p, dict))
        if role == "system":
            out.append(f"**system prompt**\n\n{_quote(content)}")
        elif role == "user":
            out.append(f"**in** \n\n{_quote(content)}")
        elif role == "assistant":
            if content:
                out.append(f"**says**\n\n{_quote(content)}")
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function", {})
                out.append(f"**calls** `{fn.get('name')}({_fmt_args(fn.get('arguments'))})`")
        elif role == "tool":
            out.append(f"**tool result** `{str(content)[:400]}`")
    return "\n\n".join(out)


def condition(ep: dict) -> str:
    if ep.get("condition"):
        return ", ".join(f"{k}={v}" for k, v in ep["condition"].items())
    return ep.get("scenario") or ep.get("scenario_spec", {}).get("name", "?")


def cost(ep: dict) -> str:
    """Sum of reported costs; says so when some calls reported none (unknown is not free)."""
    reqs = ep.get("requests", [])
    known = [(r.get("usage") or {}).get("cost") for r in reqs]
    total = sum(c for c in known if c is not None)
    missing = sum(c is None for c in known)
    return f"${total:.4f} over {len(reqs)} calls" + (f" ({missing} with unknown cost)" if missing else "")


def serving(ep: dict) -> str:
    """Which provider (and quantization, when reported) served each actor's calls."""
    from collections import Counter
    counts = Counter()
    for r in ep.get("requests", []):
        prov = r.get("served_provider") or (r.get("response") or {}).get("provider") or "unknown"
        quant = r.get("served_quantization") or "quantization not reported"
        counts[(r.get("actor"), prov, quant)] += 1
    return "; ".join(f"{a}: {p} ({q}) ×{n}" for (a, p, q), n in sorted(counts.items(), key=str)) or "unknown"


def render_episode(ep: dict) -> str:
    s = ep.get("settings", {})
    lines = [
        f"# {ep['episode_id']} · {condition(ep)}",
        "",
        f"- status: **{ep.get('status')}** ({ep.get('stop_reason')}), rounds completed: {ep.get('rounds_completed')}",
        f"- label: **{json.dumps(ep.get('label'))}**",
        f"- target: `{s.get('target_model')}` · peer: `{s.get('recruiter_model')}` · temperature {s.get('temperature')}",
        f"- cost: {cost(ep)}",
        f"- served by: {serving(ep)}",
        "",
        "## Channel",
        "",
    ]
    for c in ep.get("channel", []):
        lines.append(f"- r{c['round']} **{c['actor']}**: {c['content']}")
    hist = ep.get("histories", {})
    lines += ["", "## Target's view", "", render_history(hist.get("target", []))]
    if hist.get("recruiter"):
        lines += ["", "## Peer's view", "", render_history(hist["recruiter"])]
    if ep.get("files"):
        lines += ["", "## Final files", ""]
        for path, content in ep["files"].items():
            lines.append(f"- `{path}`: `{str(content)[:200]}`")
    return "\n".join(lines) + "\n"


def render_run(run_dir: Path) -> None:
    files = sorted((run_dir / "episodes").glob("episode-*.json"))
    # Final episode files are episode-NNNN.json; .partial.json (in progress) and .attempt-N.json
    # (restarted after a failure) are listed separately so failures stay visible but aren't counted.
    eps = [p for p in files if p.name.count(".") == 1]
    other = [p for p in files if p not in eps]
    views = run_dir / "views"
    views.mkdir(exist_ok=True)
    rows = ["| episode | condition | status | label |", "|---|---|---|---|"]
    for p in eps:
        ep = json.loads(p.read_text())
        (views / f"{p.stem}.md").write_text(render_episode(ep))
        rows.append(f"| [{ep['episode_id']}]({p.stem}.md) | {condition(ep)} | {ep.get('status')} | {json.dumps(ep.get('label'))} |")
    text = f"# {run_dir.name}\n\n" + "\n".join(rows) + "\n"
    if other:
        text += "\n## Partial and earlier attempts (not counted)\n\n" + "\n".join(f"- `{p.name}`" for p in other) + "\n"
    (views / "index.md").write_text(text)
    print(f"wrote {len(eps)} episode views to {views} ({len(other)} partial/attempt files listed, not counted)")


if __name__ == "__main__":
    target = Path(sys.argv[1])
    if target.is_dir():
        render_run(target)
    else:
        print(render_episode(json.loads(target.read_text())))
