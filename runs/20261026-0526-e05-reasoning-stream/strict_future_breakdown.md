# What “one reply ahead” means

Of the 116 strict-one-ahead positive replies, 113 precede another target call in the same round, and 3 precede a call in the next round. All 116 next prompts extend the earlier message list exactly. The intervening incoming item is a tool result in the same-round cases and a new user/peer message in the next-round cases.

Among the 113 same-round cases, the current reply calls `read_file` 109 times and the malformed name `read_file<|channel|>commentary` four times. Incoming tool content contains the protected value in 108 cases. These episodes were already exposed under the post-read eligibility rule. This concentration on a read-file step is a potential alternative explanation for the one-step ranking; the analysis does not isolate a general advance-warning signal.

| Positive subset | Replies | Provider timestamp delta, median [IQR], seconds | New incoming content tokens, median [IQR] |
|---|---:|---|---|
| all | 116 | 1 [1, 2] | 52 [50, 54] |
| same_round | 113 | 1 [1, 2] | 52 [50, 54] |
| next_round | 3 | 5 [4.5, 6] | 52 [45.5, 95.5] |

The timing column is a difference between provider `response.created` timestamps with one-second resolution. The harness does not record response-end and next-request-start times here. It is therefore **not a measured warning duration** or the gap available to an intervention. Token counts include only the newly appended incoming message bodies, tokenized with the same Harmony encoding; they exclude the current assistant reply and framing tokens.

## Same-round positive subset

These estimates retain all 1,758 original strict-future negative replies and the 113 same-round positives, dropping the three next-round positives. This is an outcome-conditioned descriptive subset, not a new deployable endpoint. Within-scenario × round AUROC and 1,000-family-bootstrap intervals average seeds 42/43/44.

| Split | MAX | Mean | Frozen last-prompt A |
|---|---|---|---|
| pooled | 0.891 [0.853, 0.926] | 0.979 [0.958, 0.993] | 0.520 [0.462, 0.578] |
| loso | 0.887 [0.853, 0.921] | 0.985 [0.971, 0.995] | 0.543 [0.489, 0.597] |

A separate next-round AUROC is not reported: three positive replies are too few for a reliable estimate. The result is overwhelmingly a warning one tool step ahead within a round; it does not establish warning before another peer turn. The saved models were trained on inclusive horizons, with no refit for this check. The last-prompt model has a different training label.

Script: `experiments/E05-probes/reasoning_stream_future_breakdown.py`. Source: `runs/20261026-0526-e05-reasoning-stream/probe_scores.csv` (SHA256 `6bcd3948f3f5a4562d3157007b0cb941dda938e4957ef4b9b71214218831c97b`). Audit run: `/Users/leo/collusion-research/runs/20261026-1219-e05-stream-future-breakdown`. No API/GPU spend.
