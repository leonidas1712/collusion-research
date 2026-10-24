"""Drive runs/viewer.html from the terminal: open a view by link, keep saved reading lists, rebuild.

    uv run python experiments/E01-behaviour-pilot/viewer.py open --run 20261024-0312 --episode 3 --turn 4
    uv run python experiments/E01-behaviour-pilot/viewer.py open --outcome leak_deliberate --model qwen --sort round
    uv run python experiments/E01-behaviour-pilot/viewer.py open --list best --print     # just print the URL
    uv run python experiments/E01-behaviour-pilot/viewer.py list add best 20261024-0312 3 --turn 4 --note "gives in after 3 refusals"
    uv run python experiments/E01-behaviour-pilot/viewer.py list show best
    uv run python experiments/E01-behaviour-pilot/viewer.py list clear best
    uv run python experiments/E01-behaviour-pilot/viewer.py build

`open` builds a file://.../runs/viewer.html#... link (the page reads its state from the hash) and opens it with
macOS `open`. `open --list NAME` with no --run starts at the list's first item. Run IDs may be a unique prefix.
Lists live in runs/viewer_lists.json ({name: [{run, episode, turn?, note}]}) and are embedded when the page is
built, so `list add/clear` rebuild it (skip with --no-build). Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
RUNS = HERE.parents[1] / "runs"
VIEWER = RUNS / "viewer.html"
LISTS = RUNS / "viewer_lists.json"


def resolve_run(prefix: str) -> str:
    """Full run ID from an exact ID or a unique prefix; exits with the candidates otherwise."""
    ids = sorted(d.name for d in RUNS.iterdir() if (d / "episodes").is_dir())
    if prefix in ids:
        return prefix
    hits = [i for i in ids if i.startswith(prefix)]
    if len(hits) == 1:
        return hits[0]
    sys.exit(f"run prefix {prefix!r} matches {len(hits)} runs" + (":\n  " + "\n  ".join(hits[:20]) if hits else ""))


def check_episode(run: str, episode: str) -> str:
    """Accept 3, 0003 or a file name; warn (not fail) if no such file, since partial/attempt names vary."""
    ep = str(int(episode)) if episode.isdigit() else episode
    name = f"episode-{int(episode):04d}.json" if episode.isdigit() else episode
    if not (RUNS / run / "episodes" / name).exists():
        print(f"warning: no {RUNS / run / 'episodes' / name}", file=sys.stderr)
    return ep


def load_lists() -> dict:
    return json.loads(LISTS.read_text()) if LISTS.exists() else {}


def save_lists(lists: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=RUNS, prefix=".viewer_lists-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(lists, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, LISTS)


def build() -> int:
    return subprocess.call([sys.executable, str(HERE / "build_viewer.py")])


def cmd_open(a) -> int:
    if a.list and not a.run:
        items = load_lists().get(a.list) or []
        if items:
            a.run, a.episode, a.turn = items[0]["run"], items[0]["episode"], a.turn or items[0].get("turn")
        else:
            print(f"warning: list {a.list!r} is empty or missing in {LISTS}", file=sys.stderr)
    if a.episode and not a.run:
        sys.exit("--episode needs --run")
    if a.turn is not None and a.episode is None:
        sys.exit("--turn needs --episode")
    run = resolve_run(a.run) if a.run else None
    keys = [("run", run), ("episode", check_episode(run, str(a.episode)) if a.episode is not None else None),
            ("turn", a.turn), ("q", a.q), ("tag", ",".join(a.tag)), ("outcome", ",".join(a.outcome)),
            ("scenario", ",".join(a.scenario)), ("model", ",".join(a.model)), ("rmin", a.rmin), ("rmax", a.rmax),
            ("sort", a.sort), ("view", a.view), ("list", a.list)]
    frag = "&".join(f"{k}={quote(str(v), safe=',/')}" for k, v in keys if v not in (None, ""))
    url = VIEWER.as_uri() + ("#" + frag if frag else "")
    if a.print:
        print(url)
        return 0
    if not VIEWER.exists():
        sys.exit(f"no {VIEWER}; run `viewer.py build` first")
    # `open` with a file:// URL keeps the #fragment; a bare path would drop it.
    return subprocess.call(["open", url])


def cmd_list(a) -> int:
    lists = load_lists()
    if a.action == "show":
        items = lists.get(a.name)
        if items is None:
            sys.exit(f"no list {a.name!r} (have: {', '.join(lists) or 'none'})")
        for i, it in enumerate(items, 1):
            turn = f" round {it['turn']}" if it.get("turn") is not None else ""
            print(f"{i}. {it['run']} episode {it['episode']}{turn}" + (f"  {it['note']}" if it.get("note") else ""))
        return 0
    if a.action == "add":
        run = resolve_run(a.run)
        item = {"run": run, "episode": check_episode(run, a.episode)}
        if a.turn is not None:
            item["turn"] = a.turn
        item["note"] = a.note or ""
        lists.setdefault(a.name, []).append(item)
        print(f"{a.name}: item {len(lists[a.name])} = {run} episode {item['episode']}")
    else:  # clear
        if lists.pop(a.name, None) is None:
            print(f"no list {a.name!r}; nothing to clear")
            return 0
        print(f"cleared list {a.name!r}")
    save_lists(lists)
    return 0 if a.no_build else build()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    o = sub.add_parser("open", help="open (or --print) a viewer link")
    o.add_argument("--run", help="run ID or unique prefix")
    o.add_argument("--episode", help="episode number (3) or file name")
    o.add_argument("--turn", type=int, help="round to scroll to and highlight")
    o.add_argument("--q", help="search text")
    o.add_argument("--tag", action="append", default=[], help="tag filter (repeatable or comma-separated)")
    o.add_argument("--outcome", action="append", default=[],
                   help="outcome filter, e.g. leaked, refused, leak_deliberate, leak_incidental, noask, incomplete")
    o.add_argument("--scenario", action="append", default=[], help="scenario filter (exact or substring)")
    o.add_argument("--model", action="append", default=[], help="target model filter (exact or substring)")
    o.add_argument("--rmin", type=int, help="first-action round, minimum")
    o.add_argument("--rmax", type=int, help="first-action round, maximum")
    o.add_argument("--sort", help="runs: new, rate, med; episodes: run, round, rounds (round/rounds switch to episodes)")
    o.add_argument("--view", choices=["runs", "episodes"], help="home list to show")
    o.add_argument("--list", help="saved list to show in the sidebar (alone: open its first item)")
    o.add_argument("--print", action="store_true", help="print the URL instead of opening it")
    o.set_defaults(fn=cmd_open)

    ls = sub.add_parser("list", help="edit saved reading lists in runs/viewer_lists.json")
    lsub = ls.add_subparsers(dest="action", required=True)
    add = lsub.add_parser("add", help="append an item")
    add.add_argument("name")
    add.add_argument("run", help="run ID or unique prefix")
    add.add_argument("episode", help="episode number or file name")
    add.add_argument("--turn", type=int, help="round worth reading")
    add.add_argument("--note", help="why this one is worth reading")
    show = lsub.add_parser("show", help="print a list")
    show.add_argument("name")
    clear = lsub.add_parser("clear", help="delete a list")
    clear.add_argument("name")
    for p in (add, clear):
        p.add_argument("--no-build", action="store_true", help="skip rebuilding runs/viewer.html")
    ls.set_defaults(fn=cmd_list)

    sub.add_parser("build", help="rebuild runs/viewer.html").set_defaults(fn=lambda a: build())
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
