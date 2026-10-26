# Qwen per-call replication

The audit and frozen plan were committed in eb62523c before fitting. This is an exploratory replication after the gpt-oss result. See report.md and verification.json.

Run from the repository root in the E05 Python environment, with PYTHONPATH=src:

```sh
python experiments/E05-probes/qwen_percall.py --audit
# Review and commit the new output folder before fitting.
python experiments/E05-probes/qwen_percall.py --fit --out runs/20261026-1237-e05-qwen-percall --workers 3 --threads 2
python experiments/E05-probes/qwen_percall_check.py --out runs/20261026-1237-e05-qwen-percall
python experiments/E05-probes/qwen_percall_routes.py --out runs/20261026-1237-e05-qwen-percall
python experiments/E05-probes/qwen_percall_structure.py --out runs/20261026-1237-e05-qwen-percall
```

The audit creates a new run. Substitute that folder to reproduce from scratch. Source activation arrays and fitted model caches are local artifacts; paths and hashes are in frozen_plan.json. Saved OOF scores are losslessly compressed in probe_scores.csv.gz. Post-hoc checks reuse fits without reselection.

Execution used at most six CPU threads (three workers with two threads each), replacing the original two-thread execution limit without changing statistical choices; see execution_changes.json. The inherited threshold helper field calibration_episodes counts calibration reply indices here, not episodes. Calibration is at the control-reply level throughout.
