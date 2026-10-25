"""Write per-episode monitor sidecars for runs/viewer.html from the E06 monitor caches.

    uv run python experiments/E01-behaviour-pilot/build_viewer_monitors.py     # writes runs/viewer_monitors/

Reads every runs/*e06-monitor-main*/cache/<key>.json (one file per monitor call: request_body, response,
score, cost, ...). Each record's step_id is "<run>/<episode file>::request_idx=N", N indexing that episode's
`requests`, so a call maps to one target API request. Records are grouped by episode and written as
runs/viewer_monitors/<run>__<episode>.js, a script that sets window.MONDATA[<episode key>]; the viewer adds
that <script> tag when the episode is opened (works under file://, where fetch of local JSON is blocked).
runs/viewer_monitors/index.json lists the episodes with monitor data and is embedded in the viewer.

Size: long strings (the monitor prompt / decision state) are split on newlines and the lines interned in a
per-episode table (each string becomes {"$c": [line ids, run-length coded]}), since operator instructions and earlier history repeat across steps and setups; the page
joins them back, so the input shown is byte-for-byte the request that was sent. One field is dropped from
responses: the encrypted reasoning blob of gpt-5-nano (reasoning_details[].data with type reasoning.encrypted),
which is opaque ciphertext; it is replaced by a marker string giving its length.
Read-only on run folders; standard library only. Rebuilt automatically by build_viewer.py when a cache changes.
"""

from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
OUT = RUNS / "viewer_monitors"
INDEX = OUT / "index.json"
MIN_CHUNKED = 200  # strings at least this long are stored as interned lines
FAMILY = {"jev": "Jev", "luna": "Luna", "llm": "LLM judge"}
STEP_RE = re.compile(r"^(?P<run>[^/]+)/(?P<file>[^/]+\.json)::request_idx=(?P<idx>\d+)$")


def monitor_runs() -> list[Path]:
    return sorted(d for d in RUNS.glob("*e06-monitor-main*") if (d / "cache").is_dir())


def stale() -> bool:
    """True when the index is missing or older than any monitor cache folder (adding a file bumps its mtime)."""
    if not INDEX.exists():
        return True
    t = INDEX.stat().st_mtime
    runs = monitor_runs()
    built = set(json.loads(INDEX.read_text()).get("runs") or [])
    return built != {d.name for d in runs} or any((d / "cache").stat().st_mtime > t for d in runs)


def strip_blobs(resp):
    """Copy of a response with encrypted reasoning ciphertext replaced by a length marker."""
    if not isinstance(resp, dict):
        return resp, 0
    n = 0
    out = json.loads(json.dumps(resp))
    for ch in out.get("choices") or []:
        for d in ((ch or {}).get("message") or {}).get("reasoning_details") or []:
            if isinstance(d, dict) and d.get("type") == "reasoning.encrypted" and isinstance(d.get("data"), str):
                d["data"] = f"<omitted by the viewer: encrypted reasoning, {len(d['data'])} chars>"
                n += 1
    return out, n


class Interner:
    def __init__(self):
        self.lines: list[str] = []
        self.ids: dict[str, int] = {}


def _intern(it: Interner, s: str) -> int:
    i = it.ids.get(s)
    if i is None:
        i = it.ids[s] = len(it.lines)
        it.lines.append(s)
    return i


def runs(ids: list[int]) -> list[int]:
    """Run-length form of a line-id list: -n after an id means the next n ids follow it consecutively."""
    out: list[int] = []
    for i in ids:
        if out and (out[-1] < 0 and prev + 1 == i):
            out[-1] -= 1
        elif out and out[-1] >= 0 and out[-1] + 1 == i:
            out.append(-1)
        else:
            out.append(i)
        prev = i
    return out


def encode(it: Interner, v):
    if isinstance(v, str) and len(v) >= MIN_CHUNKED:
        return {"$c": runs([_intern(it, s) for s in v.split("\n")])}
    if isinstance(v, dict):
        if "$c" in v:
            raise ValueError("record already has a $c key; encoding would be ambiguous")
        return {k: encode(it, x) for k, x in v.items()}
    if isinstance(v, list):
        return [encode(it, x) for x in v]
    return v


def build() -> dict:
    runs = monitor_runs()
    by_ep: dict[str, list] = defaultdict(list)
    skipped = defaultdict(int)
    for d in runs:
        for p in sorted((d / "cache").glob("*.json")):
            r = json.loads(p.read_text())
            m = STEP_RE.match(r.get("step_id") or "")
            if not m:
                skipped[f"{d.name}: step_id not parsable"] += 1
                continue
            by_ep[f"{m['run']}/{m['file']}"].append((d.name, int(m["idx"]), r))
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    index, total, blobs = {}, 0, 0
    for ep_key, calls in sorted(by_ep.items()):
        run, file = ep_key.split("/")
        ep_path = RUNS / run / "episodes" / file
        if not ep_path.exists():
            skipped[f"episode file missing ({run})"] += len(calls)
            continue
        reqs = json.loads(ep_path.read_text()).get("requests") or []
        it, out = Interner(), []
        mon_runs = sorted({c[0] for c in calls})
        for src, idx, r in sorted(calls, key=lambda c: (c[1], c[2]["monitor"], c[2]["prompt"], c[2]["level"], c[0])):
            if not (0 <= idx < len(reqs)) or reqs[idx].get("actor") != "target":
                skipped[f"request_idx not a target request ({src})"] += 1
                continue
            resp, n = strip_blobs(r.get("response"))
            blobs += n
            out.append({"src": mon_runs.index(src), "ri": idx, "round": reqs[idx].get("round"), "key": r["key"],
                        "monitor": r["monitor"], "model": r.get("model"), "prompt": r.get("prompt"),
                        "prompt_sha": r.get("prompt_sha"), "level": r.get("level"), "option_order": r.get("option_order"),
                        "scenario": r.get("scenario"), "request_sha256": r.get("request_sha256"), "score": r.get("score"),
                        "parse_error": r.get("parse_error"), "cost": r.get("cost"), "attempts": r.get("attempts"),
                        "url": r.get("request_url"), "body": encode(it, r.get("request_body")), "resp": encode(it, resp),
                        "blob_omitted": n})
        if not out:
            continue
        name = f"{run}__{file.removesuffix('.json')}.js"
        payload = {"runs": mon_runs, "lines": it.lines, "calls": out}
        js = ("(window.MONDATA=window.MONDATA||{})[" + json.dumps(ep_key) + "]="
              + json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";\n")
        (OUT / name).write_text(js)
        total += len(out)
        index[ep_key] = {"file": name, "n": len(out), "runs": mon_runs, "steps": sorted({c["ri"] for c in out}),
                         "setups": sorted({f"{c['monitor']}:{c['prompt']}:{c['level']}" for c in out})}
    INDEX.write_text(json.dumps({"runs": [d.name for d in runs], "episodes": index, "skipped": dict(skipped)}, indent=1))
    size = sum(p.stat().st_size for p in OUT.iterdir())
    print(f"wrote {OUT} ({size / 1e6:.1f} MB): {len(index)} episodes, {total} monitor calls from {len(runs)} runs"
          + (f"; {blobs} encrypted reasoning blobs omitted" if blobs else "")
          + ("; skipped " + ", ".join(f"{k}: {v}" for k, v in skipped.items()) if skipped else "; nothing skipped"))
    return index


def ensure() -> dict:
    """The embedded index, rebuilding the sidecars first if a monitor cache changed."""
    if stale():
        build()
    return json.loads(INDEX.read_text()) if INDEX.exists() else {"runs": [], "episodes": {}}


if __name__ == "__main__":
    build()
