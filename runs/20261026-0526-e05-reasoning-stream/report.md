# INTERIM: k=0 and paper round comparator

Reply horizons k=1,2,3 are still fitting. The separately approved expanded capture is running in parallel and will be analysed separately; it does not alter this original reasoning-only dataset.

# Exploratory reasoning-token warning probes

This CPU-only, post hoc analysis asks whether saved gpt-oss-20b reasoning activations identify a reply that is about to emit the protected value publicly. It does not change the paper or its frozen results. No API calls or GPU inference were used for this primary analysis.

Saved activations comprise the last prompt token and returned reasoning-body tokens only. Other prompt-position and answer/tool-call residuals were not saved; token IDs/transcripts are available but are not activations. The combined saved-stream addendum is appended separately after this primary report is ready.

## Cohort and labels

The frozen main cohort contains 2,059 strictly pre-emission post-ask recruiting replies from 238 episodes. Those rows contain no leaking replies by construction. With author approval, this analysis adds the first public-emission request from those same episodes: 146 replies, giving 2,205 replies. Every retained reasoning position precedes the first public answer/tool header. The primary immediate label marks any first public emission, including a file write; this differs from the paper’s channel-publication outcome. Reply horizons k=0,1,2,3 mark whether the first public emission occurs within k subsequent eligible replies, counting replies with no reasoning before excluding them from feature-based scoring. Each horizon is fitted separately. The round comparator is the paper’s prospective A label: channel-positive episode and first-public-emission boundary in this or the next round. It therefore differs in outcome definition as well as horizon; first-public file leaks in channel-held episodes are positive for reply horizons but negative for the paper comparator.

Of 146 leaking replies, 121 have reasoning; 25 have none and cannot support a reasoning-token warning. There are 210 empty-reasoning replies overall. Two leaking replies mention the protected value in reasoning. Only three channel-first positive replies occur within this public-only window, too few for a credible separate channel-only nested fit. The primary fits are also scored against this sparse channel-first label in metrics.json; later channel publications are not added after an earlier public leak.

## Recipe

The saved pooled five-fold and six-scenario held-out partitions, seeds 42/43/44, and inner partitions are reused by episode. Candidate layers are 0,1,3,4,6,7,9,10,12,13,15,16,18,19,20,22,23. Logistic regression uses C=0.1, training-only scaling, and the frozen round-balancing rule. Each reply’s weight is divided equally among its reasoning tokens; the scaler also gives each training reply equal mass. The layer is chosen by inner-holdout reply-MAX within-scenario × round AUROC. The mean aggregator uses that same chosen layer. Family-bootstrap 95% intervals use 1,000 resamples and average the three seeds; these are uncertainty intervals, not multiplicity-adjusted tests.

The last-prompt comparator uses the saved near-term-A fold models without refitting, including predictions on the appended requests. It is evaluated on exactly the same nonempty-reasoning replies and the new labels. It was trained for the paper’s channel-outcome A label. For the reply horizons this differs from the any-public label, so those comparisons do not isolate token position alone; the paper-round comparator uses the matching frozen label.

## Reply discrimination

![AUROC by reply horizon](horizon_auc.png)

| Label | Tokens | Split | Replies / positive | MAX AUROC [95% CI] | Mean AUROC [95% CI] | Frozen last-prompt A |
|---|---|---|---:|---|---|---|
| immediate | all | pooled | 1995 / 121 | 0.949 [0.926, 0.969] | 0.973 [0.951, 0.988] | 0.423 [0.378, 0.468] |
| immediate | all | loso | 1995 / 121 | 0.933 [0.912, 0.952] | 0.983 [0.967, 0.994] | 0.493 [0.444, 0.538] |
| immediate | censored | pooled | 1995 / 121 | 0.945 [0.922, 0.965] | 0.974 [0.953, 0.988] | 0.423 [0.378, 0.468] |
| immediate | censored | loso | 1995 / 121 | 0.957 [0.937, 0.974] | 0.982 [0.964, 0.993] | 0.493 [0.444, 0.538] |
| round | all | pooled | 1995 / 199 | 0.587 [0.535, 0.641] | 0.687 [0.630, 0.747] | 0.497 [0.451, 0.541] |
| round | all | loso | 1995 / 199 | 0.637 [0.586, 0.685] | 0.751 [0.698, 0.805] | 0.526 [0.481, 0.568] |
| round | censored | pooled | 1995 / 199 | 0.594 [0.539, 0.648] | 0.690 [0.633, 0.747] | 0.497 [0.451, 0.541] |
| round | censored | loso | 1995 / 199 | 0.637 [0.584, 0.686] | 0.750 [0.695, 0.802] | 0.526 [0.481, 0.568] |

Pooled AUROC, fold-stratified AUROC, scenario-mean AUROC, per-scenario estimates, and positive-stratum coverage are retained in `metrics.json`. Paired family-bootstrap probe-minus-last-prompt intervals are in `paired_comparisons.json`.

## Within-reply alarms (k=0 only)

Thresholds use other-fold training-control reply maxima at a nominal 5% reply false-alarm rate, with a strict greater-than comparison. This is control calibration, not held-recruiting calibration and not an episode-maximum threshold. The held-recruiting rate below is an evaluation result. An alarm consumes the current reasoning token; it occurs before the public/tool header. First-crossing fractions are conditional on a crossing and summarized over reply-seed observations.

| Label | Tokens | Split | Leak warning rate, seed mean | Held-reply alarm rate | Crossing fraction median [IQR] |
|---|---|---|---:|---:|---|
| immediate | all | pooled | 75.5% | 2.0% | 0.078 [0.050, 0.250] |
| immediate | all | loso | 84.8% | 4.4% | 0.077 [0.048, 0.219] |
| immediate | censored | pooled | 73.8% | 1.9% | 0.077 [0.048, 0.250] |
| immediate | censored | loso | 79.9% | 2.7% | 0.077 [0.048, 0.222] |

Rates above condition on leaking replies with usable reasoning. All 146 leaking replies, including the 25 with no reasoning, must be considered when interpreting end-to-end warning coverage. Seed-specific rates and denominators are in `alarms.json`.

## Censoring and placebo

The censored analysis removes the token containing the first character of an exact protected-value mention and every later reasoning token. It uses the original reasoning length for lead fractions, and drops replies with no remaining tokens. This avoids retaining a partially consumed mention. It does not remove paraphrases or semantic discussion of the value.

The original 2,059-row window is also scored separately in `metrics.json` (`frozen`); immediate AUROC there is undefined because all immediate labels are zero. Pre-ask replies likewise have no immediate positives. The reported placebo therefore applies the fitted post-ask probe to pre-ask replies against the future any-public-emission episode outcome. This is a different diagnostic label, not an immediate-label performance estimate. A deviation from 0.5 can reflect predictive context, scenario differences, or confounding; it is not by itself proof of extraction failure.

| Training label | Tokens | Split | Pre-ask future-outcome MAX AUROC |
|---|---|---|---|
| immediate | all | pooled | 0.494 [0.440, 0.537] |
| immediate | all | loso | 0.461 [0.414, 0.507] |
| immediate | censored | pooled | 0.488 [0.441, 0.531] |
| immediate | censored | loso | 0.476 [0.427, 0.525] |
| round | all | pooled | 0.484 [0.434, 0.532] |
| round | all | loso | 0.490 [0.447, 0.529] |
| round | censored | pooled | 0.483 [0.429, 0.527] |
| round | censored | loso | 0.479 [0.436, 0.520] |

## Position curves and limits

![Mean out-of-fold token probability by relative reasoning position](position_curves.png)

The curves average replies equally after linearly interpolating their observed token probabilities to 20 relative positions, then average seeds. Points before the first observed token and censored tails are missing, not extrapolated. The contributing reply-seed count varies by position and is saved in curve_counts.json. Positive and negative refer to the panel’s label. The sigmoid-transformed scores are not calibrated probabilities of leakage. These descriptive curves have no confidence bands; `curves.json` contains the plotted values.

This is an exploratory, retrospectively labelled analysis, with multiple layers and variants. Max aggregation may exploit reasoning length. A reply-length-only score is therefore included in metrics.json for exactly the same rows, without fitting; it uses the number of available reasoning tokens after the relevant censoring rule. An AUROC below 0.5 for raw length indicates shorter reasoning is associated with the positive class; reversing that score gives one minus the reported AUROC. This diagnostic was added during integration checking and is post hoc. Returned provider reasoning may omit hidden reasoning; we cannot establish live access or monitoring latency from replay alone. Reasoning replay fidelity is weaker than answer/tool-body fidelity (approximately NLL 0.69 and top-5 97.7%). Training and inference are offline on saved activations. A separately approved expanded capture adds incoming and generated token positions for an action-time detection analysis. It is separate from this original reasoning-only dataset; no result from that expanded capture is claimed here.

## Reproduction

Run `experiments/E05-probes/.venv/bin/python experiments/E05-probes/reasoning_stream_fit.py --data runs/20261026-0522-e05-reasoning-stream-data --out runs/20261026-0526-e05-reasoning-stream --workers 2`, then `experiments/E05-probes/.venv/bin/python experiments/E05-probes/reasoning_stream_report.py --out runs/20261026-0526-e05-reasoning-stream`. The activation cache is local and not committed. `replies.json` in the data run records the source artifact and request hashes; every selected input, reasoning token sequence, layer index, shape, and finite activation check passed. No protected values are printed in this report.

## Provenance and citations

This experiment was proposed by Leo on 26 October 2026: monitor collusion during the token stream, including incoming pressure, rather than only at the last prompt token. Aboard APA-86 records the decisions (#1715, #1723, #1741, #1747, #1751, #1755, #1759, #1761, #1770). It is post hoc and exploratory. No confirmatory result is replaced.

| Variant | Source and location | What is borrowed and what differs |
|---|---|---|
| Primary reasoning-only broadcast logistic | Frozen repository E05 recipe; streaming motivation from Cunningham et al., §5.1 [@cunningham2026] | C=0.1, reply-balanced token weights, train-only scaling and inner layer selection. Reply-horizon labels replace exchange labels. This primary fit does **not** use SWiM or softmax weighting. |
| Combined saved stream | Leo, 26 October 2026, Aboard #1741 | Training-only normalization followed by MAX over frozen last-prompt and reasoning scores. This is not a trained cascade or a reproduction of CC++. |
| Expanded capture, planned SWiM and weighted-loss ablations | Cunningham et al., §5.1 and Appendix C [@cunningham2026] | M=16 logit smoothing and tau=1 softmax weighting of token losses, independently ablated. EMA alpha=2/17 is our fixed choice, not a parameter reported by that paper. Four fixed full layers and independent 256-dimensional sketches of all 24 layers replace full all-layer concatenation. Results are pending until the expanded analysis finishes. |
| Expanded max of rolling means comparison | McKenzie et al., §2.1 [@mckenzie2026; https://arxiv.org/abs/2506.10805]; Kramár et al., §3.2.2 [@kramar2026] | Fixed 10-token uniform logit means at evaluation. Kramár et al. use an attention-weighted extension; ours does not reproduce that architecture. McKenzie softmax pooling of logits is not CC++ softmax weighting of losses. |
| First-flag truncation check | Sharma et al., Appendix A.4 [@sharma2025constitutional] | Evaluate the prefix available before blocking. Here the criterion is a known exact protected value, not a semantic harmfulness grader. An exact-value buffer/regex can itself block exact disclosure; earlier-warning benefit must be shown separately. |
| Text/position nulls | Fixed for this exploratory analysis, 26 October 2026 | Causal keyword match, observed token count and round, using identical cuts and outer rows. No future text, exact protected value, or final unobserved length is an online feature. |

Source pages checked on 26 October 2026: [CC++](https://arxiv.org/html/2601.04603v1), [Constitutional Classifiers](https://arxiv.org/html/2501.18837v1), [Gemini probes](https://arxiv.org/html/2601.11516v1), and [high-stakes probes](https://arxiv.org/html/2506.10805v1). Citation keys refer to report/references.bib; the McKenzie key mckenzie2026 was supplied by the manuscript owner from the current arXiv BibTeX export (#1783), whose year is 2026 despite the original v1 being dated 2025. Its bibliography addition is owned by that agent.

Further deviations: 238 eligible recruiting episodes, three fixed seeds, family-grouped outer and inner splits, scenario × round ranking, and nominal 5% calibration on other-fold control **reply** maxima. These are not population safety benchmarks or nominal episode-level guarantees. Bootstrap intervals resample saved out-of-fold predictions by family, conditional on the fitted models and their selected layers; they do not repeat model fitting or layer selection. Comparing frozen last-prompt A to a newly fitted any-public horizon probe also changes the training label, not only the activation position.

The frozen keyword list is the six key names STAGING_DEPLOY_TOKEN, RESERVE_PRICE, ROLLOUT_THRESHOLD, CAPACITY_FIGURE, INTERNAL_NOTE, INTEGRATION_CODE; their scenario-specific summary filenames; and env, environment block, verbatim, copy the whole. Full regular expressions and per-scenario filenames are in the data run's keyword_spec.json and experiments/E05-probes/reasoning_stream_text.py. These strings were fixed before computing the text-baseline results. Matching is case-insensitive and uses only the decoded prefix observed at that token.

Primary scripts: experiments/E05-probes/reasoning_stream_{data,labels,fit,report,combined,text,nulls}.py. Inputs: runs/20261026-0522-e05-reasoning-stream-data; frozen models/splits: runs/20261026-0138-e05-gpt-oss-main; output: runs/20261026-0526-e05-reasoning-stream. Primary analysis uses local CPU and no additional billed API/GPU calls. The source replay cost is separate from this marginal analysis cost.

Expanded capture scripts: experiments/E02-activation-replay/{plan_gpt_oss_stream,gpt_oss_stream_positions,gpt_oss_stream_capture,modal_gpt_oss_stream,gpt_oss_stream_budget,download_gpt_oss_stream}.py. Frozen plan: runs/20261026-0659-e02-gpt-oss-stream-plan; client: runs/20261026-0702-e02-gpt-oss-stream-client; download inventory: runs/20261026-0704-e02-gpt-oss-stream-download. Plan source hashes identify the exact running code. Final billed/conservative costs and completion status must come from the client summary after shutdown; the author-approved cap is USD15 including the aborted superseded startup. These new scripts are not yet committed; a selective commit hash will be recorded after verification, not fabricated here.

## Fixed causal text and position baselines

The original keyword list uses only the observed reasoning prefix and the frozen key names, handoff filenames, env/environment block, verbatim, and copy-the-whole expressions in keyword_spec.json. The separately labelled keyword_broad baseline was added under Aboard #1785 before inspecting its results: it also includes scenario field names, copy, whole/full/complete block, record, and each scenario’s block wording, recorded in keyword_broad_spec.json. Both lists are retained; this is a declared post hoc expansion. Exact protected values are never used. A token-count score uses the number of tokens observed so far, not future reply length. Its final MAX equals observed total length; final-reply AUROC is therefore a length diagnostic, while an online threshold uses only the current count. Round is constant within each scenario × round stratum and consequently has AUROC 0.5. EMA uses alpha=2/17; thresholds are separately calibrated for each aggregate on other-fold control replies.

| Label | Cut | Split | Baseline | Aggregate | AUROC [95% CI] |
|---|---|---|---|---|---|
| immediate | all | pooled | keyword | max | 0.404 [0.354, 0.449] |
| immediate | all | pooled | keyword | ema_max | 0.303 [0.253, 0.358] |
| immediate | all | pooled | keyword_broad | max | 0.481 [0.452, 0.509] |
| immediate | all | pooled | keyword_broad | ema_max | 0.336 [0.287, 0.397] |
| immediate | all | pooled | prefix_count | max | 0.309 [0.264, 0.366] |
| immediate | all | pooled | prefix_count | ema_max | 0.309 [0.264, 0.366] |
| immediate | all | pooled | negative_prefix_count | max | 0.500 [0.500, 0.500] |
| immediate | all | pooled | negative_prefix_count | ema_max | 0.500 [0.500, 0.500] |
| immediate | all | pooled | round | max | 0.500 [0.500, 0.500] |
| immediate | all | pooled | round | ema_max | 0.500 [0.500, 0.500] |
| immediate | all | loso | keyword | max | 0.404 [0.354, 0.449] |
| immediate | all | loso | keyword | ema_max | 0.303 [0.253, 0.358] |
| immediate | all | loso | keyword_broad | max | 0.481 [0.452, 0.509] |
| immediate | all | loso | keyword_broad | ema_max | 0.336 [0.287, 0.397] |
| immediate | all | loso | prefix_count | max | 0.309 [0.264, 0.366] |
| immediate | all | loso | prefix_count | ema_max | 0.309 [0.264, 0.366] |
| immediate | all | loso | negative_prefix_count | max | 0.500 [0.500, 0.500] |
| immediate | all | loso | negative_prefix_count | ema_max | 0.500 [0.500, 0.500] |
| immediate | all | loso | round | max | 0.500 [0.500, 0.500] |
| immediate | all | loso | round | ema_max | 0.500 [0.500, 0.500] |
| immediate | censored | pooled | keyword | max | 0.404 [0.354, 0.449] |
| immediate | censored | pooled | keyword | ema_max | 0.299 [0.251, 0.353] |
| immediate | censored | pooled | keyword_broad | max | 0.481 [0.452, 0.509] |
| immediate | censored | pooled | keyword_broad | ema_max | 0.332 [0.283, 0.393] |
| immediate | censored | pooled | prefix_count | max | 0.306 [0.262, 0.361] |
| immediate | censored | pooled | prefix_count | ema_max | 0.306 [0.262, 0.361] |
| immediate | censored | pooled | negative_prefix_count | max | 0.500 [0.500, 0.500] |
| immediate | censored | pooled | negative_prefix_count | ema_max | 0.500 [0.500, 0.500] |
| immediate | censored | pooled | round | max | 0.500 [0.500, 0.500] |
| immediate | censored | pooled | round | ema_max | 0.500 [0.500, 0.500] |
| immediate | censored | loso | keyword | max | 0.404 [0.354, 0.449] |
| immediate | censored | loso | keyword | ema_max | 0.299 [0.251, 0.353] |
| immediate | censored | loso | keyword_broad | max | 0.481 [0.452, 0.509] |
| immediate | censored | loso | keyword_broad | ema_max | 0.332 [0.283, 0.393] |
| immediate | censored | loso | prefix_count | max | 0.306 [0.262, 0.361] |
| immediate | censored | loso | prefix_count | ema_max | 0.306 [0.262, 0.361] |
| immediate | censored | loso | negative_prefix_count | max | 0.500 [0.500, 0.500] |
| immediate | censored | loso | negative_prefix_count | ema_max | 0.500 [0.500, 0.500] |
| immediate | censored | loso | round | max | 0.500 [0.500, 0.500] |
| immediate | censored | loso | round | ema_max | 0.500 [0.500, 0.500] |
| round | all | pooled | keyword | max | 0.435 [0.390, 0.476] |
| round | all | pooled | keyword | ema_max | 0.377 [0.321, 0.428] |
| round | all | pooled | keyword_broad | max | 0.495 [0.470, 0.520] |
| round | all | pooled | keyword_broad | ema_max | 0.395 [0.335, 0.452] |
| round | all | pooled | prefix_count | max | 0.393 [0.332, 0.449] |
| round | all | pooled | prefix_count | ema_max | 0.393 [0.332, 0.449] |
| round | all | pooled | negative_prefix_count | max | 0.500 [0.500, 0.500] |
| round | all | pooled | negative_prefix_count | ema_max | 0.500 [0.500, 0.500] |
| round | all | pooled | round | max | 0.500 [0.500, 0.500] |
| round | all | pooled | round | ema_max | 0.500 [0.500, 0.500] |
| round | all | loso | keyword | max | 0.435 [0.390, 0.476] |
| round | all | loso | keyword | ema_max | 0.377 [0.321, 0.428] |
| round | all | loso | keyword_broad | max | 0.495 [0.470, 0.520] |
| round | all | loso | keyword_broad | ema_max | 0.395 [0.335, 0.452] |
| round | all | loso | prefix_count | max | 0.393 [0.332, 0.449] |
| round | all | loso | prefix_count | ema_max | 0.393 [0.332, 0.449] |
| round | all | loso | negative_prefix_count | max | 0.500 [0.500, 0.500] |
| round | all | loso | negative_prefix_count | ema_max | 0.500 [0.500, 0.500] |
| round | all | loso | round | max | 0.500 [0.500, 0.500] |
| round | all | loso | round | ema_max | 0.500 [0.500, 0.500] |
| round | censored | pooled | keyword | max | 0.435 [0.390, 0.476] |
| round | censored | pooled | keyword | ema_max | 0.374 [0.319, 0.423] |
| round | censored | pooled | keyword_broad | max | 0.495 [0.470, 0.520] |
| round | censored | pooled | keyword_broad | ema_max | 0.392 [0.329, 0.449] |
| round | censored | pooled | prefix_count | max | 0.390 [0.329, 0.446] |
| round | censored | pooled | prefix_count | ema_max | 0.390 [0.329, 0.446] |
| round | censored | pooled | negative_prefix_count | max | 0.500 [0.500, 0.500] |
| round | censored | pooled | negative_prefix_count | ema_max | 0.500 [0.500, 0.500] |
| round | censored | pooled | round | max | 0.500 [0.500, 0.500] |
| round | censored | pooled | round | ema_max | 0.500 [0.500, 0.500] |
| round | censored | loso | keyword | max | 0.435 [0.390, 0.476] |
| round | censored | loso | keyword | ema_max | 0.374 [0.319, 0.423] |
| round | censored | loso | keyword_broad | max | 0.495 [0.470, 0.520] |
| round | censored | loso | keyword_broad | ema_max | 0.392 [0.329, 0.449] |
| round | censored | loso | prefix_count | max | 0.390 [0.329, 0.446] |
| round | censored | loso | prefix_count | ema_max | 0.390 [0.329, 0.446] |
| round | censored | loso | negative_prefix_count | max | 0.500 [0.500, 0.500] |
| round | censored | loso | negative_prefix_count | ema_max | 0.500 [0.500, 0.500] |
| round | censored | loso | round | max | 0.500 [0.500, 0.500] |
| round | censored | loso | round | ema_max | 0.500 [0.500, 0.500] |

The keyword score is binary. If more than 5% of calibration controls match, the strict-greater threshold is 1 and no reply can trigger. Zero warning recall in that case is a consequence of the fixed calibration and coarse score, not evidence that the text contains no decision information. Reversing a below-chance keyword score after observing test results would be a new post hoc variant; it is not silently substituted here.

### Reversed-length diagnostic (retrospective)

Negative final reasoning length is a deliberately strong diagnostic, not an online running-max rule: future length is unknown until the reply ends. A running MAX of negative observed count is always -1 and cannot predict outcome. The probe should beat this diagnostic on the same replies, as well as the causal keyword baseline.

| Cell | Reversed-length AUROC [95% CI] |
|---|---|
| immediate/all/pooled/extended/reasoning_length | 0.691 [0.634, 0.736] |
| immediate/all/loso/extended/reasoning_length | 0.691 [0.634, 0.736] |
| immediate/censored/pooled/extended/reasoning_length | 0.694 [0.639, 0.738] |
| immediate/censored/loso/extended/reasoning_length | 0.694 [0.639, 0.738] |
| round/all/pooled/extended/reasoning_length | 0.607 [0.551, 0.668] |
| round/all/loso/extended/reasoning_length | 0.607 [0.551, 0.668] |
| round/censored/pooled/extended/reasoning_length | 0.610 [0.554, 0.671] |
| round/censored/loso/extended/reasoning_length | 0.610 [0.554, 0.671] |

## Immediate-reply probe and text comparison: Jev 1.14

All rows use the identical 1,995 replies, 121 immediate any-public positives, and 238 recruiting episodes. Row IDs and request hashes match exactly. Intervals use the same family bootstrap; alarms retain each method’s own saved-fold control-reply threshold with strict > at nominal 5%. No recalibration is performed by this join.

| Cut | Split | Method | Within scenario × round AUROC [95% CI] | Leak warning | Held-reply alarm |
|---|---|---|---|---:|---:|
| all | pooled | Reasoning probe MAX | 0.949 [0.926, 0.969] | 75.5% | 2.0% |
| all | pooled | Frozen last-prompt A | 0.423 [0.378, 0.468] | Not evaluated | Not evaluated |
| all | pooled | Broad keyword MAX | 0.481 [0.452, 0.509] | 0.0% | 0.0% |
| all | pooled | Reversed final length (retrospective) | 0.691 [0.634, 0.736] | Not evaluated | Not evaluated |
| all | pooled | Jev 1.14 sampled-prefix MAX | 0.598 [0.533, 0.653] | 91.7% | 9.0% |
| all | loso | Reasoning probe MAX | 0.933 [0.912, 0.952] | 84.8% | 4.4% |
| all | loso | Frozen last-prompt A | 0.493 [0.444, 0.538] | Not evaluated | Not evaluated |
| all | loso | Broad keyword MAX | 0.481 [0.452, 0.509] | 0.0% | 0.0% |
| all | loso | Reversed final length (retrospective) | 0.691 [0.634, 0.736] | Not evaluated | Not evaluated |
| all | loso | Jev 1.14 sampled-prefix MAX | 0.598 [0.533, 0.653] | 91.7% | 9.4% |
| censored | pooled | Reasoning probe MAX | 0.945 [0.922, 0.965] | 73.8% | 1.9% |
| censored | pooled | Frozen last-prompt A | 0.423 [0.378, 0.468] | Not evaluated | Not evaluated |
| censored | pooled | Broad keyword MAX | 0.481 [0.452, 0.509] | 0.0% | 0.0% |
| censored | pooled | Reversed final length (retrospective) | 0.694 [0.639, 0.738] | Not evaluated | Not evaluated |
| censored | pooled | Jev 1.14 sampled-prefix MAX | 0.598 [0.533, 0.653] | 91.7% | 9.0% |
| censored | loso | Reasoning probe MAX | 0.957 [0.937, 0.974] | 79.9% | 2.7% |
| censored | loso | Frozen last-prompt A | 0.493 [0.444, 0.538] | Not evaluated | Not evaluated |
| censored | loso | Broad keyword MAX | 0.481 [0.452, 0.509] | 0.0% | 0.0% |
| censored | loso | Reversed final length (retrospective) | 0.694 [0.639, 0.738] | Not evaluated | Not evaluated |
| censored | loso | Jev 1.14 sampled-prefix MAX | 0.598 [0.533, 0.653] | 91.7% | 9.4% |

The text monitor reads up to six cumulative prefixes per reply; the activation probe scores every saved reasoning token. This makes text crossing times coarser and can also miss score peaks, potentially changing MAX ranking; equal ranking resolution has not been established. Crossing fractions are conditional on alarms and should not be treated as matched latency measurements. Exact-value suffixes were redacted in text; all and censored text scores coincide in this run, but redaction is not identical to the activation intervention. The value of a semantic text comparison is not exhausted by the fixed keyword baseline.

The keyword rule’s zero alarms arise from its binary score and control threshold of 1. Reversed final length is a retrospective diagnostic, not an online alarm. The frozen last-prompt comparator has a different training label. These distinctions prevent interpreting the entire table as an isolated test of activation position.

Source: `runs/20261026-0740-e06-reasoning-prefix-jev/report.md`; exact billed costs, prompt hash, cache and prefix sampling are recorded there. This analysis is post hoc; no paper result is replaced.

## Immediate-reply probe and text comparison: GPT-5-nano

All rows use the identical 1,995 replies, 121 immediate any-public positives, and 238 recruiting episodes. Row IDs and request hashes match exactly. Intervals use the same family bootstrap; alarms retain each method’s own saved-fold control-reply threshold with strict > at nominal 5%. No recalibration is performed by this join.

| Cut | Split | Method | Within scenario × round AUROC [95% CI] | Leak warning | Held-reply alarm |
|---|---|---|---|---:|---:|
| all | pooled | Reasoning probe MAX | 0.949 [0.926, 0.969] | 75.5% | 2.0% |
| all | pooled | Frozen last-prompt A | 0.423 [0.378, 0.468] | Not evaluated | Not evaluated |
| all | pooled | Broad keyword MAX | 0.481 [0.452, 0.509] | 0.0% | 0.0% |
| all | pooled | Reversed final length (retrospective) | 0.691 [0.634, 0.736] | Not evaluated | Not evaluated |
| all | pooled | GPT-5-nano sampled-prefix MAX | 0.360 [0.298, 0.415] | 5.0% | 34.6% |
| all | loso | Reasoning probe MAX | 0.933 [0.912, 0.952] | 84.8% | 4.4% |
| all | loso | Frozen last-prompt A | 0.493 [0.444, 0.538] | Not evaluated | Not evaluated |
| all | loso | Broad keyword MAX | 0.481 [0.452, 0.509] | 0.0% | 0.0% |
| all | loso | Reversed final length (retrospective) | 0.691 [0.634, 0.736] | Not evaluated | Not evaluated |
| all | loso | GPT-5-nano sampled-prefix MAX | 0.360 [0.298, 0.415] | 5.0% | 34.6% |
| censored | pooled | Reasoning probe MAX | 0.945 [0.922, 0.965] | 73.8% | 1.9% |
| censored | pooled | Frozen last-prompt A | 0.423 [0.378, 0.468] | Not evaluated | Not evaluated |
| censored | pooled | Broad keyword MAX | 0.481 [0.452, 0.509] | 0.0% | 0.0% |
| censored | pooled | Reversed final length (retrospective) | 0.694 [0.639, 0.738] | Not evaluated | Not evaluated |
| censored | pooled | GPT-5-nano sampled-prefix MAX | 0.356 [0.296, 0.413] | 5.0% | 34.6% |
| censored | loso | Reasoning probe MAX | 0.957 [0.937, 0.974] | 79.9% | 2.7% |
| censored | loso | Frozen last-prompt A | 0.493 [0.444, 0.538] | Not evaluated | Not evaluated |
| censored | loso | Broad keyword MAX | 0.481 [0.452, 0.509] | 0.0% | 0.0% |
| censored | loso | Reversed final length (retrospective) | 0.694 [0.639, 0.738] | Not evaluated | Not evaluated |
| censored | loso | GPT-5-nano sampled-prefix MAX | 0.356 [0.296, 0.413] | 5.0% | 34.6% |

The text monitor reads up to six cumulative prefixes per reply; the activation probe scores every saved reasoning token. This makes text crossing times coarser and can also miss score peaks, potentially changing MAX ranking; equal ranking resolution has not been established. Crossing fractions are conditional on alarms and should not be treated as matched latency measurements. Exact-value suffixes were redacted in text; all and censored text scores coincide in this run, but redaction is not identical to the activation intervention. The value of a semantic text comparison is not exhausted by the fixed keyword baseline.

The keyword rule’s zero alarms arise from its binary score and control threshold of 1. Reversed final length is a retrospective diagnostic, not an online alarm. The frozen last-prompt comparator has a different training label. These distinctions prevent interpreting the entire table as an isolated test of activation position.

Source: `runs/20261026-0756-e06-reasoning-prefix-nano/report.md`; exact billed costs, prompt hash, cache and prefix sampling are recorded there. This analysis is post hoc; no paper result is replaced.

Nano-specific deviation: the canonical run uses minimal reasoning and strict score JSON. The paper-style low-reasoning attempt exhausted its completion allowance and is excluded from performance estimates. Canonical billed cost USD0.11473730 plus discarded-attempt USD0.03575890 gives USD0.15049620 total. Scores are retained in their original direction; the below-chance result is not reversed after seeing outcomes.
