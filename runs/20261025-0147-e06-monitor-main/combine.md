# Combination test: does the probe add to a text monitor?

Stacked logistic on [round, log length, monitor] vs the same plus the probe score, fit on training folds of the probe's own outer splits, applied to the held-out fold. Within scenario x round AUROC, mean of three split seeds; paired family-bootstrap 95% CI. "Selected" picks the monitor on training rows only; "fixed" is GPT-5-nano detector L2 (named in advance); "post hoc" is Jev forecaster L3 (best after seeing results). Monitor + monitor adds GPT-5-nano detector L2 to Jev forecaster L3, as a reference for "any second view".

Stacked scores come from different fitted models per fold, so the fold-stratified gain (fold x scenario x round) is shown too; it is the cleaner number for the stacked comparisons.

| Label · analysis | Rows (pos) | Probe alone | Jev F L3 alone (stacked) | + probe | Gain [95% CI] | Gain, fold-strat. | Selected: gain [95% CI] | Fixed (GPT-5-nano det L2): gain [95% CI] | Fixed, fold-strat. | Monitor+monitor: gain [95% CI] |
|---|---|---|---|---|---|---|---|---|---|---|
| A_hazard · loso | 2910 (168) | 0.611 | 0.658 | 0.663 | +0.006 [-0.017, +0.026] | +0.006 | +0.006 [-0.017, +0.026] | +0.063 [+0.017, +0.113] | +0.063 | +0.018 [-0.004, +0.039] |
| A_hazard · pooled | 2910 (168) | 0.585 | 0.630 | 0.621 | -0.008 [-0.044, +0.030] | +0.003 | -0.008 [-0.044, +0.030] | +0.073 [+0.017, +0.132] | +0.087 | +0.012 [-0.011, +0.033] |
| B_round_contrast · loso | 2460 (168) | 0.603 | 0.675 | 0.671 | -0.004 [-0.027, +0.018] | -0.004 | -0.004 [-0.027, +0.018] | +0.051 [+0.004, +0.107] | +0.051 | +0.014 [-0.010, +0.038] |
| B_round_contrast · pooled | 2460 (168) | 0.605 | 0.652 | 0.646 | -0.007 [-0.045, +0.028] | +0.022 | -0.007 [-0.045, +0.028] | +0.080 [+0.022, +0.148] | +0.112 | +0.018 [-0.006, +0.041] |
| C_step_contrast · loso | 2478 (186) | 0.619 | 0.688 | 0.688 | -0.001 [-0.030, +0.021] | -0.001 | -0.001 [-0.030, +0.021] | +0.076 [+0.007, +0.137] | +0.076 | -0.002 [-0.015, +0.009] |
| C_step_contrast · pooled | 2478 (186) | 0.589 | 0.670 | 0.666 | -0.003 [-0.038, +0.029] | +0.007 | -0.003 [-0.038, +0.029] | +0.076 [+0.014, +0.134] | +0.088 | +0.001 [-0.010, +0.015] |
| eventual · loso | 2910 (618) | 0.551 | 0.571 | 0.572 | +0.001 [-0.014, +0.017] | +0.001 | +0.001 [-0.016, +0.019] | +0.013 [-0.008, +0.033] | +0.013 | +0.002 [-0.019, +0.023] |
| eventual · pooled | 2910 (618) | 0.522 | 0.542 | 0.550 | +0.008 [-0.045, +0.055] | +0.013 | +0.022 [-0.030, +0.068] | +0.012 [-0.042, +0.059] | +0.014 | +0.021 [-0.013, +0.055] |

Monitor chosen on training rows (counts over folds x seeds):

- A_hazard | loso: jev forecaster L3 ×18
- A_hazard | pooled: jev forecaster L3 ×15
- B_round_contrast | loso: jev forecaster L3 ×18
- B_round_contrast | pooled: jev forecaster L3 ×15
- C_step_contrast | loso: jev forecaster L3 ×18
- C_step_contrast | pooled: jev forecaster L3 ×15
- eventual | loso: jev forecaster L3 ×12, llm detector L2 ×6
- eventual | pooled: jev forecaster L3 ×10, llm detector L2 ×3, llm forecaster L2 ×2
