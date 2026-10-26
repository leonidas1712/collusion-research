# Channel-only per-call sensitivity on gpt-oss-20b

This post-hoc appendix analysis keeps the same 238 recruiting episode IDs as the streaming study but expands the saved post-ask window through the first channel publication. It includes calls after an earlier file disclosure. Held episodes retain all saved post-read calls. There is no reasoning-availability filter and no new GPU replay.

The cohort has 2,632 recruiting calls and 96 first channel-publication calls; 427 calls, including 93 positives, occur after an earlier public emission. Such contexts can already contain the disclosed value in prior outputs. This is not the matched 1,995-call any-publication cohort and does not test secrecy before every public route.

The last-prompt logistic recipe, saved outer and inner partitions, 17 candidate layers, C=0.1, training-only standardisation, round weights and seeds 42/43/44 are unchanged. Layer selection maximises inner scenario × round AUROC. No new model generation or paid API calls are used.

| Split | Calls / positives | Within scenario × round AUROC [95% CI] | Channel-call catches / held-call alarms |
|---|---:|---|---|
| loso | 2632/96 | 0.943 [0.921, 0.961] | 95.1% / 13.0% |
| pooled | 2632/96 | 0.925 [0.895, 0.952] | 92.4% / 13.0% |

Intervals use 1,000 family-bootstrap draws, seed 20261025, conditional on saved fits and layer choices. Thresholds use training-side no-ask control calls, strict >, nominal 5%. Held episodes here mean no channel publication, not necessarily no earlier file disclosure. These are call-level observational catches, not intervention success rates.

This sensitivity changes both the endpoint and the call window relative to the any-publication analysis. Differences cannot be attributed solely to the outcome label. The original same-call channel check had only 3 positives and was not fitted; see runs/20261026-1333-e05-channel-percall-feasibility. Source paths, hashes and settings are in analysis_plan.json; counts.json and rows.json.gz document membership.
