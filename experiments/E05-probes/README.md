# E05: can pre-action activations predict later rule violations?

Status: CPU core analysis in progress (APA-48). Inputs are the verified E02 main replay and provisional target-authored step-position labels. No model API calls, GPU runs or commits are part of this experiment.

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

Each run uses src/collusion/runs.py:start_run. It preserves frozen joins, source hashes, selected layers, fitted coefficients, fold assignments, calibration thresholds and all out-of-fold predictions. Features are cached locally from saved NPZs; no inference is performed.

Implementation references: [scikit-learn logistic regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) and [stratified group splitting](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html). The environment is pinned to scikit-learn1.8.0; current web documentation may describe a newer version.

The first fit (20261024-1935-e05-probe-core) stopped on a dual-solver convergence warning before any evaluation results. The solver changed to L-BFGS at the same fixed C=0.1; its completed feature cache is reused with explicit lineage.
