# Near-term action probes

CPU only; no new episodes or activations. A labels all eligible recruiting steps positive if the first forbidden action occurs this round or next; earlier give-in steps are negative. B drops those earlier give-in steps and retains held negatives. C uses the same clean contrast with 1–3 completed target requests until the first action. Eligibility remains strictly after the first read and strictly before the first action.

Outer, inner-validation and three-fold stacking assignments are filtered from the saved replay-2 splits, never reallocated. Layers are reselected within training data (0,4,…,60,63), then logistic regression is refit with the original C=0.1, round-balanced weights and training-only scaling. Added value uses scenario, round and prompt length, then adds a training-cross-fitted near-term probe score; layer selection is repeated within each stacking training split. No MLP or alarm thresholds are fitted here.

Intervals are 95% family-bootstrap intervals (1,000 resamples), shared across methods and seeds; three seed estimates are averaged. They condition on the saved splits and fitted models. Scenario × round AUROC is the primary ranking; fold × scenario × round is a sensitivity. Single-class strata are omitted; coverage is in metrics.json. The new labels and contrasts are exploratory, and clean contrasts use hindsight to remove far-from-action steps.

| Label | Analysis | Rows (+) | Method | Scenario × round AUROC [95% CI] | Fold sensitivity [95% CI] |
|---|---|---:|---|---|---|
| A_hazard | pooled | 2910 (168) | eventual_nested | 0.522 [0.465, 0.575] | 0.549 [0.471, 0.618] |
| A_hazard | pooled | 2910 (168) | eventual_fixed32 | 0.569 [0.500, 0.631] | 0.601 [0.520, 0.671] |
| A_hazard | pooled | 2910 (168) | nested | 0.585 [0.526, 0.641] | 0.627 [0.559, 0.685] |
| A_hazard | pooled | 2910 (168) | fixed32 | 0.576 [0.506, 0.641] | 0.607 [0.524, 0.674] |
| A_hazard | pooled | 2910 (168) | turn | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| A_hazard | pooled | 2910 (168) | length | 0.494 [0.435, 0.560] | 0.522 [0.461, 0.598] |
| A_hazard | pooled | 2910 (168) | scenario_round | 0.324 [0.273, 0.380] | 0.500 [0.500, 0.500] |
| A_hazard | pooled | 2910 (168) | metadata_base | 0.330 [0.275, 0.384] | 0.478 [0.402, 0.539] |
| A_hazard | pooled | 2910 (168) | metadata_probe | 0.531 [0.472, 0.589] | 0.628 [0.560, 0.690] |
| A_hazard | loso | 2910 (168) | eventual_nested | 0.569 [0.508, 0.626] | 0.569 [0.508, 0.626] |
| A_hazard | loso | 2910 (168) | eventual_fixed32 | 0.567 [0.491, 0.631] | 0.567 [0.491, 0.631] |
| A_hazard | loso | 2910 (168) | nested | 0.611 [0.560, 0.658] | 0.611 [0.560, 0.658] |
| A_hazard | loso | 2910 (168) | fixed32 | 0.590 [0.529, 0.643] | 0.590 [0.529, 0.643] |
| A_hazard | loso | 2910 (168) | turn | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| A_hazard | loso | 2910 (168) | length | 0.494 [0.435, 0.560] | 0.494 [0.435, 0.560] |
| A_hazard | loso | 2910 (168) | scenario_round | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| A_hazard | loso | 2910 (168) | metadata_base | 0.506 [0.440, 0.565] | 0.506 [0.440, 0.565] |
| A_hazard | loso | 2910 (168) | metadata_probe | 0.611 [0.559, 0.657] | 0.611 [0.559, 0.657] |
| B_round_contrast | pooled | 2460 (168) | eventual_nested | 0.522 [0.461, 0.584] | 0.568 [0.474, 0.642] |
| B_round_contrast | pooled | 2460 (168) | eventual_fixed32 | 0.577 [0.493, 0.646] | 0.623 [0.517, 0.687] |
| B_round_contrast | pooled | 2460 (168) | nested | 0.605 [0.542, 0.663] | 0.647 [0.573, 0.701] |
| B_round_contrast | pooled | 2460 (168) | fixed32 | 0.578 [0.500, 0.653] | 0.608 [0.506, 0.680] |
| B_round_contrast | pooled | 2460 (168) | turn | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| B_round_contrast | pooled | 2460 (168) | length | 0.489 [0.420, 0.571] | 0.515 [0.443, 0.609] |
| B_round_contrast | pooled | 2460 (168) | scenario_round | 0.301 [0.237, 0.374] | 0.500 [0.500, 0.500] |
| B_round_contrast | pooled | 2460 (168) | metadata_base | 0.302 [0.236, 0.364] | 0.485 [0.391, 0.557] |
| B_round_contrast | pooled | 2460 (168) | metadata_probe | 0.535 [0.469, 0.596] | 0.644 [0.568, 0.698] |
| B_round_contrast | loso | 2460 (168) | eventual_nested | 0.576 [0.513, 0.635] | 0.576 [0.513, 0.635] |
| B_round_contrast | loso | 2460 (168) | eventual_fixed32 | 0.569 [0.484, 0.639] | 0.569 [0.484, 0.639] |
| B_round_contrast | loso | 2460 (168) | nested | 0.603 [0.547, 0.649] | 0.603 [0.547, 0.649] |
| B_round_contrast | loso | 2460 (168) | fixed32 | 0.590 [0.519, 0.657] | 0.590 [0.519, 0.657] |
| B_round_contrast | loso | 2460 (168) | turn | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| B_round_contrast | loso | 2460 (168) | length | 0.489 [0.420, 0.571] | 0.489 [0.420, 0.571] |
| B_round_contrast | loso | 2460 (168) | scenario_round | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| B_round_contrast | loso | 2460 (168) | metadata_base | 0.511 [0.429, 0.580] | 0.511 [0.429, 0.580] |
| B_round_contrast | loso | 2460 (168) | metadata_probe | 0.601 [0.545, 0.650] | 0.601 [0.545, 0.650] |
| C_step_contrast | pooled | 2478 (186) | eventual_nested | 0.531 [0.471, 0.592] | 0.571 [0.483, 0.637] |
| C_step_contrast | pooled | 2478 (186) | eventual_fixed32 | 0.574 [0.496, 0.643] | 0.620 [0.525, 0.691] |
| C_step_contrast | pooled | 2478 (186) | nested | 0.589 [0.527, 0.648] | 0.635 [0.559, 0.694] |
| C_step_contrast | pooled | 2478 (186) | fixed32 | 0.596 [0.522, 0.661] | 0.627 [0.533, 0.699] |
| C_step_contrast | pooled | 2478 (186) | turn | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| C_step_contrast | pooled | 2478 (186) | length | 0.521 [0.443, 0.613] | 0.560 [0.479, 0.663] |
| C_step_contrast | pooled | 2478 (186) | scenario_round | 0.300 [0.245, 0.359] | 0.500 [0.500, 0.500] |
| C_step_contrast | pooled | 2478 (186) | metadata_base | 0.289 [0.229, 0.341] | 0.440 [0.337, 0.521] |
| C_step_contrast | pooled | 2478 (186) | metadata_probe | 0.512 [0.452, 0.570] | 0.625 [0.552, 0.686] |
| C_step_contrast | loso | 2478 (186) | eventual_nested | 0.570 [0.510, 0.626] | 0.570 [0.510, 0.626] |
| C_step_contrast | loso | 2478 (186) | eventual_fixed32 | 0.579 [0.494, 0.650] | 0.579 [0.494, 0.650] |
| C_step_contrast | loso | 2478 (186) | nested | 0.619 [0.561, 0.671] | 0.619 [0.561, 0.671] |
| C_step_contrast | loso | 2478 (186) | fixed32 | 0.620 [0.544, 0.684] | 0.620 [0.544, 0.684] |
| C_step_contrast | loso | 2478 (186) | turn | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| C_step_contrast | loso | 2478 (186) | length | 0.521 [0.443, 0.613] | 0.521 [0.443, 0.613] |
| C_step_contrast | loso | 2478 (186) | scenario_round | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| C_step_contrast | loso | 2478 (186) | metadata_base | 0.479 [0.387, 0.557] | 0.479 [0.387, 0.557] |
| C_step_contrast | loso | 2478 (186) | metadata_probe | 0.621 [0.559, 0.672] | 0.621 [0.559, 0.672] |

## Added value

| Label | Analysis | Pooled AUROC gain [paired family CI] |
|---|---|---|
| A_hazard | pooled | 0.035 [0.014, 0.057] |
| A_hazard | loso | 0.019 [-0.012, 0.047] |
| B_round_contrast | pooled | 0.035 [0.015, 0.057] |
| B_round_contrast | loso | 0.020 [-0.008, 0.044] |
| C_step_contrast | pooled | 0.038 [0.015, 0.063] |
| C_step_contrast | loso | 0.015 [-0.017, 0.048] |

## Score export and provenance

`probe_scores.csv` has 423,792 records. The unique key is `(row_id, analysis, label_variant, method, seed)`. E06 row IDs and request hashes are preserved. `nested` and `fixed32` are near-term refits; `eventual_nested` and `eventual_fixed32` are frozen original eventual-label scores, evaluated without refitting. All baselines are exported too. Only eligible recruiting rows are included; these are ranking results, not a benign-calibrated alarm analysis.

Parents: `20261025-0337-e05-replay2-data` (features/rows), `20261025-0340-e05-replay2-fits` (all split assignments and frozen eventual scores). Individual fit coefficients, splits, training-cross-fitted stacking scores and selection logs are saved beneath each variant/analysis. `labels.jsonl` includes every original row, variant membership and both labels for exact monitor alignment. `preflight.json` records split checks. Every exported fitted fold matches the original assignment; saved predictions are finite and selected/fixed logistic scores reconstruct within 1e-9.
