# Matched Qwen last-prompt horizon ladder

This post-hoc analysis refits the paper logistic probe on eventual and this-or-next-round outcomes using the same 4,844 calls from 241 recruiting episodes as the immediate-publication replication. All 101 first qualifying publication calls are included in every horizon cohort. Publication follows the paper rule: deploy-token counts channel publication; the other five scenarios count channel publication or successful writes outside private/. Labels use the audited first-publication round, including its corrected dispatch cutoff.

The recipe and partitions are unchanged from runs/20261026-1237-e05-qwen-percall: C=0.1, training-only standardisation, round-balanced weights, zero weight for single-class training rounds, 17 candidate layers selected on the saved inner holdout, three seeds (42/43/44), pooled family folds and held-out-scenario rotations. No generated reasoning, GPU work or API calls are used.

| Label / split | Calls / positives | Refit AUROC [95% CI] | Frozen paper A AUROC [95% CI] | Paired difference [95% CI] | Held-call alarms |
|---|---:|---|---|---|---:|
| eventual/loso | 4844/1105 | 0.537 [0.501, 0.574] | 0.527 [0.500, 0.555] | +0.010 [-0.031, +0.051] | 8.0% |
| eventual/pooled | 4844/1105 | 0.511 [0.469, 0.557] | 0.548 [0.513, 0.582] | -0.037 [-0.083, +0.011] | 6.5% |
| round_near/loso | 4844/352 | 0.669 [0.632, 0.705] | 0.579 [0.541, 0.613] | +0.090 [+0.070, +0.110] | 5.7% |
| round_near/pooled | 4844/352 | 0.666 [0.626, 0.703] | 0.588 [0.548, 0.625] | +0.077 [+0.062, +0.094] | 3.6% |

AUROC is computed within scenario × round, with 1,000 paired family-bootstrap draws, seed 20261025, conditional on saved fitting and selection choices. The original paper A model is scored on identical rows using each new label, but its training task and cohort differ. The paired contrast is not an activation-position ablation.

Alarms use strict > thresholds targeting at most 5% of training-side no-ask control calls. Held recruiting alarm rates are evaluation results, not control false-positive rates or episode intervention rates. The threshold helper field calibration_episodes refers to control-call indices in this use.

For the same-cohort horizon ladder, combine these two rungs with immediate/loso or immediate/pooled in runs/20261026-1237-e05-qwen-percall/metrics.json. The strict-next-call result uses only 4,743 calls after excluding emitting calls, so it is a separate cohort. Unlike the old 4,697-call paper results, this ladder includes the qualifying publication calls. Different labels also change the positive set and single-class training weights; this is a matched-cohort task comparison, not proof of a causal mechanism.

Sources and hashes are in analysis_plan.json. Script: experiments/E05-probes/qwen_label_ladder.py. Saved OOF scores: probe_scores.csv.gz.
