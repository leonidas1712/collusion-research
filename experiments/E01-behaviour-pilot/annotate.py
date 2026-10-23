"""Attach a description, note or tags to a run or episode, then rebuild runs/viewer.html.

    uv run python experiments/E01-behaviour-pilot/annotate.py RUN_ID --desc "what this run is" --tag sweep
    uv run python experiments/E01-behaviour-pilot/annotate.py RUN_ID --episode episode-0004.json --note "..." --tag highlight
    uv run python experiments/E01-behaviour-pilot/annotate.py RUN_ID --remove-tag sweep

Edits runs/annotations.json ({"runs": {id: {description, tags}}, "episodes": {"id/file": {note, tags}}}) with an
atomic write (temp file + rename). --episode also accepts a bare number (4 -> episode-0004.json). Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parents[1] / "runs"
ANNOTATIONS = RUNS / "annotations.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_id")
    ap.add_argument("--episode", help="episode file name in runs/RUN_ID/episodes/, or its number")
    text = ap.add_mutually_exclusive_group()
    text.add_argument("--desc", help="run description (run-level only)")
    text.add_argument("--note", help="episode note (needs --episode)")
    ap.add_argument("--tag", action="append", default=[], help="add a tag (repeatable)")
    ap.add_argument("--remove-tag", action="append", default=[], help="remove a tag (repeatable)")
    ap.add_argument("--no-build", action="store_true", help="skip rebuilding runs/viewer.html")
    a = ap.parse_args()

    run_dir = RUNS / a.run_id
    if not (run_dir / "episodes").is_dir():
        ap.error(f"no run folder with episodes at {run_dir}")
    if a.desc is not None and a.episode:
        ap.error("--desc is for runs; use --note with --episode")
    if a.note is not None and not a.episode:
        ap.error("--note needs --episode")

    data = json.loads(ANNOTATIONS.read_text()) if ANNOTATIONS.exists() else {}
    data.setdefault("runs", {})
    data.setdefault("episodes", {})
    if a.episode:
        name = f"episode-{int(a.episode):04d}.json" if a.episode.isdigit() else a.episode
        if not (run_dir / "episodes" / name).exists():
            ap.error(f"no episode file {run_dir / 'episodes' / name}")
        entry, key = data["episodes"].setdefault(f"{a.run_id}/{name}", {}), "note"
        if a.note is not None:
            entry["note"] = a.note
    else:
        entry, key = data["runs"].setdefault(a.run_id, {}), "description"
        if a.desc is not None:
            entry["description"] = a.desc
    tags = [t for t in entry.get("tags", []) if t not in a.remove_tag]
    entry["tags"] = tags + [t for t in dict.fromkeys(a.tag) if t not in tags]
    if not entry["tags"]:
        del entry["tags"]

    fd, tmp = tempfile.mkstemp(dir=RUNS, prefix=".annotations-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, ANNOTATIONS)
    print(f"updated {ANNOTATIONS}: {entry.get(key, '')!r} tags={entry.get('tags', [])}")

    if not a.no_build:
        return subprocess.call([sys.executable, str(HERE / "build_viewer.py")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
