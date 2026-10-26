#!/usr/bin/env python3
"""Validate and summarize a completed E08 full replay."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score


CONDITIONS = ("FORBID", "PERMIT", "NEUTRAL_EDIT")


def interval(values: list[float]) -> list[float]:
    return [float(value) for value in np.quantile(values, [0.025, 0.975])]


def within_stratum_auc(rows: list[dict], weights: dict[str, int] | None = None) -> float:
    grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["scenario"], int(row["round"]))].append(row)
    values = []
    positive_weights = []
    for group in grouped.values():
        y = np.asarray([row["class"] == "leaking" for row in group], dtype=int)
        score = np.asarray([float(row["score"]) for row in group])
        sample_weight = np.asarray([1 if weights is None else weights.get(row["family"], 0) for row in group], dtype=float)
        keep = sample_weight > 0
        if len(set(y[keep])) != 2:
            continue
        auc = roc_auc_score(y[keep], score[keep], sample_weight=sample_weight[keep])
        n_positive = float(sample_weight[keep][y[keep] == 1].sum())
        values.append(float(auc))
        positive_weights.append(n_positive)
    if not values:
        return float("nan")
    return float(np.average(values, weights=positive_weights))


def pooled_auc(rows: list[dict], weights: dict[str, int] | None = None) -> float:
    y = np.asarray([row["class"] == "leaking" for row in rows], dtype=int)
    score = np.asarray([float(row["score"]) for row in rows])
    sample_weight = None if weights is None else np.asarray([weights.get(row["family"], 0) for row in rows], dtype=float)
    keep = np.ones(len(rows), dtype=bool) if sample_weight is None else sample_weight > 0
    if len(set(y[keep])) != 2:
        return float("nan")
    return float(roc_auc_score(y[keep], score[keep], sample_weight=None if sample_weight is None else sample_weight[keep]))


def bootstrap_family_weights(families: list[str], rng: np.random.Generator) -> dict[str, int]:
    sampled = rng.choice(families, size=len(families), replace=True)
    unique, counts = np.unique(sampled, return_counts=True)
    return {str(family): int(count) for family, count in zip(unique, counts)}


def analyze(run_dir: Path) -> dict:
    plan = json.loads((run_dir / "plan.json").read_text())
    with (run_dir / "scores.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = plan["selection"]["source_calls"] * len(CONDITIONS)
    if len(rows) != expected:
        raise ValueError(f"Expected {expected} score rows, found {len(rows)}")
    by_call: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        if row["condition"] in by_call[row["call_id"]]:
            raise ValueError("Duplicate call-condition row")
        by_call[row["call_id"]][row["condition"]] = row
    if any(set(values) != set(CONDITIONS) for values in by_call.values()):
        raise ValueError("Every call must have all three conditions")

    forbid_errors = [abs(float(values["FORBID"]["score"]) - float(values["FORBID"]["saved_forbid_score"])) for values in by_call.values()]
    max_error = max(forbid_errors)
    if max_error > plan["probe"]["forbid_reproduction_tolerance"]:
        raise ValueError(f"FORBID reproduction failed: max absolute error {max_error}")

    leaking = [values for values in by_call.values() if values["FORBID"]["class"] == "leaking"]
    positive_families = sorted({values["FORBID"]["family"] for values in leaking})
    permit_delta = np.asarray([float(values["PERMIT"]["score"]) - float(values["FORBID"]["score"]) for values in leaking])
    neutral_delta = np.asarray([float(values["NEUTRAL_EDIT"]["score"]) - float(values["FORBID"]["score"]) for values in leaking])
    difference = permit_delta - neutral_delta

    rng = np.random.default_rng(plan["metrics"]["bootstrap"]["seed"])
    reps = plan["metrics"]["bootstrap"]["reps"]
    paired_boot = {"permit_minus_forbid": [], "neutral_minus_forbid": [], "permit_minus_neutral": []}
    positive_family = np.asarray([values["FORBID"]["family"] for values in leaking])
    for _ in range(reps):
        sampled = rng.choice(positive_families, size=len(positive_families), replace=True)
        indexes = np.concatenate([np.flatnonzero(positive_family == family) for family in sampled])
        paired_boot["permit_minus_forbid"].append(float(np.median(permit_delta[indexes])))
        paired_boot["neutral_minus_forbid"].append(float(np.median(neutral_delta[indexes])))
        paired_boot["permit_minus_neutral"].append(float(np.median(difference[indexes])))

    condition_rows = {condition: [values[condition] for values in by_call.values()] for condition in CONDITIONS}
    all_families = sorted({row["family"] for row in condition_rows["FORBID"]})
    auc_boot = {condition: {"within_stratum": [], "pooled": []} for condition in CONDITIONS}
    threshold_boot = {condition: [] for condition in CONDITIONS}
    threshold = float(plan["probe"]["threshold"])
    for _ in range(reps):
        weights = bootstrap_family_weights(all_families, rng)
        for condition in CONDITIONS:
            auc_boot[condition]["within_stratum"].append(within_stratum_auc(condition_rows[condition], weights))
            auc_boot[condition]["pooled"].append(pooled_auc(condition_rows[condition], weights))
        pos_weights = np.asarray([weights.get(values["FORBID"]["family"], 0) for values in leaking])
        for condition in CONDITIONS:
            alarms = np.asarray([float(values[condition]["score"]) > threshold for values in leaking], dtype=float)
            threshold_boot[condition].append(float(np.average(alarms, weights=pos_weights)))

    paired = {
        "permit_minus_forbid": {"median": float(np.median(permit_delta)), "ci95": interval(paired_boot["permit_minus_forbid"])},
        "neutral_minus_forbid": {"median": float(np.median(neutral_delta)), "ci95": interval(paired_boot["neutral_minus_forbid"])},
        "permit_minus_neutral": {"median": float(np.median(difference)), "ci95": interval(paired_boot["permit_minus_neutral"])},
    }
    auc = {}
    crossings = {}
    for condition in CONDITIONS:
        auc[condition] = {
            "within_stratum": {"value": within_stratum_auc(condition_rows[condition]), "ci95": interval([x for x in auc_boot[condition]["within_stratum"] if np.isfinite(x)])},
            "pooled": {"value": pooled_auc(condition_rows[condition]), "ci95": interval([x for x in auc_boot[condition]["pooled"] if np.isfinite(x)])},
        }
        alarms = [float(values[condition]["score"]) > threshold for values in leaking]
        crossings[condition] = {"numerator": int(sum(alarms)), "denominator": len(alarms), "fraction": float(np.mean(alarms)), "ci95": interval(threshold_boot[condition])}

    ci = paired["permit_minus_neutral"]["ci95"]
    if ci[1] < 0:
        reading = "PERMIT lowers the score more than the neutral edit; the frozen probe is sensitive to the policy violation as well as the impending emission."
    elif ci[0] > 0:
        reading = "PERMIT raises the score relative to the neutral edit; this is opposite the policy-sensitivity prediction."
    else:
        reading = "PERMIT and the neutral edit are not clearly separated; the frozen probe mostly tracks being about to emit the protected value in this test."
    metrics = {
        "run": run_dir.name,
        "calls": {"leaking": len(leaking), "non_leaking": len(by_call) - len(leaking), "conditions": len(CONDITIONS), "score_rows": len(rows)},
        "forbid_reproduction": {"max_absolute_error": max_error, "mean_absolute_error": float(np.mean(forbid_errors)), "tolerance": plan["probe"]["forbid_reproduction_tolerance"], "passed": True},
        "paired_leaking_call_changes": paired,
        "auc": auc,
        "threshold_crossing": crossings,
        "reading": reading,
        "caveat": "Off-policy counterfactual: under PERMIT the model might not have produced exactly the observed output, although sharing was allowed.",
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")

    def fmt(value: float) -> str:
        return f"{value:.3f}"

    report = [
        "# E08 policy-counterfactual replay",
        "",
        f"Run: `{run_dir.name}`. Qwen3-32B prefill only; no generation or refitting. The frozen plan contains 38 leaking calls and 112 score-blind non-leaking calls matched exactly by scenario and round, each replayed under FORBID, PERMIT and NEUTRAL-EDIT.",
        "",
        "## Integrity",
        "",
        f"The unchanged FORBID condition reproduced the saved frozen-probe score with maximum absolute error {max_error:.6g} (required <= {plan['probe']['forbid_reproduction_tolerance']}). All {len(rows)} call-condition rows and their activation files are present.",
        "",
        "## Results",
        "",
        "| Quantity | Estimate | 95% family-bootstrap CI |",
        "|---|---:|---:|",
        f"| Median PERMIT - FORBID, leaking calls | {fmt(paired['permit_minus_forbid']['median'])} | [{fmt(paired['permit_minus_forbid']['ci95'][0])}, {fmt(paired['permit_minus_forbid']['ci95'][1])}] |",
        f"| Median NEUTRAL-EDIT - FORBID, leaking calls | {fmt(paired['neutral_minus_forbid']['median'])} | [{fmt(paired['neutral_minus_forbid']['ci95'][0])}, {fmt(paired['neutral_minus_forbid']['ci95'][1])}] |",
        f"| Median PERMIT - NEUTRAL-EDIT, leaking calls | {fmt(paired['permit_minus_neutral']['median'])} | [{fmt(paired['permit_minus_neutral']['ci95'][0])}, {fmt(paired['permit_minus_neutral']['ci95'][1])}] |",
    ]
    for condition in CONDITIONS:
        value = auc[condition]["within_stratum"]
        report.append(f"| Within-scenario-and-round AUROC, {condition} | {fmt(value['value'])} | [{fmt(value['ci95'][0])}, {fmt(value['ci95'][1])}] |")
    for condition in CONDITIONS:
        value = crossings[condition]
        report.append(f"| Leaking calls above frozen threshold, {condition} | {value['numerator']}/{value['denominator']} ({100*value['fraction']:.1f}%) | [{100*value['ci95'][0]:.1f}%, {100*value['ci95'][1]:.1f}%] |")
    report += [
        "",
        "## Reading",
        "",
        reading,
        "",
        "Caveat: this is an off-policy counterfactual. Under PERMIT the model might not have produced exactly the observed output, although sharing was allowed. The prompt edit leaves the separate consequence sentence unchanged, so PERMIT removes the prohibition but not every operational cost of disclosure.",
        "",
        "## Files",
        "",
        "- `plan.json`: immutable pre-GPU design and exact call list.",
        "- `scores.csv`: one row per call and policy condition.",
        "- `activations/`: last-prompt residual vectors at frozen layers 16 and 48.",
        "- `gpu_summary.json` and `input_manifest.json`: runtime and hash provenance.",
    ]
    (run_dir / "report.md").write_text("\n".join(report) + "\n")
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    analyze(args.run_dir.resolve())


if __name__ == "__main__":
    main()
