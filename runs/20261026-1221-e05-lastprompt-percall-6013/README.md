# Last-prompt per-call ablation

See `report.md` for scope and results, `metrics.json` for full-precision intervals, and `fold_summary.json` for all 132 selected layers, validation candidates and thresholds. `probe_scores.csv.gz` is a lossless, deterministic compression of the generated OOF CSV. It retains row IDs, request hashes, seeds, folds, labels, scores and alarm indicators. `verification.json` records independent metric/model/threshold checks.

The original command was:

```sh
experiments/E05-probes/.venv/bin/python experiments/E05-probes/lastprompt_percall.py
```

For an environment managed by uv:

```sh
uv run --with numpy --with scipy --with scikit-learn --with threadpoolctl --with matplotlib --with torch python experiments/E05-probes/lastprompt_percall.py
```

The saved feature caches and source folds listed in `analysis_plan.json` must be present. This command creates a new run. To resume fits or regenerate summaries for this run, pass `--out runs/20261026-1221-e05-lastprompt-percall-6013`; to summarize without fitting, also pass `--summarize-only`. Cached fold fits are reused. Original execution used script commit `6e0b6f2ded3893811f82b65ec4c804a4da288581` (committed while the unchanged script was running); its SHA256 is in `verification.json`.

The immediate matched comparison changes activation position and aggregation while holding the outcome and eligible replies fixed. It demonstrates strong prediction from last-prompt features without generated reasoning. It does not prove equivalence: the LOSO paired last-prompt-minus-reasoning CI is [-0.0610102, +0.0001244], while the pooled CI excludes zero in favour of reasoning. Strict-next comparison is not matched in training label: last-prompt was refit strictly; saved reasoning fits used inclusive 0–1 horizons. The original paper endpoint also differs in outcome and cohort, so the entire improvement cannot be attributed to label choice alone.
