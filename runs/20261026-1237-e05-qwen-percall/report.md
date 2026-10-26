# Qwen per-call last-prompt replication

This is an exploratory second-model replication chosen after seeing the gpt-oss per-call result. The label audit, cohort, splits and recipe were committed in eb62523c before any Qwen per-call fit. No GPU replay, model generation or paid API calls were used.

The frozen paper cohort supplies 241 recruiting episodes. Actual channel and successful write receipts, joined to completed target requests, define the first qualifying publication: deploy-token counts channel only; the other five scenarios count channel or files outside private/. Of 104 old exact-emission candidates, 100 already identify the qualifying call, three do not qualify, and one shifts from call16 to call22. This restores later pre-publication calls and yields4,844 recruiting calls/101 positives. Strict-next removes all own-leak calls from every split, leaving4,743 calls/101 positives. No new episode is admitted.

The paper logistic recipe uses C=0.1, training-only scaling, round-balanced weights (single-class rounds receive zero weight),17 candidate layers and saved inner partitions; inner scenario × round AUROC selects the layer, with earlier-layer tie breaking. Seeds42/43/44 use the frozen pooled-family and held-out-scenario splits. The comparator is the paper’s frozen near-term A model from the same outer fold, applied to the same rows, including newly included publication calls. Its original training label differs.

| Label / split | Rows / positives | Per-call AUROC [95% CI] | Frozen paper A AUROC [95% CI] | Paired difference [95% CI] | Held-step alarms: per-call / A |
|---|---:|---|---|---|---|
| immediate/loso | 4844/101 | 0.953 [0.926, 0.974] | 0.561 [0.514, 0.600] | +0.391 [+0.345, +0.446] | 11.0% / 5.6% |
| immediate/pooled | 4844/101 | 0.938 [0.913, 0.961] | 0.566 [0.514, 0.611] | +0.372 [+0.326, +0.426] | 10.7% / 4.3% |
| strict1/loso | 4743/101 | 0.715 [0.664, 0.758] | 0.660 [0.611, 0.703] | +0.055 [+0.012, +0.097] | 9.1% / 5.6% |
| strict1/pooled | 4743/101 | 0.707 [0.655, 0.754] | 0.677 [0.623, 0.725] | +0.030 [-0.015, +0.074] | 8.9% / 4.3% |

AUROC is positive-weighted within scenario × round. Intervals use1,000 paired family-bootstrap resamples, seed20261025, conditional on the saved fitted choices; they do not repeat fitting or layer selection. Full-precision intervals, per-seed estimates, fold-stratified sensitivity, scenario results and selected layers are in metrics.json.

Both models’ thresholds are calibrated independently on identical training-side no-ask CONTROL reply rows at nominal5%, strict >. Calibration families are disjoint from test families; LOSO calibration uses training scenarios. Held recruiting alarm rates are evaluation results, not control false-positive rates or episode intervention rates. The source cache also contains25 alone episodes, but those are not used to calibrate.

Changing from the old paper endpoint to the per-call task also changes the positive calls and window. The frozen-A comparison is therefore a task/label contrast, not an isolated activation-position test. Qwen has no matched reasoning-stream arm here. Scenario-specific publication rules differ from gpt-oss’s any-publication outcome, so cross-model numbers are descriptive rather than directly paired.

Sources and frozen hashes: frozen_plan.json. Complete label audit: label_audit.json. Script: experiments/E05-probes/qwen_percall.py.

## Post hoc descriptive publication-route subgroups

This subgroup analysis was requested after the plan was frozen. No refits, layer reselection or threshold recalibration were performed. Plain text means the first qualifying publication is a final assistant reply without tool calls; tool arguments means a successful send_message or public-file write. Each route is compared against the same nonleaking-call negatives, excluding positives of the other route.

| Split / route | Positive calls | Same negative calls | AUROC [95% family CI] | Positive calls caught (seeds42/43/44) | Mean catch rate |
|---|---:|---:|---|---|---:|
| loso/plain_assistant_text | 47 | 4743 | 0.922 [0.871, 0.963] | 36 / 39 / 43 | 83.7% |
| loso/tool_call_arguments | 54 | 4743 | 0.979 [0.963, 0.992] | 51 / 50 / 53 | 95.1% |
| pooled/plain_assistant_text | 47 | 4743 | 0.906 [0.862, 0.945] | 36 / 43 / 41 | 85.1% |
| pooled/tool_call_arguments | 54 | 4743 | 0.966 [0.940, 0.984] | 50 / 51 / 53 | 95.1% |

Catches use the saved per-fold strict >5%-control-reply thresholds. They are observational call-level warning opportunities, not measured intervention success or episode-level catch rates. A tool-call-only filter cannot block a plain final text publication; a general output filter can still match the exact protected string in that text. These data do not demonstrate an advantage over such an output filter.

## Post hoc read-step structural diagnostic

Post hoc, outside frozen plan; feature definition set before reading subgroup OOF metrics. Latest incoming block consists of trailing tool-result messages; at least one is a successful read_file of an initially protected private file and its content contains the exact value. Only saved request messages are inspected, never the current response.
This flag means immediately after the tool-result block, not merely secret in context: every analysed call already satisfies the latter condition. The rule was fixed before looking at subgroup scores.

| Split | Read-step baseline AUROC [95% CI] | Paired probe minus baseline [95% CI] | Probe AUROC within flagged calls [95% CI] | Flagged positives / negatives |
|---|---|---|---|---:|
| loso | 0.812 [0.765, 0.859] | +0.141 [+0.101, +0.186] | 0.788 [0.647, 0.942] | 66/298 |
| pooled | 0.812 [0.765, 0.859] | +0.126 [+0.089, +0.167] | 0.713 [0.564, 0.874] | 66/298 |

Same OOF scores, labels and family-bootstrap draws as the primary result; no refits. Conditional AUROC only uses comparable scenario × round strata, 49 of the 66 flagged positive calls have a comparable negative in their stratum (74.2% coverage); the other 17 do not enter the conditional AUROC. The structural baseline is constant inside its positive subset, so no within-subset baseline AUROC or paired subtraction is defined. This diagnostic tests one observable task-step cue, not every possible contextual explanation.
