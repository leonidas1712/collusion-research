# Channel-window per-call sensitivity

This post-hoc appendix analysis expands the window to first channel publication while retaining the original 238 recruiting episode IDs. It admits calls after an earlier file disclosure. It is not the same-call endpoint comparison that proved infeasible (only three channel-positive calls among the original 1,995).

From the repository root with the E05 environment:

```sh
PYTHONPATH=src experiments/E05-probes/.venv/bin/python experiments/E05-probes/channel_window_percall.py --prepare-only
PYTHONPATH=src experiments/E05-probes/.venv/bin/python experiments/E05-probes/channel_window_percall.py --out runs/20261026-1340-e05-channel-window-percall
```

The first command creates a new folder; substitute it to reproduce from scratch. The second command reuses complete fits if present and repeats metric, model, threshold and family-separation checks. This run was fitted only after the six-thread Qwen ladder completed; the channel sensitivity used two CPU threads and no GPU or API calls.

Compact artifacts include counts.json, analysis_plan.json, rows.json.gz, probe_scores.csv.gz, metrics.json, report.md and verification.json. Activation arrays and fitted model caches are local. The original request and source-metadata hashes are recorded in the plan. Threshold helper calibration_episodes counts control-call indices here, not episodes.
