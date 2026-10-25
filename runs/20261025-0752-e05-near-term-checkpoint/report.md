# Near-term checkpoint: A_hazard

This variant is fully fitted; the other variants in the parent run are still in progress. No new fits. All figures use the same 1,000 family-bootstrap resamples and saved test folds as the final report.

| Analysis | Method | Scenario × round AUROC [95% CI] | Fold sensitivity [95% CI] |
|---|---|---|---|
| pooled | eventual_nested | 0.522 [0.465, 0.575] | 0.549 [0.471, 0.618] |
| pooled | eventual_fixed32 | 0.569 [0.500, 0.631] | 0.601 [0.520, 0.671] |
| pooled | nested | 0.585 [0.526, 0.641] | 0.627 [0.559, 0.685] |
| pooled | fixed32 | 0.576 [0.506, 0.641] | 0.607 [0.524, 0.674] |
| pooled | turn | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| pooled | length | 0.494 [0.435, 0.560] | 0.522 [0.461, 0.598] |
| pooled | scenario_round | 0.324 [0.273, 0.380] | 0.500 [0.500, 0.500] |
| pooled | metadata_base | 0.330 [0.275, 0.384] | 0.478 [0.402, 0.539] |
| pooled | metadata_probe | 0.531 [0.472, 0.589] | 0.628 [0.560, 0.690] |
| loso | eventual_nested | 0.569 [0.508, 0.626] | 0.569 [0.508, 0.626] |
| loso | eventual_fixed32 | 0.567 [0.491, 0.631] | 0.567 [0.491, 0.631] |
| loso | nested | 0.611 [0.560, 0.658] | 0.611 [0.560, 0.658] |
| loso | fixed32 | 0.590 [0.529, 0.643] | 0.590 [0.529, 0.643] |
| loso | turn | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| loso | length | 0.494 [0.435, 0.560] | 0.494 [0.435, 0.560] |
| loso | scenario_round | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| loso | metadata_base | 0.506 [0.440, 0.565] | 0.506 [0.440, 0.565] |
| loso | metadata_probe | 0.611 [0.559, 0.657] | 0.611 [0.559, 0.657] |
