# Learning-curve checkpoint: B_round_contrast, pooled

This analysis has all three seeds and three draws at every size; other analyses in the parent run are still in progress. Fixed test rows and saved inner folds; 100% scores reused. Point estimates average nine seed×draw AUROCs; intervals are conditional 95% family-bootstrap intervals (1,000 resamples). No new fits.

| Fraction | Nested AUROC [95% CI] | Fixed32 AUROC [95% CI] |
|---|---|---|
| 25% | 0.533 [0.499, 0.568] | 0.536 [0.497, 0.574] |
| 50% | 0.557 [0.511, 0.607] | 0.560 [0.499, 0.617] |
| 75% | 0.572 [0.513, 0.628] | 0.565 [0.490, 0.629] |
| 100% | 0.605 [0.542, 0.663] | 0.578 [0.500, 0.653] |

75%→100% paired increments:

- nested: +0.033 [+0.003, +0.066].
- fixed32: +0.013 [-0.013, +0.038].

An interval spanning zero does not establish saturation. Cross-fold score shifts can affect pooled-CV ranks.
