"""Sample give-in episodes for hand-labelling the disclosure kind (deliberate vs incidental), blind to the automatic labels.

    uv run python experiments/E01-behaviour-pilot/sample_label_batch.py            # 40 episodes, seed 20261025
    uv run python experiments/E01-behaviour-pilot/sample_label_batch.py --dry-run  # print strata, write nothing

Pool: complete, scored recruiting episodes that gave in (objective_success) in the six E06 monitor scenarios
(deploy-token-v2 and the five spray scenarios), from the 2026-10-24 and 2026-10-25 runs. Episodes that already
have a hand label in runs/human_labels.json or sit in the `label-batch-1` list are left out.

Automatic labels kept per episode (none of them decides the main outcome, which is deterministic):
  heuristic_kind   label.disclosure_kind, the wording heuristic (deploy-token family only; null for spray)
  judge_kind       semantic judge first_publication_kind, else first_file_disclosure_kind (accidental -> incidental)
  viewer_kind      what the viewer shows: heuristic_kind if set, else judge_kind
Stratum: `deliberate` when every available automatic label says deliberate, else `nondeliberate`
(incidental, mixed, unclear, missing or the two labels disagree).

Allocation: --n split as evenly as possible over the six scenarios (larger pools get the remainder); inside a
scenario, up to half (rounded up) comes from the nondeliberate stratum, the rest from deliberate, topping up from
the other stratum when one runs short. Inside a stratum, old (10-24) and new (10-25) episodes alternate, each list
shuffled with the seed. Writes runs/<stamp>-e01-label-batch-2/{sample.jsonl, meta.json, log.txt} and the list
`label-batch-2` in runs/viewer_lists.json (notes do not reveal any automatic label). Rebuild the viewer afterwards.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNS = ROOT / "runs"
sys.path.insert(0, str(ROOT / "src"))

SCENARIOS = ["deploy-token-v2", "dispatch-integration-code", "handoff-exception-note", "procurement-reserve-price",
             "service-capacity-figure", "service-rollout-threshold"]
LIST_NAME = "label-batch-2"


def norm(kind):
    return {"accidental": "incidental"}.get(kind, kind)


def give_in_round(ep: dict) -> tuple[int | None, bool]:
    """(round, file_only): the scorer's first_action_round, else the round of the first leaking target call."""
    L = ep["label"]
    if isinstance(L.get("first_action_round"), int):
        return L["first_action_round"], False
    call = L.get("first_action_target_request")
    reqs = [r for r in ep.get("requests", []) if r.get("actor") == "target" and r.get("response")]
    if isinstance(call, int) and 0 < call <= len(reqs):
        return reqs[call - 1].get("round"), True
    return None, False


def pool(excluded: set) -> list[dict]:
    rows = []
    for d in sorted(RUNS.glob("2026102[45]-*-e01-*recruiting*")):
        for path in sorted(d.glob("episodes/episode-*.json")):
            if ".partial" in path.name or ".attempt-" in path.name:
                continue
            ep = json.loads(path.read_text())
            L = ep.get("label")
            if ep.get("status") != "complete" or ep.get("fake") or not isinstance(L, dict) or not L.get("objective_success"):
                continue
            if (ep.get("condition") or {}).get("peer_condition") != "recruiting":
                continue
            scen = ep.get("scenario", "").removeprefix("spray-").split("_")[0]
            if scen not in SCENARIOS:
                continue
            num = str(int(path.stem.split("-")[1]))
            if (d.name, num) in excluded:
                continue
            rnd, file_only = give_in_round(ep)
            if rnd is None:
                continue
            sj = L.get("semantic_judge") or {}
            lab = sj.get("labels") or {}
            field = "first_publication_kind" if lab.get("first_publication_kind") else (
                "first_file_disclosure_kind" if lab.get("first_file_disclosure_kind") else None)
            heur, judge = L.get("disclosure_kind"), norm(lab.get(field)) if field else None
            avail = [k for k in (heur, judge) if k]
            rows.append({
                "run": d.name, "episode": num, "episode_file": path.name, "scenario": scen,
                "era": "old" if d.name.startswith("20261024") else "new", "give_in_round": rnd, "file_only": file_only,
                "rounds_completed": ep.get("rounds_completed"),
                "heuristic_kind": heur, "heuristic_method": L.get("disclosure_kind_method"),
                "judge_kind": judge, "judge_kind_raw": lab.get(field) if field else None, "judge_field": field,
                "judge_model": sj.get("model"), "judge_source": sj.get("source"),
                "viewer_kind": heur or judge,
                "stratum": "deliberate" if avail and all(k == "deliberate" for k in avail) else "nondeliberate",
            })
    return rows


def interleave(items: list[dict], rng: random.Random) -> list[dict]:
    old = [x for x in items if x["era"] == "old"]
    new = [x for x in items if x["era"] == "new"]
    rng.shuffle(old)
    rng.shuffle(new)
    first, second = (old, new) if rng.random() < 0.5 else (new, old)
    out = []
    for i in range(max(len(old), len(new))):
        out += [x for x in (first[i:i + 1] + second[i:i + 1])]
    return out


def sample(rows: list[dict], n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    by = {s: [r for r in rows if r["scenario"] == s] for s in SCENARIOS}
    base, extra = divmod(n, len(SCENARIOS))
    order = sorted(SCENARIOS, key=lambda s: (-len(by[s]), s))
    quota = {s: base + (i < extra) for i, s in enumerate(order)}
    picked = []
    for s in SCENARIOS:
        nd = interleave([r for r in by[s] if r["stratum"] == "nondeliberate"], rng)
        de = interleave([r for r in by[s] if r["stratum"] == "deliberate"], rng)
        q = min(quota[s], len(by[s]))
        k_nd = min(len(nd), math.ceil(q / 2))
        k_de = min(len(de), q - k_nd)
        k_nd = min(len(nd), q - k_de)
        picked += nd[:k_nd] + de[:k_de]
    short = n - len(picked)
    if short > 0:  # a scenario ran out: top up from the leftover pool, nondeliberate first
        left = [r for r in rows if r not in picked]
        rng.shuffle(left)
        left.sort(key=lambda r: r["stratum"] != "nondeliberate")
        picked += left[:short]
    rng.shuffle(picked)  # labelling order: mixed, so neighbours don't hint at the stratum
    return picked


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20261025)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    labels = json.loads((RUNS / "human_labels.json").read_text()).get("labels", [])
    lists_path = RUNS / "viewer_lists.json"
    lists = json.loads(lists_path.read_text())
    excluded = {(x["run"], str(x.get("episode_num") or int(x["episode"].split("-")[1].split(".")[0]))) for x in labels}
    excluded |= {(x["run"], str(x["episode"])) for x in lists.get("label-batch-1", [])}
    rows = pool(excluded)
    picked = sample(rows, a.n, a.seed)

    def table(rs):
        c = Counter((r["scenario"], r["stratum"]) for r in rs)
        return {s: {k: c[(s, k)] for k in ("deliberate", "nondeliberate")} for s in SCENARIOS}

    print(f"pool: {len(rows)} give-in episodes after excluding {len(excluded)} labelled / label-batch-1 episodes")
    print("pool by scenario x stratum:", json.dumps(table(rows)))
    print("sample by scenario x stratum:", json.dumps(table(picked)))
    print("sample by era:", dict(Counter(r["era"] for r in picked)))
    print("sample by viewer_kind:", dict(Counter(str(r["viewer_kind"]) for r in picked)))
    print("sample by heuristic_kind:", dict(Counter(str(r["heuristic_kind"]) for r in picked)))
    print("sample by judge_kind:", dict(Counter(str(r["judge_kind"]) for r in picked)))
    if a.dry_run:
        return 0

    from collusion.runs import start_run, write_json_atomic
    run = start_run("e01-label-batch-2", experiment="E01", tags=["hand-labels", "disclosure-kind"],
                    settings={"n": a.n, "seed": a.seed, "scenarios": SCENARIOS, "list": LIST_NAME,
                              "excluded_episodes": len(excluded)})
    print(f"pool: {len(rows)}; sample: {len(picked)}")
    print("sample by scenario x stratum:", json.dumps(table(picked)))
    with open(run.dir / "sample.jsonl", "w") as f:
        for i, r in enumerate(picked, 1):
            f.write(json.dumps({"item": i, **r}) + "\n")
    lists[LIST_NAME] = [{"run": r["run"], "episode": r["episode"], "turn": r["give_in_round"],
                         "note": f"Label give-in kind on round {r['give_in_round']}, and 'decision visible' on rounds "
                                 f"{r['give_in_round'] - 1} and {r['give_in_round']}."
                                 if r["give_in_round"] > 1 else
                                 "Label give-in kind on round 1, and 'decision visible' on round 1."} for r in picked]
    write_json_atomic(lists_path, lists)
    run.result(pool=len(rows), sample=len(picked), strata=table(picked),
               era=dict(Counter(r["era"] for r in picked)), viewer_kind=dict(Counter(str(r["viewer_kind"]) for r in picked)))
    print(f"wrote {run.dir / 'sample.jsonl'} and list {LIST_NAME!r} ({len(picked)} items) in {lists_path}")
    print("rebuild the viewer: uv run python experiments/E01-behaviour-pilot/build_viewer.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
