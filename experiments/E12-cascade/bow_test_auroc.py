"""Per-call AUROC of the E12 bag-of-words classifier on the Qwen test calls, and its paired difference from the probe.

Refits the classifier exactly as E12 does (add_bow: all development calls, latest-message view),
scores the 1,825 test calls, and applies the paper's metric (stream_metrics: within scenario and
round, 1000 family-bootstrap draws) and paired-difference code (as arxiv_fresh_comparisons.py).
Saved scores and CPU only.
"""
import csv, gzip, json, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT / "src"), str(ROOT / "experiments/E05-probes")]
from collusion.runs import start_run, write_json_atomic  # noqa: E402
from e12_cascade import PROBE, add_bow, load  # noqa: E402
from reasoning_stream_report import stream_metrics  # noqa: E402


def main():
    run = start_run("e12-bow-test-auroc", experiment="E12", parents=["20261027-2007-e12-cascade", PROBE.name],
                    settings=dict(saved_scores_only=True, no_api=True, no_gpu=True, bootstrap=1000))
    try:
        rows = load()
        fit = add_bow(rows)
        with gzip.open(PROBE / "probe_scores.csv.gz", "rt") as f:
            meta = {r["row_id"]: r for r in csv.DictReader(f)}
        for r in rows:
            m = meta[r["row_id"]]
            r.update(round=int(m["round"]), scenario=m["scenario"], family=m["family"])
        y = np.array([r["label"] for r in rows]); ids = np.arange(len(rows)); fold = np.zeros((1, len(rows)), int)
        probe = np.array([r["probe"] for r in rows])[None, :]
        bow = np.array([r["bow"] for r in rows])[None, :]
        p, pb = stream_metrics(rows, ids, y, probe, fold, 1000)
        b, bb = stream_metrics(rows, ids, y, bow, fold, 1000)
        d = pb["within_round"] - bb["within_round"]
        results = dict(bow_fit=fit, calls=len(rows), leaking_calls=int(y.sum()), probe=p, bow=b,
                       paired_difference=dict(value=p["within_round_auc"] - b["within_round_auc"],
                                              ci95=np.nanquantile(d, [.025, .975]).tolist()))
        write_json_atomic(run.dir / "metrics.json", results)
        with gzip.open(run.dir / "bow_scores.csv.gz", "wt", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["row_id", "label", "bow", "probe"]); w.writeheader()
            for r in rows:
                w.writerow({k: r[k] for k in ("row_id", "label", "bow", "probe")})
        run.result(bow_auc=b["within_round_auc"], probe_auc=p["within_round_auc"]); run.finish()
        print(run.dir)
        print(json.dumps({k: results[k] for k in ("calls", "leaking_calls", "paired_difference")}, indent=1))
        print("probe", p["within_round_auc"], p["within_round_ci95"], "bow", b["within_round_auc"], b["within_round_ci95"])
    except BaseException as e:
        run.finish("failed", str(e)); raise


if __name__ == "__main__":
    main()
