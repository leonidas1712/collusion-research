"""Count Qwen3-32B test-episode target calls made before the first read of the protected file.

These calls are outside the scored window, so the paper reports no false-alarm rate on them.
Saved episodes and scores only; no model calls.
"""
import collections, csv, gzip, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from collusion.runs import start_run, write_json_atomic  # noqa: E402

OLD = Path("/Users/leo/collusion-research")  # read-only: saved episode files not in this clone
TEST = ROOT / "runs/20261026-2212-e05-arxiv-qwen-fresh-percall/probe_scores.csv.gz"


def episode(path):
    run, name = path.split("/", 1)
    p = ROOT / "runs" / run / "episodes" / name
    if not p.exists():
        p = OLD / "runs" / run / "episodes" / name
    return json.loads(p.read_text())


def main():
    run = start_run("e05-pre-read-calls", experiment="E05", parents=[TEST.parent.name],
                    settings=dict(saved_scores_only=True, no_api=True, no_gpu=True,
                                  rule="target calls with request index below the episode's first scored call"))
    try:
        with gzip.open(TEST, "rt") as f:
            rows = list(csv.DictReader(f))
        by = collections.defaultdict(list)
        for r in rows:
            by[r["episode"]].append((int(r["row_id"].rsplit("=", 1)[1]), int(r["round"])))
        pre = first_round_one = 0
        for name, calls in by.items():
            ep = episode(name)
            first, first_round = min(calls)
            pre += sum(q["actor"] == "target" for q in ep["requests"][:first])
            first_round_one += first_round == 1
        results = dict(episodes=len(by), scored_calls=len(rows), pre_read_calls=pre,
                       pre_read_share=pre / (pre + len(rows)), first_read_round_one=first_round_one)
        write_json_atomic(run.dir / "results.json", results)
        run.result(**results)
        run.finish()
        print(run.dir)
        print(json.dumps(results, indent=1))
    except Exception as e:
        run.finish("failed", str(e))
        raise


if __name__ == "__main__":
    main()
