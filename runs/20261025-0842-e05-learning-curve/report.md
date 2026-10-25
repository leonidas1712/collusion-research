# Training-family learning curves

Fixed replay-2 outer test sets; eventual outcome and near-term B. At each outer split, three seeded permutations of recruiting training families define nested 25/50/75/100% subsets (rounded up). Saved inner-training/validation assignments are filtered to those families. Draws are retried only when a training or inner-validation split cannot support the original recipe; no fitted scores or outer test labels guide sampling. All selected families and retry counts are in sampling_plan.json.

Inner-selected and fixed-layer-32 logistic probes use the original fitting settings. The 100% scores reuse the saved full-data fits and are identical across subsample draws. Estimates average three seeds × three draws; 95% family-bootstrap intervals use the same test-family resamples across sizes and methods. Intervals condition on the fits, not on a new training-data experiment. Primary metric: scenario × round AUROC.

| Label | Analysis | Training fraction | Training families (min–max) | Nested AUROC [95% CI] | Fixed32 AUROC [95% CI] |
|---|---|---:|---|---|---|
| eventual | pooled | 25% | 27–27 | 0.501 [0.454, 0.548] | 0.508 [0.452, 0.564] |
| eventual | pooled | 50% | 53–54 | 0.536 [0.481, 0.584] | 0.548 [0.487, 0.609] |
| eventual | pooled | 75% | 79–81 | 0.527 [0.466, 0.591] | 0.557 [0.483, 0.628] |
| eventual | pooled | 100% | 105–108 | 0.522 [0.450, 0.591] | 0.576 [0.493, 0.650] |
| eventual | loso | 25% | 24–30 | 0.521 [0.481, 0.559] | 0.541 [0.491, 0.585] |
| eventual | loso | 50% | 48–60 | 0.537 [0.500, 0.570] | 0.552 [0.486, 0.603] |
| eventual | loso | 75% | 72–90 | 0.552 [0.507, 0.592] | 0.551 [0.473, 0.611] |
| eventual | loso | 100% | 95–119 | 0.551 [0.499, 0.597] | 0.547 [0.460, 0.612] |
| B_round_contrast | pooled | 25% | 27–27 | 0.533 [0.499, 0.568] | 0.536 [0.497, 0.574] |
| B_round_contrast | pooled | 50% | 53–54 | 0.557 [0.511, 0.607] | 0.560 [0.499, 0.617] |
| B_round_contrast | pooled | 75% | 79–81 | 0.572 [0.513, 0.628] | 0.565 [0.490, 0.629] |
| B_round_contrast | pooled | 100% | 105–108 | 0.605 [0.542, 0.663] | 0.578 [0.500, 0.653] |
| B_round_contrast | loso | 25% | 24–30 | 0.592 [0.563, 0.617] | 0.577 [0.540, 0.607] |
| B_round_contrast | loso | 50% | 48–60 | 0.602 [0.564, 0.633] | 0.588 [0.537, 0.631] |
| B_round_contrast | loso | 75% | 72–90 | 0.611 [0.570, 0.646] | 0.594 [0.532, 0.647] |
| B_round_contrast | loso | 100% | 95–119 | 0.603 [0.547, 0.649] | 0.590 [0.519, 0.657] |

## Is performance still rising at 100%?

| Label | Analysis | Method | Gain, 75% to 100% [paired family CI] |
|---|---|---|---|
| eventual | pooled | nested | -0.006 [-0.031, +0.023] |
| eventual | pooled | fixed32 | +0.018 [-0.003, +0.038] |
| eventual | loso | nested | -0.001 [-0.031, +0.030] |
| eventual | loso | fixed32 | -0.004 [-0.019, +0.010] |
| B_round_contrast | pooled | nested | +0.033 [+0.003, +0.066] |
| B_round_contrast | pooled | fixed32 | +0.013 [-0.013, +0.038] |
| B_round_contrast | loso | nested | -0.008 [-0.037, +0.019] |
| B_round_contrast | loso | fixed32 | -0.003 [-0.027, +0.019] |

A positive final increment is compatible with further gains; an interval spanning zero does not establish saturation. These curves vary training-family count on the existing test distribution and do not predict the benefit of collecting a new scenario.

The optional v1+v2 deploy-token comparison is not included: v1 uses a different episode/eligibility cache and combining it would require harmonized family splits and a separate fit. Existing v2-only results remain in the replay-2 report; they are not substituted for a matched combined-data comparison.

Sources: `20261025-0337-e05-replay2-data`, `20261025-0340-e05-replay2-fits`, `20261025-0730-e05-near-term`. Per-subset coefficients, split indices and predictions are saved for audit. No API/GPU use.
