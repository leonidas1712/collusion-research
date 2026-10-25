# Learning-curve checkpoint: eventual, pooled

This analysis has all three seeds and three draws at every size; other analyses in the parent run are still in progress. Fixed test rows and saved inner folds; 100% scores reused. Point estimates average nine seed×draw AUROCs; intervals are conditional 95% family-bootstrap intervals (1,000 resamples). No new fits.

| Fraction | Nested AUROC [95% CI] | Fixed32 AUROC [95% CI] |
|---|---|---|
| 25% | 0.501 [0.454, 0.548] | 0.508 [0.452, 0.564] |
| 50% | 0.536 [0.481, 0.584] | 0.548 [0.487, 0.609] |
| 75% | 0.527 [0.466, 0.591] | 0.557 [0.483, 0.628] |
| 100% | 0.522 [0.450, 0.591] | 0.576 [0.493, 0.650] |

75%→100% paired increments:

- nested: -0.006 [-0.031, +0.023].
- fixed32: +0.018 [-0.003, +0.038].

An interval spanning zero does not establish saturation. Cross-fold score shifts can affect pooled-CV ranks.
