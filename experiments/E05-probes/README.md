# E05: can pre-action activations predict later rule violations?

Status: core analysis complete (APA-48). Inputs are the verified E02 main replay and provisional target-authored step-position labels. No model API calls, GPU runs or commits are part of this experiment.

[Final report and figures](../../runs/20261024-2007-e05-probe-core/report.md): 1,810 exposed steps from 92 recruiting episodes, 47 families. The inner-selected probe reaches within-round AUROC **0.658** (95% family-bootstrap CI 0.593–0.724), versus round0.500, prompt length0.530 and shuffled labels0.509. Control-calibrated episode recall is18.0%, with6.1% false alarms on held recruiting and3.5% on held-out controls. Exposure decoding reaches0.997 AUROC.

Deliberate-only AUROC is0.695; strict pre-action0.649; provisional no-visible-sharing-signal0.654; length-matched0.640. Strict family-disjoint tactic transfer is **0.481** (0.314–0.651), so these data do not demonstrate transfer; this restriction leaves onlyT0 training episodes. The result is modest within-dataset discrimination with weak alarm recall, not established general forecasting. Observation/reporting/mock-tool cues remain in the frozen source dataset.

Fit artifacts: `20261024-1937-e05-probe-core`; frozen bootstrap metrics: `20261024-1949-e05-probe-core`; final presentation/validation: `20261024-2007-e05-probe-core`. Earlier report renders remain for provenance. Seven code tests pass; saved selected/fixed-layer models reproduce all cross-validation scores exactly; group and calibration checks pass. CPU only, no commits.

The headline includes exposed, valid recruiting steps through the first forbidden action's input. Positives have semantic-judge publication kind deliberate or accidental; held recruiting episodes are negatives. A file-only violating episode without a judge kind is excluded from that headline and included in a deterministic-boundary sensitivity. Deliberate-only fits drop accidental episodes. Control/alone episodes only calibrate thresholds and measure false alarms, not outcome-probe training.

Before outcome fitting, the fixed recipe is: three seeds (42,43,44), five outer folds grouped by family; every fold must contain give-in, held, control and alone episodes. Invalid fold dealings are retried using categories only, before any models are fitted. Within each outer training set, one of four family-grouped folds serves as layer-selection validation. Candidates are blocks 0,4,...,60,63. All standardization and layer selection use training data only. Logistic regression uses fixed L2 C=0.1, L-BFGS, tolerance 1e-5, maximum 2000 iterations; convergence failure aborts rather than silently reporting it. Episode-split CV is a sensitivity, not the primary result.

Negative training weights match positive counts within each training round; rounds without both training classes are excluded. This prevents the easy long-held-history training shortcut. Fixed comparisons are layer32, mean logits over separately fitted blocks26–30, and a raw-residual difference-of-means at layer32 learned only from strictly pre-action steps, normalized by its training projection SD. Round-only (-round), prompt-length (+tokens), episode-shuffled outcomes, and the token-exposure positive control accompany the learned scores.

Headline AUROC is computed within round and averaged with positive-step counts as weights. Report pooled AUROC and eligible positive coverage as well. Per-fold thresholds permit at most floor(0.05*n) false alarms on calibration control/alone episode maxima; ties use strict greater-than. This finite sample cutoff often has realized calibration FPR below5%. Held recruiting false alarms and held-out control false alarms are separately reported.

All steps/retries of a family remain together. The primary uncertainty resamples families; episode-bootstrap intervals are also reported for the requested comparison. CIs condition on fitted out-of-fold scores and thresholds; repeat fold dealings show additional split variability. The position subset is share_signal_so_far=false and remains provisional. Length matching is one-to-one within round, minimizing absolute log token-length difference with a0.1 caliper. No prediction score enters matching.

Grouped tactic transfer trains T0–T2 and tests T3–T7. A second, stricter version removes test families from training/calibration; its surviving training tactics are reported rather than hidden. Exploratory layer curves never choose the headline layer on outer-test results.

Run with the local environment pinned in requirements-lock.txt:

    uv venv experiments/E05-probes/.venv --python 3.11
    uv pip sync --python experiments/E05-probes/.venv/bin/python experiments/E05-probes/requirements-lock.txt
    experiments/E05-probes/.venv/bin/python -m unittest discover -s experiments/E05-probes -p 'test_*.py'
    experiments/E05-probes/.venv/bin/python experiments/E05-probes/core.py
    experiments/E05-probes/.venv/bin/python experiments/E05-probes/report.py --fit-run <fit-run-id>

Each run uses src/collusion/runs.py:start_run. It preserves frozen joins, source hashes, selected layers, fitted coefficients, fold assignments, calibration thresholds and all out-of-fold predictions. Features are cached locally from saved NPZs; no inference is performed.

Implementation references: [scikit-learn logistic regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) and [stratified group splitting](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html). The environment is pinned to scikit-learn1.8.0; current web documentation may describe a newer version.

The first fit (20261024-1935-e05-probe-core) stopped on a dual-solver convergence warning before any evaluation results. The solver changed to L-BFGS at the same fixed C=0.1; its completed feature cache is reused with explicit lineage.

The report includes bootstrap intervals conditional on the saved predictions, per-seed values, partial AUROC, threshold false-alarm rates, visibility and length subsets, and exploratory PNG/SVG figures. A report may reuse frozen metrics with `--metrics-run <earlier-report-id>`; the new run records both parents. The `consequence_logged` source dataset includes an observation/review cue, so this experiment does not establish transfer to unlogged scenarios.

## Text comparison (APA-52)

[TF-IDF headline table and paired intervals](../../runs/20261024-2011-e05-text-baselines/report.md) uses exactly the saved main steps and outer/inner folds. Within-round AUROC: full rendered prompt **0.480**, prior target assistant text including tool calls **0.484**, target prose only **0.488**, versus activation probe **0.658**. Probe-minus-text paired family-bootstrap intervals are **+0.178 [0.076, 0.271]**, **+0.174 [0.081, 0.282]**, and **+0.169 [0.096, 0.262]**, respectively.

Vocabulary and IDF use training texts only. C is chosen from 0.1/1/10/100 on the saved inner validation split. These word-unigram baselines do not capture word order or semantic reasoning; beating them does not establish hidden intent or eliminate richer surface-text explanations. No sentence-embedding checkpoint was found in the local Hugging Face cache, and no weights were downloaded.

Reproduce with `experiments/E05-probes/.venv/bin/python experiments/E05-probes/text_baseline.py`. `validate_text.py` reconstructs all 45 saved text models and calibration cutoffs, and refits the feature extractors to verify training-only vocabulary/IDF. Ten code tests cover the core metrics, target-span extraction and exclusion of test-only vocabulary. [Artifact validation](../../runs/20261024-2013-e05-text-validation/summary.json) found zero score-reconstruction error for all 45 models and verified every cutoff. Mean training within-round AUROC was 0.986/0.957/0.875 for full/target/prose, respectively; the near-chance held-out results reflect poor generalization rather than an inability to fit the training data.

## Using the saved scores

The fit run's `rows.jsonl` has one row per original E02 index row, in the same order. Join monitors by `(episode, request_idx)` and verify `request_sha256`. Each variant's `predictions.npz` stores `eligible` row indices, `y`, and score arrays such as `nested`, `fixed32`, `band26_30` and `dom32`, shaped `[seed, original_row]`. Outside the variant's eligible set, outcome scores are NaN. `threshold_<method>` holds the matching outer-fold cutoff; compare with strict `>` and take the maximum over an episode for the raw alert. The main run's `positive_control` additionally covers unexposed steps.

`folds.json` records each seed's train, test, calibration and inner-validation episode IDs, group IDs, chosen layer and cutoff. Main `layer_scores` has shape `[seed, original_row, candidate_layer]`, ordered as `0,4,...,60,63`. Never select a new headline layer from these outer-test scores. Tactic-transfer arrays have one seed and a separate `transfer.json` describing their fixed train/test split.

## V1 branching check (APA-59c)

[Report and plot](../../runs/20261025-0000-e05-branching-check/report.md): all 34 recruiting branch points match replayed first target requests, but only 23 points from 20 families have finite eligible frozen OOF scores. The 11 excluded points lack token exposure (six also fail the original episode-validity filter). All 170 reruns are complete and their three-round outcomes match the summaries.

Mean frozen OOF logit versus the fraction giving in over five reruns: Spearman **0.527**, family-bootstrap 95% CI **[0.178, 0.772]**. This is a parent-step association: branches restart before the peer speaks, whereas the saved target prompt includes the original current-round peer message; none of the 170 new target requests exactly matches it. The strictly earlier-score sensitivity gives **0.149 [-0.299, 0.550]**. Selection by parent outcome, repeated points, five-sample fractions and the timing mismatch limit interpretation. No refits or inference. Reproduce the original checkpoint analysis with `branching_check.py`; the clean shared-state replay is reported below.

## Shared pooled-scenario scoring (APA-59)

Call `metrics.within_round(y, scores, rounds, weights, stratum_key=scenario_names)` for scenario×round AUROC, weighted by positive mass. `weights` is optional. Omit `stratum_key` for the legacy round-only metric. Keys must be hashable with one per row. Single-class strata are omitted and `positive_coverage` reports the retained positive mass; per-stratum details remain in `detail['rounds']`, with an added `stratum_key` field.

`evaluate.ranking_summary(..., stratum_key=scenario_names)` and `score_bootstrap(..., stratum_key=scenario_names)` use the same strata for point estimates and family-bootstrap intervals. Pooled AUROC remains unstratified and must be labeled as a reference. E06 should pass the same scenario array to both point estimates and intervals.

For pooled v2/spray results, the replay2 recipe includes a scenario-only baseline using each scenario's **training-fold episode** give-in rate, and a logistic scenario+round baseline (one-hot scenario plus numeric round, preprocessing fitted on training data). The added-value base model includes scenario, round and prompt length; compare adding the probe score with paired family-bootstrap intervals. All meta-model training scores must be generated within the outer training families, so outer-test families cannot leak indirectly through a stacking feature. For leave-one-scenario-out, the unseen scenario-only rate falls back to the overall training-episode rate: no test labels, hence a constant score within the held-out scenario. Report that baseline alongside each held-out scenario result.

## Replay2 CPU pipeline (APA-59)

The frozen recipe is [REPLAY2_ANALYSIS_PLAN.md](REPLAY2_ANALYSIS_PLAN.md). Replay2 uses the completed-request window strictly after first read and strictly before first action, including file-only action boundaries. This differs from the original v1 headline above. All pooled ranking comparisons and bootstrap intervals stratify by scenario × round.

After both E02 replay parts pass `verify_main.py`, run these CPU stages in order. Each command prints the run ID needed by the next command:

```sh
experiments/E05-probes/.venv/bin/python experiments/E05-probes/replay2_data.py <benchmark-replay-id> <main-replay-id>
experiments/E05-probes/.venv/bin/python experiments/E05-probes/replay2_positive_control.py <data-id>
experiments/E05-probes/.venv/bin/python experiments/E05-probes/replay2_branching.py <data-id>
experiments/E05-probes/.venv/bin/python experiments/E05-probes/replay2_core.py <data-id> <positive-control-id>
experiments/E05-probes/.venv/bin/python experiments/E05-probes/replay2_report.py <data-id> <fits-id> <positive-control-id> <branching-id>
```

The positive-control stage tests fixed decoder layer 32 first and stops below 0.95 AUROC, then records the full 64-layer curve. The outcome runner requires a passed gate. It fits the v2-only, pooled, LOSO and deliberate-only analyses. The report reconstructs saved logistic, metadata and MLP scores and checks split isolation before evaluation. The MLP runs on CPU; no stage above launches a GPU or calls a model API. The feature cache needs about 7.9 GB of disk space.

`replay2_pipeline.py` is the one-time continuation for the approved replay2 client. It waits for that specific client to finish and stop its app, downloads and verifies the main output, then runs the stages above. It stops on any failed stage. Do not start a duplicate while the original continuation is active.

Replay2 predictions retain `[seed, data_row]` score arrays. Threshold arrays are `[seed, data_row, target_fpr]`, with `fprs = [0.01, 0.05, 0.10, 0.20]`. `threshold_<method>` applies to raw scores; `ema_threshold_<method>` applies to causal EMA maxima. Both use strict `>`. Each cutoff is calibrated from benign training-fold episode maxima. Use the data run's `rows.jsonl` for joins and verify request/prompt hashes. `replay2_evaluate.alarm_results` counts any alarm as one episode event; its denominator is episodes with eligible steps, not every episode in the original dataset.

The pre-fit pooled split export for E06 is `runs/20261025-0240-e05-replay2-folds/`: `rows.jsonl` has manifest hashes and labels, `eligible.npy` selects the 4,184 eligible rows, and `folds.json` lists training, benign calibration and test rows/episodes/families for all 15 outer splits. It was generated without model fitting by `replay2_export_folds.py`, using the same `outer_cases` function as the probe fits. Score monitor predictions on test rows and calibrate cutoffs only on the matching calibration episodes.

[Clean shared-state branching](../../runs/20261025-0340-e05-replay2-branching/report.md) now uses the 23 replayed states before the new peer message. Frozen v1 family-held-out probes give Spearman −0.032, with family-bootstrap 95% CI [−0.460, 0.401]. This does not reproduce the earlier after-peer association. The new checkpoint differs from the probe's original training inputs, and five reruns per state give noisy fractions; the result does not rule out all shared-state predictors. The replay2 exposure gate passed at every layer (minimum AUROC 0.9999908; fixed layer 32 = 1.000).

## Replay2 final analysis

[Final report, metrics and plots](../../runs/20261025-0536-e05-replay2-analysis/report.md) cover v2, pooled six-scenario CV, LOSO, MLP, cross-fitted added value, deliberate-only sensitivity, clean branching, and episode alarm trade-offs. Inner-selected logistic scenario × round AUROC is 0.632 [0.474, 0.757] on v2, 0.522 [0.450, 0.591] pooled, and 0.551 [0.499, 0.597] in LOSO. MLP and added-value comparisons do not show a clear improvement. At the 5% training-benign target, pooled raw logistic recall is 3.2% with held-out benign FPR 5.6% (control-only 8.2%).

All 78 fold audits passed; pooled splits match the E06 export, and saved selected LR/metadata/MLP scores and LR/MLP cutoffs reconstruct within the recorded numerical tolerance (maximum score error 7.63e-6). All 18 tests pass. The [post-hoc baseline audit](../../runs/20261025-0533-e05-replay2-baseline-audit/report.md) explains below-chance training-prevalence CV baselines through cross-fold comparisons. Primary metrics are unchanged; no probe was refit or rescored under a new fold stratum. The final report flags this limitation and the below-chance v2 shuffled-label check.

Fits: `20261025-0340-e05-replay2-fits`; frozen numerical analysis: `20261025-0531-e05-replay2-analysis`; final narrative/package: `20261025-0536-e05-replay2-analysis`. `replay2_finalize.py` copies the frozen numerical artifacts and plots with hash checks, then adds the summary and audit caveat without recomputation.

### Near-term action labels (APA-62)

`near_term.py` reuses replay-2 features and the saved outer, inner-validation and stacking folds. A labels all eligible recruiting steps by whether the first action is in the current or next round. B drops earlier give-in steps, comparing near-action positives with held negatives. C uses B's contrast with at most three completed target requests until action. All retained steps precede the first action. It evaluates frozen eventual-label probes and refits inner-selected/fixed32 logistic probes, metadata baselines and a cross-fitted added-value model. Family-bootstrap ranking uses scenario × round, with fold × scenario × round as a sensitivity. The CSV includes each variant's exact labels and E06 row IDs.

```sh
experiments/E05-probes/.venv/bin/python experiments/E05-probes/near_term.py --workers 3
experiments/E05-probes/.venv/bin/python experiments/E05-probes/near_term_validate.py <run-id>
```

Status: complete. [Report](../../runs/20261025-0730-e05-near-term/report.md), [validation](../../runs/20261025-0840-e05-near-term-validation/summary.json). Nested scenario × round AUROC (pooled/LOSO): A 0.585/0.611; B 0.605/0.603; C 0.589/0.619. These are exploratory near-term results; the eventual-label headline is unchanged. The run contains `probe_scores.csv` (423,792 records, generated local artifact) with all methods, `label_variant`, E06 row IDs and new labels. All 99 fits and the CSV audit passed; no new episodes or GPU use. The initial run was stopped before LOSO fitting to correct reconstruction of a shared-family validation scenario; completed pooled fits were verified and reused. `test_near_term.py` checks exact reproduction of the saved stacking splits.

### Learning and per-layer curves (APA-67)

`learning_curve.py` compares eventual outcome and near-term B under pooled CV and LOSO. It samples 25/50/75/100% of the recruiting training families, with three nested draws per seed and unchanged test and inner-validation assignments. Only class/comparability failures cause a draw retry; the plan was frozen in `runs/20261025-0731-e05-learning-curve` before B's scores were evaluated. The 100% predictions are reused. It reports family-bootstrap scenario × round AUROC and the paired 75%→100% increment. The completed CPU run is `runs/20261025-0842-e05-learning-curve`; `runs/20261025-1003-e05-learning-curve-validation` verifies all 594 fits (exact score reconstruction and full-data reuse; no train/test family overlap). Only near-term B pooled nested has a positive 75%→100% interval: +.033 [.003,.066]; B LOSO is −.008 [−.037,.019]. Eventual-label final increments all include zero. These conditional intervals do not establish saturation, and pooled ranks remain sensitive to cross-fold score calibration.

```sh
experiments/E05-probes/.venv/bin/python experiments/E05-probes/learning_curve.py 20261025-0730-e05-near-term --workers 3 --plan-run 20261025-0731-e05-learning-curve
experiments/E05-probes/.venv/bin/python experiments/E05-probes/learning_curve_validate.py <curve-run> 20261025-0730-e05-near-term
experiments/E05-probes/.venv/bin/python experiments/E05-probes/layer_diagnostic.py 20261025-0730-e05-near-term --workers 3
```

The completed [per-layer diagnostic](../../runs/20261025-1003-e05-layer-diagnostic/report.md) shows all 17 candidate layers with pointwise family confidence intervals, reusing saved scores/coefficients where available. Its CSV, PNG and PDF include all four label/analysis combinations. Descriptive maxima are eventual pooled layer32 (.576), eventual LOSO layer8 (.574), near-term B pooled layer48 (.644), and B LOSO layer63 (.660). These outer-test maxima do not select a replacement for the inner-selected headline probe. Fixed32 score agreement is within 7.11e-15; the exported 2700×1950 PNG was visually inspected and its 300-dpi metadata verified.
