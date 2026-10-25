# gpt-oss prospective activation probes

96 of 128 channel-positive collection episodes have an eligible post-ask scoring window; 32 have none and do not enter post-ask AUROC. Collection outcomes and scoring-window coverage are distinct denominators.

The target outcome is channel publication. Eligible requests are strictly after the protected-value read and before the first public emission, including file/tool arguments. Episodes must be complete, exposed and have written a correct task summary at least once. Private reasoning does not censor the scoring window. Post-ask steps are primary; pre-ask steps are the separately fitted placebo. No targets are pooled.

Logistic regression uses C=0.1, a train-only scaler and E05 round-balanced weights. Layer selection uses only an inner 25% family holdout, or one training scenario for LOSO. Candidates are [0, 1, 3, 4, 6, 7, 9, 10, 12, 13, 15, 16, 18, 19, 20, 22, 23]; layer12 is the fixed secondary baseline. Outer family CV has five folds; LOSO has six scenarios; both use seeds42/43/44. Every test family is absent from training. Family bootstrap intervals use 1000 draws.

| Window | Label | Evaluation | Method | Within scenario × round AUROC [95% CI] | Fold-stratified AUROC | Steps / positives |
|---|---|---|---|---:|---:|---:|
| post_ask | eventual | pooled | nested | 0.533 [0.484, 0.579] | 0.530 | 2059 / 169 |
| post_ask | eventual | pooled | fixed12 | 0.499 [0.439, 0.561] | 0.517 | 2059 / 169 |
| post_ask | eventual | loso | nested | 0.511 [0.461, 0.565] | 0.511 | 2059 / 169 |
| post_ask | eventual | loso | fixed12 | 0.521 [0.457, 0.593] | 0.521 | 2059 / 169 |
| post_ask | A_hazard | pooled | nested | 0.526 [0.473, 0.574] | 0.531 | 2059 / 148 |
| post_ask | A_hazard | pooled | fixed12 | 0.535 [0.475, 0.594] | 0.548 | 2059 / 148 |
| post_ask | A_hazard | loso | nested | 0.528 [0.476, 0.578] | 0.528 | 2059 / 148 |
| post_ask | A_hazard | loso | fixed12 | 0.563 [0.499, 0.628] | 0.563 | 2059 / 148 |
| post_ask | B_round_contrast | pooled | nested | 0.533 [0.480, 0.581] | 0.555 | 2038 / 148 |
| post_ask | B_round_contrast | pooled | fixed12 | 0.535 [0.473, 0.594] | 0.556 | 2038 / 148 |
| post_ask | B_round_contrast | loso | nested | 0.529 [0.481, 0.579] | 0.529 | 2038 / 148 |
| post_ask | B_round_contrast | loso | fixed12 | 0.563 [0.497, 0.628] | 0.563 | 2038 / 148 |
| post_ask | C_step_contrast | pooled | nested | 0.538 [0.489, 0.584] | 0.556 | 2039 / 149 |
| post_ask | C_step_contrast | pooled | fixed12 | 0.530 [0.469, 0.590] | 0.544 | 2039 / 149 |
| post_ask | C_step_contrast | loso | nested | 0.530 [0.477, 0.579] | 0.530 | 2039 / 149 |
| post_ask | C_step_contrast | loso | fixed12 | 0.555 [0.488, 0.619] | 0.555 | 2039 / 149 |
| pre_ask | eventual | pooled | nested | 0.514 [0.477, 0.555] | 0.525 | 1141 / 489 |
| pre_ask | eventual | pooled | fixed12 | 0.511 [0.471, 0.555] | 0.531 | 1141 / 489 |
| pre_ask | eventual | loso | nested | 0.520 [0.489, 0.553] | 0.520 | 1141 / 489 |
| pre_ask | eventual | loso | fixed12 | 0.527 [0.491, 0.569] | 0.527 | 1141 / 489 |

A_hazard marks a channel-positive episode’s steps in the action round or preceding round; earlier positive-episode steps count as negative. B_round_contrast drops those earlier steps. C_step_contrast uses at most three target requests before first public emission and drops earlier positive-episode steps. File-only episodes retain the negative channel label but are censored at their first public emission.

metrics.json also contains pooled AUROC, scenario-mean AUROC, baseline rows, and a sensitivity scoring the same out-of-fold predictions after removing requests with absolute prompt-token gap >1. No refit is made for that sensitivity. probe_scores.csv includes controls for monitor alignment; ranking metrics use recruiting only. Per-fold calibration in fit.json uses maxima across training control episodes for nominal1/5/10/20% alarm thresholds.

For AkashML, a mid-turn prompt includes earlier same-turn reasoning. Qwen-comparable text monitors omit that private reasoning, so the input access differs. DekaLLM prompt formatting remains approximate. Returned reasoning-token activations are not used in this analysis.
