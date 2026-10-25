# Near-term checkpoint: B_round_contrast

This variant is fully fitted; the other variants in the parent run are still in progress. No new fits. All figures use the same 1,000 family-bootstrap resamples and saved test folds as the final report.

| Analysis | Method | Scenario × round AUROC [95% CI] | Fold sensitivity [95% CI] |
|---|---|---|---|
| pooled | eventual_nested | 0.522 [0.461, 0.584] | 0.568 [0.474, 0.642] |
| pooled | eventual_fixed32 | 0.577 [0.493, 0.646] | 0.623 [0.517, 0.687] |
| pooled | nested | 0.605 [0.542, 0.663] | 0.647 [0.573, 0.701] |
| pooled | fixed32 | 0.578 [0.500, 0.653] | 0.608 [0.506, 0.680] |
| pooled | turn | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| pooled | length | 0.489 [0.420, 0.571] | 0.515 [0.443, 0.609] |
| pooled | scenario_round | 0.301 [0.237, 0.374] | 0.500 [0.500, 0.500] |
| pooled | metadata_base | 0.302 [0.236, 0.364] | 0.485 [0.391, 0.557] |
| pooled | metadata_probe | 0.535 [0.469, 0.596] | 0.644 [0.568, 0.698] |
| loso | eventual_nested | 0.576 [0.513, 0.635] | 0.576 [0.513, 0.635] |
| loso | eventual_fixed32 | 0.569 [0.484, 0.639] | 0.569 [0.484, 0.639] |
| loso | nested | 0.603 [0.547, 0.649] | 0.603 [0.547, 0.649] |
| loso | fixed32 | 0.590 [0.519, 0.657] | 0.590 [0.519, 0.657] |
| loso | turn | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| loso | length | 0.489 [0.420, 0.571] | 0.489 [0.420, 0.571] |
| loso | scenario_round | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| loso | metadata_base | 0.511 [0.429, 0.580] | 0.511 [0.429, 0.580] |
| loso | metadata_probe | 0.601 [0.545, 0.650] | 0.601 [0.545, 0.650] |
