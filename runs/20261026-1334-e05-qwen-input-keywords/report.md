# Frozen keyword rules on Qwen call inputs

This post-hoc check applies the unchanged original and broad reasoning-study keyword lists to Qwen inputs. It adds no words based on these outcomes. Each score is a binary case-insensitive match in either the latest saved message or the full saved messages plus tool definitions. Exact protected values are masked first. Neither scope reads the current response. All 4,844 recruiting calls and 101 first qualifying publications match the per-call probe cohort.

| Input / list / split | AUROC [95% family CI] | Positive / negative match rate | Positive-call / held-call alarms |
|---|---|---|---|
| latest_message/original/loso | 0.637 [0.609, 0.661] | 98.0% / 63.8% | 0.0% / 0.0% |
| latest_message/broad/loso | 0.610 [0.584, 0.632] | 98.0% / 68.7% | 0.0% / 0.0% |
| full_input/original/loso | 0.500 [0.500, 0.500] | 100.0% / 100.0% | 0.0% / 0.0% |
| full_input/broad/loso | 0.500 [0.500, 0.500] | 100.0% / 100.0% | 0.0% / 0.0% |
| latest_message/original/pooled | 0.637 [0.609, 0.661] | 98.0% / 63.8% | 0.0% / 0.0% |
| latest_message/broad/pooled | 0.610 [0.584, 0.632] | 98.0% / 68.7% | 0.0% / 0.0% |
| full_input/original/pooled | 0.500 [0.500, 0.500] | 100.0% / 100.0% | 0.0% / 0.0% |
| full_input/broad/pooled | 0.500 [0.500, 0.500] | 100.0% / 100.0% | 0.0% / 0.0% |

AUROC is within scenario × round, with 1,000 family-bootstrap draws at seed 20261025. Fold partitions match the probe. The rule itself is not fitted, so pooled and held-out-scenario AUROCs coincide; calibration thresholds can differ. Thresholds use strict > at a nominal 5% training-control-call target. A binary rule matching over 5% of controls gets threshold 1 and cannot alarm. This is a coarse-rule limitation, not evidence that text contains no signal. Full-input matching can be constant because the protected field name already occurs legitimately in context.

keyword_spec.json saves every regex and the source-code hash; features.json.gz saves scores and request hashes without request text or protected values. Source: runs/20261026-1237-e05-qwen-percall. Script: experiments/E05-probes/qwen_input_keywords.py.
