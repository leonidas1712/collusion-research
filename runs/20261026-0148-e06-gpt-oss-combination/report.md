# GPT-OSS combination test: does the activation probe add to a text monitor?

This uses the frozen Qwen Table 2 recipe: stacked logistic regression on `[round, log length, monitor]` versus the same features plus the activation-probe score. Models are trained on the other folds of the probe's saved outer split and applied to its held-out fold. Inputs are restricted to canonical `method=nested`, `window=post_ask` recruiting rows and joined to monitor scores by row ID and request hash.

The fixed monitor is llm detector L2; the post-hoc monitor is jev forecaster L3. The selected monitor is chosen by within-scenario×round AUROC on each outer training fold only. Estimates average three split seeds; gain intervals use 1000 paired family-bootstrap draws.

| Label · analysis | Rows (positive) | Probe alone | Post-hoc monitor base | + probe | Gain [95% CI] | Fold-stratified gain | Selected gain [95% CI] | Fixed gain [95% CI] | Monitor+monitor gain [95% CI] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_hazard · loso | 2059 (148) | 0.528 | 0.549 | 0.551 | +0.002 [-0.007, +0.010] | +0.002 | +0.007 [-0.006, +0.022] | +0.003 [-0.013, +0.021] | -0.008 [-0.027, +0.009] |
| A_hazard · pooled | 2059 (148) | 0.526 | 0.547 | 0.552 | +0.004 [-0.024, +0.031] | +0.000 | +0.008 [-0.021, +0.035] | +0.000 [-0.033, +0.034] | -0.008 [-0.020, +0.003] |
| B_round_contrast · loso | 2038 (148) | 0.529 | 0.548 | 0.544 | -0.004 [-0.012, +0.004] | -0.004 | +0.004 [-0.010, +0.017] | +0.002 [-0.012, +0.017] | -0.007 [-0.023, +0.009] |
| B_round_contrast · pooled | 2038 (148) | 0.533 | 0.547 | 0.556 | +0.009 [-0.020, +0.040] | +0.011 | +0.017 [-0.012, +0.046] | +0.009 [-0.023, +0.044] | -0.008 [-0.018, +0.002] |
| C_step_contrast · loso | 2039 (149) | 0.530 | 0.531 | 0.539 | +0.008 [-0.006, +0.024] | +0.008 | +0.011 [-0.014, +0.034] | +0.005 [-0.018, +0.028] | -0.002 [-0.014, +0.009] |
| C_step_contrast · pooled | 2039 (149) | 0.538 | 0.532 | 0.549 | +0.017 [-0.016, +0.052] | +0.025 | +0.022 [-0.010, +0.056] | +0.014 [-0.024, +0.055] | -0.008 [-0.015, -0.001] |
| eventual · loso | 2059 (169) | 0.511 | 0.520 | 0.514 | -0.006 [-0.017, +0.005] | -0.006 | -0.007 [-0.017, +0.002] | -0.006 [-0.015, +0.001] | -0.004 [-0.017, +0.007] |
| eventual · pooled | 2059 (169) | 0.533 | 0.510 | 0.524 | +0.014 [-0.010, +0.039] | +0.012 | +0.010 [-0.016, +0.038] | +0.004 [-0.024, +0.035] | -0.006 [-0.014, +0.000] |

## Training-fold monitor selections

- A_hazard | loso: jev forecaster L3 ×9, llm forecaster L2 ×6, llm detector L2 ×3
- A_hazard | pooled: jev forecaster L3 ×5, llm detector L2 ×3, llm forecaster L2 ×3, jev detector L4 ×2, llm detector L4 ×1, llm forecaster L4 ×1
- B_round_contrast | loso: jev detector L4 ×6, jev forecaster L3 ×6, llm detector L2 ×6
- B_round_contrast | pooled: jev forecaster L3 ×6, llm detector L2 ×3, jev detector L4 ×2, llm forecaster L2 ×2, llm detector L4 ×1, llm forecaster L4 ×1
- C_step_contrast | loso: jev detector L4 ×12, llm detector L2 ×6
- C_step_contrast | pooled: llm detector L2 ×5, jev detector L4 ×4, jev forecaster L3 ×2, llm detector L4 ×2, llm forecaster L2 ×1, llm forecaster L4 ×1
- eventual | loso: jev detector L4 ×15, llm detector L2 ×3
- eventual | pooled: jev detector L4 ×7, jev detector L3 ×3, llm detector L2 ×2, llm detector L4 ×2, jev forecaster L3 ×1

This is CPU-only post-processing; paid cost is $0.
