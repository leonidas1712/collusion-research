# Matched Qwen last-prompt label ladder

This post-hoc extension uses the audited 4,844-call cohort and saved splits from runs/20261026-1237-e05-qwen-percall. No new episode or activation is added. Eventual has 1,105 positive calls, this-or-next-round has 352, and the existing this-call endpoint has 101.

From the repository root, in the E05 Python environment:

```sh
PYTHONPATH=src python experiments/E05-probes/qwen_label_ladder.py --benchmark
PYTHONPATH=src python experiments/E05-probes/qwen_label_ladder.py --out runs/20261026-1313-e05-qwen-label-ladder
PYTHONPATH=src python experiments/E05-probes/qwen_label_ladder_check.py --out runs/20261026-1313-e05-qwen-label-ladder
```

The first command creates a new run; substitute its path to reproduce from scratch. The benchmark fits one fold at six threads; the full pass reuses it and uses three workers with two threads each. Both obey a six-thread cap. The source activation cache and local model caches are required for fitting and reconstruction checks. Source hashes are recorded in analysis_plan.json. Compact results include metrics.json, report.md, verification.json and lossless probe_scores.csv.gz.

Threshold calibration is per control call, even though the shared helper names its count calibration_episodes. Held-call alarm rates are not episode intervention rates. The original 4,697-call paper cohort and the 4,743-call strict-next cohort must not be presented as identical to this matched ladder.
