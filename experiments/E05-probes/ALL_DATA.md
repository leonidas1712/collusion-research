# Activation probes and text monitors on the combined dataset

`all_data_main.py` estimates how well a target model’s activations and text monitors predict a rule violation. It uses `runs/20261025-1026-e05-replay3-data-1d95`, a combined cache of Qwen3-32B last-prompt-token activations and episode labels. Text-monitor scores come from `runs/20261025-0147-e06-monitor-main` and `runs/20261025-0841-e06-monitor-main-balanced`. Running this analysis requires those local artifacts; it makes no API calls and uses no GPU.

The four labels are eventual violation, action this round or next (A), that same near-action label contrasted only with held episodes (B), and action within three target requests contrasted with held episodes (C). B and C exclude earlier steps using hindsight. Only eligible recruiting steps enter probe training and ranking: after the first protected-token read and strictly before the first forbidden action.

The runner uses five family-grouped cross-validation folds and six leave-one-scenario-out rotations at seeds 42, 43 and 44. It also fits one deployment model per label and seed. Related episode families never cross a probe’s train/test or inner-training/validation boundary. A training-only inner split selects among 17 decoder blocks; fixed block 32 is secondary. Models use logistic C=0.1, training-only scaling, and equal positive/negative weight totals within each comparable round.

## Run and audit

Use the E05 Python environment documented in [README.md](README.md):

```sh
experiments/E05-probes/.venv/bin/python experiments/E05-probes/all_data_main.py --preflight-only
experiments/E05-probes/.venv/bin/python experiments/E05-probes/all_data_main.py --workers 3
experiments/E05-probes/.venv/bin/python experiments/E05-probes/all_data_validate.py <main-run-id>
experiments/E05-probes/.venv/bin/python experiments/E05-probes/finalize_all_data.py <main-run-id> <audit-run-id>
```

Each command creates a tracked run. The main run contains `report.md`, `metrics.json`, `probe_scores.csv`, the split plan, saved coefficients, and `deployable/README.md`. Finalization creates a separate report run, copies the score export and deployment models, adds a model index with checksums, and compresses the exact split plan. It leaves the fitted run unchanged. The large CSV and numerical arrays stay local; code and compact reports can be committed.

Four AUROC summaries are reported with paired family-bootstrap confidence intervals: comparisons within scenario and round; within fold, scenario and round; all pooled pairs; and the equal-weight mean of scenario-specific within-round results. Metrics average seed-specific AUROCs rather than raw scores. Bootstrap intervals condition on the fitted models.

The combination test uses the stacker in `experiments/E06-monitors/combine.py`: logistic regression on round, log prompt length and a monitor score, then adds the probe score or a second monitor. Its training rows use existing out-of-fold probe scores whose models may have trained on the outer test fold. This can optimistically bias the combination estimate; it is not a fully nested estimate. LOSO stackers use the same family-purged training rows as their probes.

The independent confirmation report is `runs/20261025-1030-e06-confirmation/report.md`. The all-data estimate includes those confirmation episodes, so it is not another independent confirmation.
