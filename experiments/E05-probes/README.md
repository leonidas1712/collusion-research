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

Mean frozen OOF logit versus the fraction giving in over five reruns: Spearman **0.527**, family-bootstrap 95% CI **[0.178, 0.772]**. This is a parent-step association: branches restart before the peer speaks, whereas the saved target prompt includes the original current-round peer message; none of the 170 new target requests exactly matches it. The strictly earlier-score sensitivity gives **0.149 [-0.299, 0.550]**. Selection by parent outcome, repeated points, five-sample fractions and the timing mismatch limit interpretation. No refits or inference. Reproduce with `branching_check.py`; v2 work remains queued.

## Shared pooled-scenario scoring (APA-59, pending v2)

Call `metrics.within_round(y, scores, rounds, weights, stratum_key=scenario_names)` for scenario×round AUROC, weighted by positive mass. `weights` is optional. Omit `stratum_key` for the legacy round-only metric. Keys must be hashable with one per row. Single-class strata are omitted and `positive_coverage` reports the retained positive mass; per-stratum details remain in `detail['rounds']`, with an added `stratum_key` field.

`evaluate.ranking_summary(..., stratum_key=scenario_names)` and `score_bootstrap(..., stratum_key=scenario_names)` use the same strata for point estimates and family-bootstrap intervals. Pooled AUROC remains unstratified and must be labeled as a reference. E06 should pass the same scenario array to both point estimates and intervals.

For pooled v2/spray results, the queued plan includes a scenario-only baseline using each scenario's **training-fold episode** give-in rate, and a logistic scenario+round baseline (one-hot scenario plus numeric round, preprocessing fitted on training data). The added-value base model includes scenario, round and prompt length; compare adding the probe score with paired family-bootstrap intervals. All meta-model training scores must be generated within the outer training families, so outer-test families cannot leak indirectly through a stacking feature. For leave-one-scenario-out, the unseen scenario-only rate falls back to the overall training-episode rate: no test labels, hence a constant score within the held-out scenario. Report that baseline alongside each held-out scenario result.
