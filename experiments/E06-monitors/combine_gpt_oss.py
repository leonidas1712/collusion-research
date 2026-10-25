"""GPT-OSS probe + monitor combination test using the frozen Qwen Table 2 recipe."""
import argparse
import csv
from collections import defaultdict
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT / "experiments/E05-probes"), str(ROOT / "src")]
from collusion.runs import start_run, write_json_atomic  # noqa: E402
from combine import FIXED, POSTHOC, REPS, run_case, wr  # noqa: E402
from monitors import collect  # noqa: E402


def load_probe(path):
    out = defaultdict(lambda: defaultdict(dict))
    with path.open() as fh:
        for row in csv.DictReader(fh):
            if row["method"] != "nested" or row["window"] != "post_ask" or row["condition"] != "recruiting":
                continue
            key = (row["label_variant"], row["analysis"])
            item = (int(row["fold"]), float(row["score"]), int(row["label"]), row["request_sha256"])
            assert row["row_id"] not in out[key][int(row["seed"])]
            out[key][int(row["seed"])][row["row_id"]] = item
    return out


def main(probe_csv, monitor_run, data_path):
    data = {}
    for line in data_path.read_text().splitlines():
        row = json.loads(line)
        data[row["row_id"]] = row
    mon_scores = defaultdict(dict)
    mon_hash = {}
    for row in collect(monitor_run / "cache"):
        if row["score"] is not None:
            name = f'{row["monitor"]} {row["prompt"]} L{row["level"]}'
            mon_scores[name][row["step_id"]] = float(row["score"])
            mon_hash[row["step_id"]] = row["request_sha256"]
    names = sorted(mon_scores)
    assert len(names) == 12 and FIXED in names and POSTHOC in names
    probe_all = load_probe(probe_csv)
    out = start_run("e06-gpt-oss-combination", experiment="E06",
                    parents=[str(probe_csv.relative_to(ROOT)), monitor_run.name],
                    settings={"recipe": "Qwen Table 2 combine.py", "method": "nested", "window": "post_ask",
                              "fixed_monitor": FIXED, "posthoc_monitor": POSTHOC, "bootstrap_reps": REPS,
                              "paid_cost_usd": 0})
    results = {}
    rng = np.random.default_rng(20261025)
    for (label, analysis), seeds in sorted(probe_all.items()):
        ids = sorted(set.intersection(*[set(rows) for rows in seeds.values()]))
        ids = [row_id for row_id in ids if all(row_id in mon_scores[name] for name in names)]
        assert ids
        for row_id in ids:
            assert data[row_id]["request_sha256"] == mon_hash[row_id]
            assert all(seeds[seed][row_id][3] == mon_hash[row_id] for seed in seeds)
        meta = {"round": np.array([data[i]["round"] for i in ids], float),
                "loglen": np.log(np.array([data[i]["n_tokens"] for i in ids], float)),
                "scenario": np.array([data[i]["scenario"] for i in ids]),
                "family": np.array([data[i]["family"] for i in ids])}
        mon = {name: np.array([mon_scores[name][i] for i in ids]) for name in names}
        per_seed, chosen_all = [], defaultdict(int)
        for seed, rows in sorted(seeds.items()):
            folds = np.array([rows[i][0] for i in ids])
            probe = np.array([rows[i][1] for i in ids])
            y = np.array([rows[i][2] for i in ids])
            scores, chosen = run_case(ids, folds, probe, y, meta, mon, names)
            per_seed.append((y, scores, np.array([f"{fold}|{scenario}" for fold, scenario in zip(folds, meta["scenario"])])))
            for name in chosen:
                chosen_all[name] += 1
        y0 = per_seed[0][0]
        assert all(np.array_equal(y0, item[0]) for item in per_seed)
        fold_score = lambda name: float(np.mean([wr(y, scores[name], meta["round"], fold_scenario)
                                                 for y, scores, fold_scenario in per_seed]))
        point = {name: float(np.mean([wr(y, scores[name], meta["round"], meta["scenario"])
                                     for y, scores, _ in per_seed])) for name in per_seed[0][1]}
        pairs = {"selected": ("selected_comb", "selected_base"),
                 "fixed": ("fixed_comb", "fixed_base"),
                 "posthoc": ("posthoc_comb", "posthoc_base"),
                 "monitor+monitor": ("mm_comb", "mm_base"),
                 "posthoc monitor vs probe alone": ("posthoc_base", "probe_alone")}
        families, codes = np.unique(meta["family"], return_inverse=True)
        boots = defaultdict(list)
        for _ in range(REPS):
            weight = rng.multinomial(len(families), np.ones(len(families)) / len(families))[codes].astype(float)
            for name, (a, b) in pairs.items():
                delta = [wr(y, scores[a], meta["round"], meta["scenario"], weight) -
                         wr(y, scores[b], meta["round"], meta["scenario"], weight)
                         for y, scores, _ in per_seed]
                boots[name].append(np.mean(delta))
        result = {"rows": len(ids), "positives": int(y0.sum()), "chosen_monitor_counts": dict(chosen_all),
                  "auc": point,
                  "auc_fold_stratified": {name: fold_score(name) for name in per_seed[0][1]},
                  "diff_fold_stratified": {name: fold_score(a) - fold_score(b) for name, (a, b) in pairs.items()},
                  "diff": {name: {"diff": point[a] - point[b],
                                  "ci95": [float(q) for q in np.nanquantile(boots[name], [.025, .975])]}
                           for name, (a, b) in pairs.items()}}
        results[f"{label} | {analysis}"] = result
        print(label, analysis, {k: round(v["diff"], 3) for k, v in result["diff"].items()}, flush=True)
    write_json_atomic(out.dir / "metrics.json", results)
    write_report(out.dir, results)
    out.result(cases=len(results), row_hash_join=True)
    out.finish("finished")
    print(out.dir)


def write_report(directory, results):
    lines = ["# GPT-OSS combination test: does the activation probe add to a text monitor?", "",
             "This uses the frozen Qwen Table 2 recipe: stacked logistic regression on `[round, log length, monitor]` versus the same features plus the activation-probe score. Models are trained on the other folds of the probe's saved outer split and applied to its held-out fold. Inputs are restricted to canonical `method=nested`, `window=post_ask` recruiting rows and joined to monitor scores by row ID and request hash.", "",
             f"The fixed monitor is {FIXED}; the post-hoc monitor is {POSTHOC}. The selected monitor is chosen by within-scenario×round AUROC on each outer training fold only. Estimates average three split seeds; gain intervals use {REPS} paired family-bootstrap draws.", "",
             "| Label · analysis | Rows (positive) | Probe alone | Post-hoc monitor base | + probe | Gain [95% CI] | Fold-stratified gain | Selected gain [95% CI] | Fixed gain [95% CI] | Monitor+monitor gain [95% CI] |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    show = lambda value: f"{value['diff']:+.3f} [{value['ci95'][0]:+.3f}, {value['ci95'][1]:+.3f}]"
    for key, result in results.items():
        auc, delta = result["auc"], result["diff"]
        lines.append(f"| {key.replace(' | ', ' · ')} | {result['rows']} ({result['positives']}) | "
                     f"{auc['probe_alone']:.3f} | {auc['posthoc_base']:.3f} | {auc['posthoc_comb']:.3f} | "
                     f"{show(delta['posthoc'])} | {result['diff_fold_stratified']['posthoc']:+.3f} | "
                     f"{show(delta['selected'])} | {show(delta['fixed'])} | {show(delta['monitor+monitor'])} |")
    lines += ["", "## Training-fold monitor selections", ""]
    for key, result in results.items():
        counts = sorted(result["chosen_monitor_counts"].items(), key=lambda item: (-item[1], item[0]))
        lines.append(f"- {key}: " + ", ".join(f"{name} ×{count}" for name, count in counts))
    lines += ["", "This is CPU-only post-processing; paid cost is $0."]
    (directory / "report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-csv", required=True, type=Path)
    parser.add_argument("--monitor-run", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    args = parser.parse_args()
    main(args.probe_csv.resolve(), args.monitor_run.resolve(), args.data.resolve())
