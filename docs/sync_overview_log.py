"""Copy EXPERIMENT_LOG.md into the Log tab, and explainers/INDEX.md + GLOSSARY.md into the Explainers tab, of docs/overview.html.

    uv run python docs/sync_overview_log.py

Replaces everything between <!--LOG-START--> and <!--LOG-END--> with one table row per log entry,
newest first. Run it after adding log entries, before republishing the page.
"""

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "EXPERIMENT_LOG.md"
PAGE = ROOT / "docs" / "overview.html"
ENTRY = re.compile(r"^- (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) SGT \[([a-z-]+)\]\s*(.*)$")
EXPL = ROOT / "explainers"
PILL = {"result": "ok", "decision": "info", "pivot": "wait", "dead-end": "bad", "infra": "plain", "idea": "plain"}


def inline(text: str) -> str:
    out = html.escape(text)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)


def rows() -> list[str]:
    entries, current = [], None
    for line in LOG.read_text().splitlines():
        m = ENTRY.match(line)
        if m:
            current = list(m.groups())
            entries.append(current)
        elif current and line.strip():  # continuation line of the previous entry
            current[3] += " " + line.strip()
    out = []
    for date, time, tag, text in reversed(entries):
        out.append(f'<tr><td class="num">{date[5:]} {time}</td>'
                   f'<td><span class="pill {PILL.get(tag, "plain")}">{tag}</span></td><td>{inline(text)}</td></tr>')
    return out


def link(text: str) -> str:
    """Markdown [label](file) → a link into the repo's explainers folder."""
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="../explainers/\2"><code>\1</code></a>', text)


def explainers() -> str:
    items = [link(inline(l[2:])) for l in (EXPL / "INDEX.md").read_text().splitlines() if l.startswith("- ")]
    terms = []
    for l in (EXPL / "GLOSSARY.md").read_text().splitlines():
        m = re.match(r"^- \*\*(.+?)\*\*:?\s*(.*)$", l)
        if m:
            terms.append(f"<tr><td><strong>{inline(m.group(1)).rstrip(':')}</strong></td><td>{inline(m.group(2))}</td></tr>")
    return ("<h3>Explainers</h3>\n<ul>\n" + "\n".join(f"<li>{i}</li>" for i in items) + "\n</ul>\n"
            "<h3>Glossary</h3>\n<div class=\"scroll\"><table><tr><th>Term</th><th>Meaning</th></tr>\n"
            + "\n".join(terms) + "\n</table></div>")


def main() -> None:
    page = PAGE.read_text()
    page = re.sub(r"<!--EXPL-START-->.*?<!--EXPL-END-->", lambda _: f"<!--EXPL-START-->\n{explainers()}\n<!--EXPL-END-->", page, flags=re.S)
    table = ('<div class="scroll"><table><tr><th>When (SGT)</th><th>Type</th><th>Entry</th></tr>\n'
             + "\n".join(rows()) + "\n</table></div>")
    new = re.sub(r"<!--LOG-START-->.*?<!--LOG-END-->", f"<!--LOG-START-->\n{table}\n<!--LOG-END-->", page, flags=re.S)
    PAGE.write_text(new)
    print(f"synced {len(rows())} log entries into {PAGE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
