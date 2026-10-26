# Post hoc last-prompt label ladder on gpt-oss-20b

These fits were requested after the immediate and strict-next-call ablation. They use the identical 1,995 nonempty-reasoning recruiting calls from 238 episodes, including 121 first-public-emission calls, and the same saved family/scenario partitions, 17 candidate layers, training-only scaling, round weights, C=0.1 and seeds 42/43/44. Neither model consumes generated reasoning. Round-any-public is positive when the first public emission occurs in this round or the next; eventual-any-public is positive for every retained call of an episode that eventually publishes. Both use any-publication rather than the paper’s channel-only episode outcome.

| Label / split | Rows / positives | Refit last-prompt AUROC [95% CI] | Frozen paper A AUROC [95% CI] | Paired gain [95% CI] | Held-reply alarms |
|---|---:|---|---|---|---:|
| round_any/loso | 1995/304 | 0.637 [0.586, 0.692] | 0.526 [0.477, 0.573] | +0.111 [+0.048, +0.170] | 1.8% |
| round_any/pooled | 1995/304 | 0.607 [0.553, 0.668] | 0.498 [0.434, 0.556] | +0.109 [+0.042, +0.190] | 2.4% |
| eventual_any/loso | 1995/330 | 0.610 [0.565, 0.664] | 0.516 [0.467, 0.565] | +0.094 [+0.037, +0.156] | 2.9% |
| eventual_any/pooled | 1995/330 | 0.628 [0.576, 0.682] | 0.508 [0.445, 0.563] | +0.120 [+0.059, +0.186] | 3.7% |

Metrics are within scenario × round, with 1,000 paired family bootstrap draws at seed 20261025 conditional on fitted choices. Held-reply alarms use training-side no-ask control-reply thresholds at nominal 5%, strict >; they are not episode-level intervention rates. The frozen A model is evaluated on identical rows with each new label, but was trained on its original channel-outcome near-term label. This contrast changes the training task and includes emitting calls absent from the original fitting cohort. Do not interpret differences between ladder labels as a paired effect of temporal distance alone.

The previous immediate refit on these same 1,995 rows is in runs/20261026-1221-e05-lastprompt-percall-6013. Its strict-next refit excludes own-leak calls and uses 1,874 rows, so that rung has a different cohort. Sources: runs/20261026-0522-e05-reasoning-stream-data; runs/20261025-2305-e05-gpt-oss-full-data; runs/20261026-0138-e05-gpt-oss-main. Reusable fitting code: experiments/E05-probes/lastprompt_percall.py; wrapper: experiments/E05-probes/lastprompt_label_ladder.py.
