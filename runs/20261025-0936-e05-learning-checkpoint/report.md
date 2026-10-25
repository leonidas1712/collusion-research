# Learning-curve checkpoint: eventual, loso

This analysis has all three seeds and three draws at every size; other analyses in the parent run are still in progress. Fixed test rows and saved inner folds; 100% scores reused. Point estimates average nine seed×draw AUROCs; intervals are conditional 95% family-bootstrap intervals (1,000 resamples). No new fits.

| Fraction | Nested AUROC [95% CI] | Fixed32 AUROC [95% CI] |
|---|---|---|
| 25% | 0.521 [0.481, 0.559] | 0.541 [0.491, 0.585] |
| 50% | 0.537 [0.500, 0.570] | 0.552 [0.486, 0.603] |
| 75% | 0.552 [0.507, 0.592] | 0.551 [0.473, 0.611] |
| 100% | 0.551 [0.499, 0.597] | 0.547 [0.460, 0.612] |

75%→100% paired increments:

- nested: -0.001 [-0.031, +0.030].
- fixed32: -0.004 [-0.019, +0.010].

An interval spanning zero does not establish saturation. Cross-fold score shifts can affect pooled-CV ranks.
