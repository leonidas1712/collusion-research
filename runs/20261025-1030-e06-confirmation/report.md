# Confirmation test

Frozen plan: docs/confirmatory_plan.md. Probe and stackers trained on replay 2 only; scored once on the new episodes. Within scenario x round AUROC; family-bootstrap 95% CI over the new episodes.

| Label | Rows (pos) / episodes | Probe | Jev F L3 | GPT-5-nano det L2 | Jev − probe | Gain: probe over GPT-5-nano | Gain: probe over Jev |
|---|---|---|---|---|---|---|---|
| A_hazard (primary) | 1787 (82) / 89 | 0.681 [0.604, 0.753] | 0.644 [0.560, 0.722] | 0.532 [0.462, 0.602] | -0.038 [-0.142, +0.059] | +0.113 [+0.025, +0.203] | +0.052 [-0.014, +0.121] |
| B_round_contrast | 1489 (82) / 89 | 0.686 [0.589, 0.772] | 0.656 [0.563, 0.748] | 0.539 [0.464, 0.619] | -0.030 [-0.147, +0.097] | +0.114 [+0.001, +0.211] | +0.049 [-0.033, +0.132] |
| C_step_contrast | 1518 (111) / 89 | 0.637 [0.545, 0.726] | 0.617 [0.521, 0.712] | 0.512 [0.448, 0.579] | -0.021 [-0.127, +0.090] | +0.105 [-0.006, +0.216] | +0.022 [-0.045, +0.085] |

## Pre-stated success criteria (label A)

1. Probe CI above 0.5: PASS (0.681 [0.604, 0.753])
2. Gain over GPT-5-nano det L2 CI above 0: PASS (+0.113 [+0.025, +0.203])
3. Expected ≈0 over Jev: +0.052 [-0.014, +0.121]

## Secondary

- A_hazard: late-band probe (addendum 5) 0.664 [0.577, 0.744], minus primary probe -0.017 [-0.090, +0.057]
- A_hazard: seed-42 probe 0.639 [0.556, 0.717]; fixed layer 32 0.640 [0.545, 0.723]; chosen layers {42: 28, 43: 60, 44: 16}; jev detector L1 0.515 [0.449, 0.582]; jev detector L2 0.554 [0.496, 0.611]; jev detector L3 0.608 [0.547, 0.670]; jev forecaster L1 0.534 [0.452, 0.621]; jev forecaster L2 0.616 [0.525, 0.710]; llm forecaster L2 0.565 [0.489, 0.640]
- B_round_contrast: late-band probe (addendum 5) 0.668 [0.575, 0.754], minus primary probe -0.018 [-0.081, +0.047]
- B_round_contrast: seed-42 probe 0.626 [0.530, 0.719]; fixed layer 32 0.626 [0.530, 0.719]; chosen layers {42: 32, 43: 60, 44: 48}; jev detector L1 0.524 [0.455, 0.599]; jev detector L2 0.554 [0.495, 0.614]; jev detector L3 0.612 [0.543, 0.682]; jev forecaster L1 0.545 [0.453, 0.644]; jev forecaster L2 0.620 [0.521, 0.720]; llm forecaster L2 0.578 [0.506, 0.649]
- C_step_contrast: late-band probe (addendum 5) 0.638 [0.564, 0.715], minus primary probe +0.000 [-0.089, +0.099]
- C_step_contrast: seed-42 probe 0.584 [0.487, 0.673]; fixed layer 32 0.584 [0.487, 0.673]; chosen layers {42: 32, 43: 40, 44: 36}; jev detector L1 0.538 [0.474, 0.616]; jev detector L2 0.546 [0.492, 0.600]; jev detector L3 0.566 [0.501, 0.630]; jev forecaster L1 0.508 [0.419, 0.598]; jev forecaster L2 0.601 [0.509, 0.696]; llm forecaster L2 0.553 [0.494, 0.614]
