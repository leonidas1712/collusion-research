"""Agreement between hand-labelled give-in kind and the automatic disclosure-kind labels, on a label batch.

    uv run python experiments/E01-behaviour-pilot/label_agreement.py
    uv run python experiments/E01-behaviour-pilot/label_agreement.py --labels ~/Downloads/human_labels_2026-10-25.json
    uv run python experiments/E01-behaviour-pilot/label_agreement.py --sample runs/20261025-1355-e01-label-batch-2/sample.jsonl

Reads hand labels (runs/human_labels.json by default, or a page export; both are {labels: [...]}) and a sample
written by sample_label_batch.py (default: the newest runs/*-e01-label-batch-2*/sample.jsonl). For each sampled
episode with a hand `give_in_kind` (deliberate / incidental / unclear) on a target turn, it compares that against
each automatic label in the sample (heuristic_kind, judge_kind, viewer_kind) and prints, per automatic label:
count compared, raw agreement %, a confusion table (rows human, columns automatic) and Cohen's kappa, plus the
same on a binary split (deliberate vs not deliberate). Episodes where the automatic label is missing are counted
and left out of that comparison. Standard library only, read-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
AUTO = ["heuristic_kind", "judge_kind", "viewer_kind"]
ORDER = ["deliberate", "incidental", "unclear", "mixed"]


def newest_sample() -> Path:
    hits = sorted(RUNS.glob("*-e01-label-batch-2*/sample.jsonl"))
    if not hits:
        sys.exit("no runs/*-e01-label-batch-2*/sample.jsonl; pass --sample")
    return hits[-1]


def human_kinds(labels: list[dict], sample: list[dict]) -> dict:
    """{(run, episode file): give_in_kind}; prefers the label on the give-in round, then the newest."""
    want = {(s["run"], s["episode_file"]): s["give_in_round"] for s in sample}
    best = {}
    for x in labels:
        k = (x.get("run"), x.get("episode"))
        if k not in want or x.get("scope") != "turn" or not x.get("give_in_kind"):
            continue
        rank = (x.get("round") == want[k], x.get("updated") or "")
        if k not in best or rank > best[k][0]:
            best[k] = (rank, x["give_in_kind"])
    return {k: v for k, (_, v) in best.items()}


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[c] * cb[c] for c in set(ca) | set(cb)) / n / n
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def report(name: str, pairs: list[tuple[str, str]]) -> None:
    n = len(pairs)
    agree = sum(a == b for a, b in pairs)
    k = kappa(pairs)
    print(f"  {name}: n={n}, agree {agree}/{n} = {100 * agree / n:.0f}%, Cohen's kappa = "
          + ("n/a" if k is None else f"{k:.2f}"))
    cats = [c for c in ORDER if any(c in p for p in pairs)] + sorted({c for p in pairs for c in p} - set(ORDER))
    w = max(12, *(len(c) + 2 for c in cats))
    print("    " + "human \\ auto".ljust(w) + "".join(c.rjust(w) for c in cats))
    cnt = Counter(pairs)
    for h in cats:
        if any(a == h for a, _ in pairs):
            print("    " + h.ljust(w) + "".join(str(cnt[(h, a)]).rjust(w) for a in cats))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--labels", default=str(RUNS / "human_labels.json"), help="hand labels JSON ({labels: [...]})")
    ap.add_argument("--sample", help="sample.jsonl from sample_label_batch.py (default: newest label-batch-2)")
    a = ap.parse_args()

    sample_path = Path(a.sample) if a.sample else newest_sample()
    sample = [json.loads(l) for l in sample_path.read_text().splitlines() if l.strip()]
    data = json.loads(Path(a.labels).expanduser().read_text())
    labels = data.get("labels", []) if isinstance(data, dict) else data
    human = human_kinds(labels, sample)
    print(f"sample: {sample_path} ({len(sample)} episodes)")
    print(f"labels: {a.labels}; {len(human)} of {len(sample)} sampled episodes have a hand give-in kind")
    if not human:
        return 0
    print("human give-in kind:", dict(Counter(human.values())))
    for field in AUTO:
        rows = [(human[(s["run"], s["episode_file"])], s.get(field)) for s in sample if (s["run"], s["episode_file"]) in human]
        pairs = [(h, au) for h, au in rows if au]
        print(f"\n{field} (automatic label present for {len(pairs)} of {len(rows)} labelled episodes)")
        if not pairs:
            continue
        report("all categories", pairs)
        report("binary (deliberate vs not)", [tuple("deliberate" if x == "deliberate" else "not deliberate" for x in p)
                                             for p in pairs])
    return 0


if __name__ == "__main__":
    sys.exit(main())
