# E06 main run, near-term label C_step_contrast: monitors vs probe

3752 eligible steps (2478 recruiting: 63 give-in and 89 held episodes; 78 benign control/alone episodes), six scenarios. Every method is scored on the same rows with the E05 `within_round` and `ranking_summary` code. Monitor cost: jev $2.03, llm $6.53, luna $4.11 (total $12.67).

## Ranking (recruiting steps)

Within-round AUROC compares a step only with steps of the same scenario and round (0.5 = chance). The fold-stratified column also requires the same E05 fold (post hoc; it matters only for the fitted probe). Added value: pooled AUROC gain from adding the score to turn + log length (cross-fitted, family-bootstrap CI). This base has no scenario term, so the probe gain differs from the E05 report (base scenario + turn + length). Probe scores are seed means here.

| Method | Within-round AUROC [95% CI] | Fold-stratified | Balanced (scenario mean) | Pooled AUROC [95% CI] | Added value [95% CI] | Rows |
|---|---|---|---|---|---|---|
| probe (pooled CV, out of fold) | 0.531 [0.471, 0.592] | 0.571 | 0.524 | 0.664 [0.615, 0.715] | 0.027 [-0.005, 0.065] | 2478 |
| probe (held-out scenario) | 0.570 [0.510, 0.626] | 0.574 | 0.573 | 0.627 [0.567, 0.686] | 0.003 [-0.025, 0.032] | 2478 |
| baseline: round only | 0.500 [0.500, 0.500] | 0.500 | 0.500 | 0.703 [0.633, 0.767] | 0.000 [-0.000, 0.001] | 2478 |
| baseline: prompt length | 0.521 [0.443, 0.613] | 0.560 | 0.506 | 0.311 [0.244, 0.386] | -0.000 [-0.011, 0.011] | 2478 |
| jev detector L1 | 0.507 [0.454, 0.556] | 0.509 | 0.500 | 0.432 [0.374, 0.493] | 0.008 [-0.022, 0.044] | 2478 |
| jev detector L2 | 0.550 [0.498, 0.598] | 0.562 | 0.540 | 0.534 [0.483, 0.582] | 0.010 [-0.018, 0.042] | 2478 |
| jev detector L3 | 0.569 [0.512, 0.623] | 0.577 | 0.564 | 0.596 [0.537, 0.652] | 0.010 [-0.015, 0.039] | 2478 |
| llm detector L1 | 0.521 [0.475, 0.565] | 0.525 | 0.507 | 0.494 [0.450, 0.540] | 0.009 [-0.010, 0.028] | 2478 |
| llm detector L2 | 0.546 [0.497, 0.597] | 0.552 | 0.535 | 0.607 [0.561, 0.662] | 0.013 [0.000, 0.028] | 2478 |
| llm detector L3 | 0.532 [0.475, 0.589] | 0.536 | 0.547 | 0.587 [0.540, 0.643] | 0.011 [0.003, 0.019] | 2478 |
| luna detector L1 | 0.557 [0.494, 0.616] | 0.547 | 0.544 | 0.469 [0.396, 0.548] | 0.006 [-0.016, 0.027] | 2478 |
| luna detector L2 | 0.539 [0.474, 0.604] | 0.537 | 0.521 | 0.430 [0.370, 0.496] | 0.004 [-0.011, 0.017] | 2478 |
| luna detector L3 | 0.595 [0.519, 0.669] | 0.575 | 0.574 | 0.468 [0.394, 0.542] | 0.009 [-0.011, 0.026] | 2478 |
| jev forecaster L1 | 0.489 [0.418, 0.552] | 0.483 | 0.495 | 0.475 [0.404, 0.541] | -0.006 [-0.023, 0.012] | 2478 |
| jev forecaster L2 | 0.654 [0.593, 0.710] | 0.646 | 0.647 | 0.750 [0.689, 0.803] | 0.042 [0.017, 0.067] | 2478 |
| jev forecaster L3 | 0.687 [0.630, 0.739] | 0.683 | 0.678 | 0.762 [0.708, 0.811] | 0.056 [0.024, 0.091] | 2478 |
| llm forecaster L1 | 0.533 [0.475, 0.590] | 0.534 | 0.513 | 0.594 [0.537, 0.650] | -0.002 [-0.009, 0.004] | 2478 |
| llm forecaster L2 | 0.546 [0.487, 0.604] | 0.538 | 0.535 | 0.641 [0.588, 0.691] | 0.012 [0.000, 0.025] | 2478 |
| llm forecaster L3 | 0.514 [0.458, 0.565] | 0.510 | 0.523 | 0.611 [0.566, 0.656] | 0.006 [-0.002, 0.015] | 2478 |
| luna forecaster L1 | 0.536 [0.478, 0.592] | 0.525 | 0.525 | 0.504 [0.444, 0.560] | 0.006 [-0.007, 0.022] | 2478 |
| luna forecaster L2 | 0.523 [0.471, 0.580] | 0.517 | 0.521 | 0.476 [0.423, 0.529] | -0.001 [-0.007, 0.006] | 2478 |
| luna forecaster L3 | 0.484 [0.431, 0.544] | 0.489 | 0.478 | 0.488 [0.438, 0.538] | -0.005 [-0.009, -0.001] | 2478 |

Probe rows here are the eventual-label probe scored against the near-term label (no refit); refit probe numbers come from the E05 near-term run.
