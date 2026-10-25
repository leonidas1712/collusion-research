# Near-term MLP versus nested logistic

Exploratory CPU-only comparison; two threads, memory-mapped activations, no paid calls or GPU. Exact saved outer and inner splits are filtered by the original near-term A/B memberships. MLP layer selection uses only inner validation over layers 0,4,…,60,63 (ties choose the lower layer). Final models refit on all outer-training rows. Both inner and final MLP seeds equal outer seed + fold, matching replay2_core.py.

Recipe unchanged: training-only StandardScaler; round-balanced weights; one 32-unit ReLU layer; AdamW learning rate .001, weight decay .01; batch size 256; 80 epochs. No tuning using test rows. Nested logistic scores are copied from the existing near-term CSV and checked against its saved fold scores.

Primary metric is scenario × round AUROC; sensitivity adds fold. Paired 95% CIs use 1000 identical family-bootstrap resamples for both methods and all three seeds, then subtract seed-averaged AUROCs. Intervals condition on fixed splits/fits. Single-class strata are omitted; coverage is in metrics.json. B uses outcome hindsight to remove earlier give-in steps; A retains those as negatives. Neither contrast is a prospective deployment estimate.

| Label | Analysis | Rows (+) | MLP primary [CI] | Logistic primary [CI] | Paired MLP − LR [CI] | Fold-stratified difference [CI] |
| --- | --- | ---: | --- | --- | --- | --- |
| B_round_contrast | pooled | 2460 (168) | 0.586 [0.520, 0.654] | 0.605 [0.542, 0.663] | -0.020 [-0.056, 0.021] | 0.009 [-0.043, 0.053] |
| B_round_contrast | loso | 2460 (168) | 0.600 [0.559, 0.637] | 0.603 [0.547, 0.649] | -0.003 [-0.040, 0.035] | -0.003 [-0.040, 0.035] |
| A_hazard | pooled | 2910 (168) | 0.586 [0.525, 0.647] | 0.585 [0.526, 0.641] | 0.001 [-0.036, 0.035] | 0.006 [-0.038, 0.061] |
| A_hazard | loso | 2910 (168) | 0.608 [0.565, 0.646] | 0.611 [0.560, 0.658] | -0.003 [-0.038, 0.029] | -0.003 [-0.038, 0.029] |

OOF export: 64440 rows, original CSV schema; methods mlp and nested. Per-fold selection.json, inner validation scores, model.npz, scores.npz and fit.json preserve selection and reconstruction evidence. metrics.json contains all metric and coverage details.

Inputs: 20261025-0337-e05-replay2-data; 20261025-0340-e05-replay2-fits (saved splits); 20261025-0730-e05-near-term (labels, filtered splits and nested logistic scores).

## Final audit

All 66 final models and 1122 candidate-layer validation records passed reconstruction/selection checks. All 64440 CSV rows match the saved fold assignments and baseline identities. Logistic primary estimates, confidence intervals and sensitivity point estimates reproduce the existing near-term report exactly. Maximum final-score reconstruction error: 9.06e-06. See audit.json.
