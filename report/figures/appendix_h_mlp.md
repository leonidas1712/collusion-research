**MLP sensitivity: first data batch only**

First data batch only, not the all-data cohort. A one-hidden-layer MLP (32 ReLU units, 80 epochs) and logistic probe each select layers on inner validation using the same saved splits. Scenario × round AUROC, three-seed mean; paired differences and intervals use the same 1,000 family resamples. No C-label MLP result is available.

| Label | Split | Steps / + | MLP | Logistic | Paired MLP − logistic |
|---|---|---|---|---|---|
| B: round contrast | POOLED | 2460 / 168 | 0.586 [0.520, 0.654] | 0.605 [0.542, 0.663] | -0.020 [-0.056, +0.021] |
| B: round contrast | LOSO | 2460 / 168 | 0.600 [0.559, 0.637] | 0.603 [0.547, 0.649] | -0.003 [-0.040, +0.035] |
| A: current/next round | POOLED | 2910 / 168 | 0.586 [0.525, 0.647] | 0.585 [0.526, 0.641] | +0.001 [-0.036, +0.035] |
| A: current/next round | LOSO | 2910 / 168 | 0.608 [0.565, 0.646] | 0.611 [0.560, 0.658] | -0.003 [-0.038, +0.029] |
