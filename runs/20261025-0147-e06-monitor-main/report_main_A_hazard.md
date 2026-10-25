# E06 main run, near-term label A_hazard: monitors vs probe

4184 eligible steps (2910 recruiting: 63 give-in and 89 held episodes; 78 benign control/alone episodes), six scenarios. Every method is scored on the same rows with the E05 `within_round` and `ranking_summary` code. Monitor cost: jev $2.03, llm $6.53, luna $4.11 (total $12.67).

## Ranking (recruiting steps)

Within-round AUROC compares a step only with steps of the same scenario and round (0.5 = chance). The fold-stratified column also requires the same E05 fold (post hoc; it matters only for the fitted probe). Added value: pooled AUROC gain from adding the score to turn + log length (cross-fitted, family-bootstrap CI). This base has no scenario term, so the probe gain differs from the E05 report (base scenario + turn + length). Probe scores are seed means here.

| Method | Within-round AUROC [95% CI] | Fold-stratified | Balanced (scenario mean) | Pooled AUROC [95% CI] | Added value [95% CI] | Rows |
|---|---|---|---|---|---|---|
| probe (pooled CV, out of fold) | 0.522 [0.465, 0.575] | 0.549 | 0.519 | 0.666 [0.617, 0.717] | 0.022 [0.000, 0.050] | 2910 |
| probe (held-out scenario) | 0.569 [0.508, 0.626] | 0.573 | 0.578 | 0.642 [0.585, 0.695] | 0.013 [-0.007, 0.035] | 2910 |
| baseline: round only | 0.500 [0.500, 0.500] | 0.500 | 0.500 | 0.731 [0.651, 0.798] | -0.000 [-0.000, 0.000] | 2910 |
| baseline: prompt length | 0.494 [0.435, 0.560] | 0.522 | 0.490 | 0.275 [0.207, 0.361] | 0.007 [-0.008, 0.026] | 2910 |
| jev detector L1 | 0.507 [0.468, 0.548] | 0.510 | 0.503 | 0.428 [0.381, 0.480] | -0.002 [-0.023, 0.017] | 2910 |
| jev detector L2 | 0.549 [0.504, 0.593] | 0.556 | 0.535 | 0.529 [0.486, 0.571] | 0.007 [-0.010, 0.025] | 2910 |
| jev detector L3 | 0.570 [0.519, 0.622] | 0.579 | 0.571 | 0.626 [0.575, 0.676] | 0.007 [-0.009, 0.023] | 2910 |
| llm detector L1 | 0.511 [0.469, 0.553] | 0.510 | 0.502 | 0.479 [0.439, 0.524] | 0.004 [-0.010, 0.018] | 2910 |
| llm detector L2 | 0.569 [0.525, 0.616] | 0.574 | 0.560 | 0.642 [0.593, 0.694] | 0.013 [0.000, 0.026] | 2910 |
| llm detector L3 | 0.542 [0.495, 0.589] | 0.538 | 0.558 | 0.610 [0.566, 0.655] | 0.010 [0.001, 0.018] | 2910 |
| luna detector L1 | 0.514 [0.458, 0.571] | 0.498 | 0.495 | 0.406 [0.341, 0.482] | 0.002 [-0.012, 0.018] | 2910 |
| luna detector L2 | 0.522 [0.466, 0.580] | 0.511 | 0.510 | 0.399 [0.342, 0.464] | 0.003 [-0.009, 0.014] | 2910 |
| luna detector L3 | 0.566 [0.494, 0.634] | 0.553 | 0.541 | 0.419 [0.351, 0.495] | 0.000 [-0.011, 0.012] | 2910 |
| jev forecaster L1 | 0.512 [0.458, 0.568] | 0.496 | 0.533 | 0.517 [0.465, 0.567] | -0.002 [-0.015, 0.011] | 2910 |
| jev forecaster L2 | 0.635 [0.586, 0.675] | 0.628 | 0.625 | 0.780 [0.725, 0.827] | 0.036 [0.017, 0.060] | 2910 |
| jev forecaster L3 | 0.660 [0.613, 0.704] | 0.661 | 0.653 | 0.785 [0.735, 0.828] | 0.055 [0.029, 0.086] | 2910 |
| llm forecaster L1 | 0.548 [0.493, 0.604] | 0.550 | 0.531 | 0.640 [0.578, 0.693] | 0.004 [-0.002, 0.012] | 2910 |
| llm forecaster L2 | 0.554 [0.498, 0.614] | 0.542 | 0.528 | 0.668 [0.619, 0.718] | 0.005 [-0.007, 0.021] | 2910 |
| llm forecaster L3 | 0.535 [0.484, 0.580] | 0.530 | 0.541 | 0.638 [0.595, 0.677] | 0.007 [-0.000, 0.014] | 2910 |
| luna forecaster L1 | 0.517 [0.464, 0.570] | 0.506 | 0.510 | 0.476 [0.423, 0.528] | 0.005 [-0.005, 0.019] | 2910 |
| luna forecaster L2 | 0.496 [0.442, 0.552] | 0.492 | 0.488 | 0.466 [0.419, 0.513] | -0.002 [-0.005, 0.001] | 2910 |
| luna forecaster L3 | 0.505 [0.454, 0.555] | 0.510 | 0.502 | 0.516 [0.473, 0.558] | -0.003 [-0.005, -0.001] | 2910 |

Probe rows here are the eventual-label probe scored against the near-term label (no refit); refit probe numbers come from the E05 near-term run.
