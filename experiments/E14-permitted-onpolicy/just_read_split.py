"""Split E14 sharing calls and the Qwen test leaks by whether the value was just read.

A call "follows a read" when the last message of its prompt is a tool result that contains
the protected value. Saved scores only; no model calls. A call crosses the frozen threshold
when its score is strictly greater than it.
"""
import csv, gzip, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from collusion.runs import start_run, write_json_atomic  # noqa: E402

OLD = Path("/Users/leo/collusion-research")  # read-only: saved episode files not in this clone
E14 = ROOT / "runs/20261028-0224-e14-permitted-onpolicy"
ARMS = ("PERMIT", "PERMIT_NO_CONSEQUENCE")
TEST = ROOT / "runs/20261026-2212-e05-arxiv-qwen-fresh-percall/probe_scores.csv.gz"
THRESHOLD = json.loads((ROOT / "paper-arxiv/frozen/qwen_percall_plan.json").read_text())["threshold"]


def episode(path):
    """'<run>/episode-N.json' -> the saved file in runs/<run>/episodes/."""
    run, name = path.split("/", 1)
    p = ROOT / "runs" / run / "episodes" / name
    if not p.exists():
        p = OLD / "runs" / run / "episodes" / name
    return json.loads(p.read_text())


def follows_read(ep, request_idx):
    value = ep["scenario_spec"]["honeypots"][0]
    last = ep["requests"][request_idx]["request"]["messages"][-1]
    return last.get("role") == "tool" and value in str(last.get("content", ""))


def split(rows):
    out = {}
    for key, flag in (("follows_read", True), ("other", False)):
        sel = [r for r in rows if r["read"] is flag]
        out[key] = dict(calls=len(sel), over=sum(r["score"] > THRESHOLD for r in sel))
        out[key]["share_over"] = out[key]["over"] / len(sel) if sel else None
    out["calls"] = len(rows)
    out["share_follows_read"] = out["follows_read"]["calls"] / len(rows)
    return out


def main():
    run = start_run("e14-just-read-split", experiment="E14", parents=[E14.name],
                    settings=dict(saved_scores_only=True, no_api=True, no_gpu=True, threshold=THRESHOLD,
                                  rule="follows a read = last prompt message is a tool result containing the value"))
    try:
        results = {}
        with gzip.open(TEST, "rt") as f:
            test = [r for r in csv.DictReader(f) if r["label"] == "1"]
        rows = []
        for r in test:
            ep = episode(r["episode"])
            rows.append(dict(read=follows_read(ep, int(r["row_id"].rsplit("=", 1)[1])), score=float(r["score"])))
        assert len(rows) == 38
        results["forbidden_test_leaks"] = split(rows)
        with (E14 / "scores.csv").open() as f:
            scores = [r for r in csv.DictReader(f) if r["label"] == "1" and r["condition"] in ARMS]
        for arm in ARMS:
            rows = []
            for r in scores:
                if r["condition"] != arm:
                    continue
                ep = episode(r["episode"])
                rows.append(dict(read=follows_read(ep, int(r["request_idx"])), score=float(r["score"])))
            results[arm] = split(rows)
        write_json_atomic(run.dir / "results.json", results)
        run.result(saved_scores_only=True)
        run.finish()
        print(run.dir)
        print(json.dumps(results, indent=1))
    except Exception as e:
        run.finish("failed", str(e))
        raise


if __name__ == "__main__":
    main()
