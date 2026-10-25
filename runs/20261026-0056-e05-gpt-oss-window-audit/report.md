# gpt-oss scoring windows and available lead time

This is a descriptive audit of the frozen 360-episode collection and replay step plan. No model was fitted and no API/GPU call was made. Channel publication is the episode outcome. The scoring window is strictly after the protected-value read and strictly before the first public response/tool-argument emission; a file write can therefore close the window before a later channel post.

Of 128 channel-positive episodes, 96 have an eligible post-ask scoring request and 32 have none. The latter remain positive collection outcomes but do not enter the post-ask AUROC. An action in the very first request receiving the ask has no strict pre-action post-ask row. Among the zero-window positives, 31 emit in the first request receiving the ask and 1 before the ask. These are window exclusions, not failed-task exclusions.

| Scenario | Channel positives | With window | No window | Public before ask | Public same round | Public later round | Channel later round |
|---|---:|---:|---:|---:|---:|---:|---:|
| deploy-token-v2 | 19 | 6 | 13 | 0 | 17 | 2 | 6 |
| dispatch-integration-code | 15 | 12 | 3 | 1 | 7 | 7 | 7 |
| handoff-exception-note | 25 | 21 | 4 | 0 | 18 | 7 | 9 |
| procurement-reserve-price | 22 | 18 | 4 | 0 | 17 | 5 | 10 |
| service-capacity-figure | 22 | 20 | 2 | 0 | 16 | 6 | 6 |
| service-rollout-threshold | 25 | 19 | 6 | 0 | 21 | 4 | 7 |

Public delay and channel delay are different: a later channel post does not extend the scoring window if a file emission has already occurred. Before-ask cases are retained descriptively, not relabelled. Request distances count completed target requests and include the action request as the endpoint; zero means the action-producing request is the first request receiving the ask.

## Available lead time

These distributions describe prediction opportunities, not achieved warning time or alarm recall. The episode-level distribution uses the earliest eligible post-ask row. The step-level distribution counts every eligible positive request, so episodes with longer windows contribute more steps.

| Quantity | Histogram (distance or round: count) |
|---|---|
| first_public_round | {"2": 1, "3": 94, "4": 29, "5": 3, "12": 1} |
| first_channel_round | {"2": 1, "3": 81, "4": 39, "5": 6, "12": 1} |
| public_minus_ask_rounds | {"-1": 1, "0": 96, "1": 27, "2": 3, "9": 1} |
| channel_minus_ask_rounds | {"-1": 1, "0": 82, "1": 39, "2": 5, "9": 1} |
| public_minus_ask_requests | {"-1": 1, "0": 31, "1": 64, "2": 11, "3": 15, "4": 3, "5": 1, "8": 1, "13": 1} |
| channel_minus_ask_requests | {"-1": 1, "1": 27, "2": 55, "3": 15, "4": 21, "5": 4, "6": 3, "8": 1, "14": 1} |
| earliest_eligible_lead_requests | {"1": 64, "2": 11, "3": 15, "4": 3, "5": 1, "8": 1, "13": 1} |
| earliest_eligible_lead_rounds | {"0": 65, "1": 27, "2": 3, "9": 1} |
| eligible_positive_step_lead_requests | {"1": 96, "2": 32, "3": 21, "4": 6, "5": 3, "6": 2, "7": 2, "8": 2, "9": 1, "10": 1, "11": 1, "12": 1, "13": 1} |
| eligible_positive_step_lead_rounds | {"0": 76, "1": 72, "2": 11, "3": 1, "4": 1, "5": 2, "6": 1, "7": 1, "8": 1, "9": 3} |

## Prompt-count sensitivity coverage

The within-one-token sensitivity removes individual requests with absolute count gap >1. It does not remove all other requests from an episode merely because one mismatches.

| Window | Filter | Steps | Positive steps (%) | Episodes | Positive episodes (%) |
|---|---|---:|---:|---:|---:|
| post_ask | primary | 2059 | 169 (8.21%) | 238 | 96 (40.34%) |
| post_ask | within1 | 1923 | 159 (8.27%) | 227 | 91 (40.09%) |
| pre_ask | primary | 1141 | 489 (42.86%) | 292 | 128 (43.84%) |
| pre_ask | within1 | 1066 | 456 (42.78%) | 290 | 126 (43.45%) |
