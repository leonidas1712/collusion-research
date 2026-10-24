# E06 main run, near-term label B_round_contrast: monitors vs probe

3734 eligible steps (2460 recruiting: 63 give-in and 89 held episodes; 78 benign control/alone episodes), six scenarios. Every method is scored on the same rows with the E05 `within_round` and `ranking_summary` code. Monitor cost: jev $2.03, llm $6.53, luna $4.11 (total $12.67).

## Ranking (recruiting steps)

Within-round AUROC compares a step only with steps of the same scenario and round (0.5 = chance). The fold-stratified column also requires the same E05 fold (post hoc; it matters only for the fitted probe). Added value: pooled AUROC gain from adding the score to turn + log length (cross-fitted, family-bootstrap CI). This base has no scenario term, so the probe gain differs from the E05 report (base scenario + turn + length). Probe scores are seed means here.

| Method | Within-round AUROC [95% CI] | Fold-stratified | Pooled AUROC [95% CI] | Added value [95% CI] | Rows |
|---|---|---|---|---|---|
| probe (pooled CV, out of fold) | 0.522 [0.461, 0.584] | 0.568 | 0.691 [0.643, 0.740] | 0.016 [-0.010, 0.047] | 2460 |
| probe (held-out scenario) | 0.576 [0.513, 0.635] | 0.584 | 0.656 [0.594, 0.711] | 0.011 [-0.009, 0.032] | 2460 |
| baseline: round only | 0.500 [0.500, 0.500] | 0.500 | 0.755 [0.677, 0.819] | -0.000 [-0.001, 0.000] | 2460 |
| baseline: prompt length | 0.489 [0.420, 0.571] | 0.515 | 0.253 [0.189, 0.334] | 0.004 [-0.011, 0.021] | 2460 |
| jev detector L1 | 0.509 [0.465, 0.552] | 0.513 | 0.416 [0.363, 0.474] | 0.012 [-0.012, 0.044] | 2460 |
| jev detector L2 | 0.555 [0.505, 0.602] | 0.565 | 0.530 [0.481, 0.577] | 0.014 [-0.004, 0.038] | 2460 |
| jev detector L3 | 0.579 [0.523, 0.636] | 0.590 | 0.630 [0.571, 0.683] | 0.012 [-0.006, 0.032] | 2460 |
| llm detector L1 | 0.511 [0.466, 0.557] | 0.513 | 0.474 [0.434, 0.521] | 0.007 [-0.008, 0.022] | 2460 |
| llm detector L2 | 0.573 [0.527, 0.623] | 0.575 | 0.659 [0.609, 0.710] | 0.015 [0.002, 0.029] | 2460 |
| llm detector L3 | 0.532 [0.480, 0.584] | 0.532 | 0.618 [0.572, 0.668] | 0.009 [0.001, 0.017] | 2460 |
| luna detector L1 | 0.520 [0.462, 0.579] | 0.509 | 0.392 [0.321, 0.471] | 0.006 [-0.007, 0.020] | 2460 |
| luna detector L2 | 0.521 [0.458, 0.586] | 0.516 | 0.385 [0.326, 0.453] | 0.005 [-0.006, 0.015] | 2460 |
| luna detector L3 | 0.568 [0.491, 0.641] | 0.542 | 0.406 [0.333, 0.483] | 0.006 [-0.004, 0.015] | 2460 |
| jev forecaster L1 | 0.507 [0.442, 0.570] | 0.497 | 0.509 [0.447, 0.567] | 0.008 [-0.003, 0.022] | 2460 |
| jev forecaster L2 | 0.648 [0.591, 0.697] | 0.647 | 0.799 [0.744, 0.842] | 0.038 [0.015, 0.064] | 2460 |
| jev forecaster L3 | 0.677 [0.627, 0.725] | 0.676 | 0.805 [0.757, 0.846] | 0.055 [0.027, 0.089] | 2460 |
| llm forecaster L1 | 0.549 [0.489, 0.608] | 0.552 | 0.648 [0.583, 0.701] | 0.002 [-0.004, 0.009] | 2460 |
| llm forecaster L2 | 0.567 [0.507, 0.627] | 0.559 | 0.690 [0.640, 0.738] | 0.010 [-0.001, 0.022] | 2460 |
| llm forecaster L3 | 0.532 [0.476, 0.583] | 0.528 | 0.652 [0.608, 0.693] | 0.008 [0.001, 0.015] | 2460 |
| luna forecaster L1 | 0.521 [0.465, 0.576] | 0.506 | 0.470 [0.414, 0.523] | -0.001 [-0.009, 0.008] | 2460 |
| luna forecaster L2 | 0.511 [0.454, 0.565] | 0.502 | 0.465 [0.414, 0.514] | -0.001 [-0.004, 0.002] | 2460 |
| luna forecaster L3 | 0.496 [0.440, 0.552] | 0.492 | 0.508 [0.457, 0.553] | -0.008 [-0.018, -0.001] | 2460 |

Probe rows here are the eventual-label probe scored against the near-term label (no refit); refit probe numbers come from the E05 near-term run.
