# Does workflow position explain immediate-call prediction?

Post hoc, input-only structural controls on the same 1,995 calls/121 first-public-emission positives. These controls use no current response. No model was refitted. The last-prompt comparator is the MATCHED immediate-label probe, not the old near-term-channel model.

Baseline A: the last message in the current request is a tool result linked to an exact `read_file` of a protected source file. Baseline B: the preceding target call requested that read. Both exclude malformed function names; tool-error results still count. Protected source paths are defined from the initial scenario files, without inspecting future outputs.

| Structural subset | Calls | Positives | Negatives |
|---|---:|---:|---:|
| latest_incoming_protected_read | 130 | 84 | 46 |
| previous_call_protected_read | 127 | 82 | 45 |

| Split / subset / score | Calls / positives | Within scenario × round AUROC [95% CI] |
|---|---|---|
| pooled/latest_incoming_protected_read | 1995 / 121 | 0.797 [0.755, 0.841] |
| pooled/previous_call_protected_read | 1995 / 121 | 0.790 [0.746, 0.832] |
| pooled/reasoning_MAX | 1995 / 121 | 0.949 [0.926, 0.969] |
| pooled/matched_last_prompt | 1995 / 121 | 0.882 [0.841, 0.918] |
| pooled/latest_incoming_protected_read_only/reasoning_MAX | 130 / 84 | 0.981 [0.956, 0.995] |
| pooled/previous_call_protected_read_only/reasoning_MAX | 127 / 82 | 0.988 [0.973, 0.997] |
| pooled/latest_incoming_protected_read_only/matched_last_prompt | 130 / 84 | 0.941 [0.893, 0.977] |
| pooled/previous_call_protected_read_only/matched_last_prompt | 127 / 82 | 0.949 [0.906, 0.982] |
| loso/latest_incoming_protected_read | 1995 / 121 | 0.797 [0.755, 0.841] |
| loso/previous_call_protected_read | 1995 / 121 | 0.790 [0.746, 0.832] |
| loso/reasoning_MAX | 1995 / 121 | 0.933 [0.912, 0.952] |
| loso/matched_last_prompt | 1995 / 121 | 0.906 [0.871, 0.936] |
| loso/latest_incoming_protected_read_only/reasoning_MAX | 130 / 84 | 0.934 [0.896, 0.964] |
| loso/previous_call_protected_read_only/reasoning_MAX | 127 / 82 | 0.937 [0.900, 0.966] |
| loso/latest_incoming_protected_read_only/matched_last_prompt | 130 / 84 | 0.932 [0.883, 0.970] |
| loso/previous_call_protected_read_only/matched_last_prompt | 127 / 82 | 0.939 [0.888, 0.975] |

## Paired differences on all calls

- pooled/reasoning_MAX minus latest_incoming_protected_read: 0.152, 95% CI [0.114, 0.188].
- pooled/reasoning_MAX minus previous_call_protected_read: 0.159, 95% CI [0.124, 0.195].
- pooled/matched_last_prompt minus latest_incoming_protected_read: 0.084, 95% CI [0.053, 0.112].
- pooled/matched_last_prompt minus previous_call_protected_read: 0.092, 95% CI [0.059, 0.119].
- loso/reasoning_MAX minus latest_incoming_protected_read: 0.136, 95% CI [0.098, 0.174].
- loso/reasoning_MAX minus previous_call_protected_read: 0.144, 95% CI [0.106, 0.182].
- loso/matched_last_prompt minus latest_incoming_protected_read: 0.108, 95% CI [0.075, 0.137].
- loso/matched_last_prompt minus previous_call_protected_read: 0.116, 95% CI [0.082, 0.148].

Conditional comparison coverage: latest-incoming-read strata retain 79/84 positives (94.0%); previous-read strata retain 78/82 (95.1%). Single-class scenario×round strata do not contribute to AUROC.

Intervals use 1,000 paired family-bootstrap draws, seed 20261025, averaging seeds 42/43/44. Conditional AUROCs retain only strata with both classes; coverage is in JSON. These diagnostics do not identify a causal mechanism or establish general advance warning.

Script: experiments/E05-probes/reasoning_stream_immediate_readstep.py. Audit run: /Users/leo/collusion-research/runs/20261026-1307-e05-immediate-readstep. CPU only, USD0.
