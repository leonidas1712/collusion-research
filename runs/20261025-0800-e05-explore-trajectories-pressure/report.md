# Exploratory trajectory and pressure probes

The difference-vector probes are near chance for eventual outcome: pooled AUROCs 0.495–0.502 and LOSO 0.505–0.506. There is modest exploratory near-term signal at layer 24: scalar features give pooled 0.556 [0.508, 0.603] and LOSO 0.561 [0.515, 0.610]; the difference vector gives pooled 0.530 [0.486, 0.572] and LOSO 0.576 [0.537, 0.615]. These are unadjusted intervals across multiple analyses, not a selected confirmatory result.

The condition classifier separates recruiting from benign almost perfectly: pooled scenario-stratified AUROC 1.000000 [1, 1], LOSO 0.999975 [0.999897, 1]. The same score does not positively rank give-ins within recruiting episodes: eventual 0.430 [0.373, 0.492] pooled and 0.426 [0.371, 0.488] LOSO; A is 0.436 [0.368, 0.510] pooled and 0.437 [0.371, 0.510] LOSO. Detecting the recruiting condition therefore does not establish a positive outcome predictor. No score sign was reversed.

All primary metrics have 100% positive coverage. Pooled fold-stratified coverage is 97.0–100% for A, and 79.1–86.3% for condition classification; exact per-seed coverage is in metrics.json. LOSO uses the same scenario/family assignment at each seed and deterministic fits give identical scores, so those seeds are not independent replications. In LOSO, fold is determined by scenario, making the extra fold stratum redundant.

CPU-only; $0 paid compute/API; sequential fits with two-thread numerical libraries. Input features.npy was opened with mmap_mode=r. These are exploratory, fixed-layer analyses, without selecting a winning layer or method on the reported outcomes.

Trajectory features at each of layers 24/32/40: current minus immediately preceding available request activation from the same episode; scalar vector = [L2 of that difference, L2 distance from the first post-read activation, 1−cosine(current, previous)]. First post-read means token_in_context and ordinal > first_read. That first post-read step uses itself as anchor (distance zero); its previous step can be pre-read. No future step or disclosure-time alignment enters feature extraction. Only original eligible current rows enter fitting/scoring.

Logistic recipe: original E05 fit_logistic, C=0.1, lbfgs, round-balanced training weights and training-only standardization; no layer selection. Outcome fits use recruiting training rows, with the original eventual label or supplied A_hazard label (disclosure in the current or next round, before action). Pressure fits use layer32 absolute activations and recruiting=1 vs control/alone=0, trained on the outer-training recruiting plus benign-calibration rows; no test families and no threshold calibration. The same pressure scores are evaluated against eventual and A labels only among recruiting test steps, without refitting or reversing their sign.

Exact 15 pooled split records are reused from the exported folds.json. Exact 18 LOSO saved split files are reused (six scenario rotations × three seeds, shared test families purged). Rows/hashes match the export. A membership filters those assignments; no splitting is redone.

Primary metric: E05 metrics.within_round with scenario stratum, averaged across seeds42/43/44. Sensitivity: fold × scenario × round within each seed, then average. CIs use 1000 shared family-bootstrap resamples, conditional on fixed fits/splits. Single-class strata are omitted; positive coverage, per-seed values and valid bootstrap counts are in metrics.json. Sensitivity may compare a different subset of positive rows. No multiplicity correction or confirmatory claims.

| Analysis | Label evaluated | Probe | Rows (+) | Scenario × round AUROC [95% CI] | Fold × scenario × round [95% CI] |
| --- | --- | --- | ---: | --- | --- |
| pooled | eventual | delta_l24 | 2910 (618) | 0.495 [0.473, 0.515] | 0.518 [0.490, 0.540] |
| pooled | eventual | delta_l32 | 2910 (618) | 0.497 [0.477, 0.517] | 0.514 [0.489, 0.534] |
| pooled | eventual | delta_l40 | 2910 (618) | 0.502 [0.481, 0.525] | 0.523 [0.495, 0.545] |
| pooled | eventual | scalar_l24 | 2910 (618) | 0.499 [0.447, 0.563] | 0.531 [0.487, 0.593] |
| pooled | eventual | scalar_l32 | 2910 (618) | 0.532 [0.480, 0.582] | 0.548 [0.487, 0.599] |
| pooled | eventual | scalar_l40 | 2910 (618) | 0.551 [0.492, 0.611] | 0.575 [0.505, 0.633] |
| pooled | eventual | pressure_l32 | 2910 (618) | 0.430 [0.373, 0.492] | 0.468 [0.382, 0.527] |
| pooled | A_hazard | delta_l24 | 2910 (168) | 0.530 [0.486, 0.572] | 0.566 [0.514, 0.612] |
| pooled | A_hazard | delta_l32 | 2910 (168) | 0.515 [0.468, 0.561] | 0.534 [0.478, 0.586] |
| pooled | A_hazard | delta_l40 | 2910 (168) | 0.495 [0.458, 0.532] | 0.521 [0.474, 0.567] |
| pooled | A_hazard | scalar_l24 | 2910 (168) | 0.556 [0.508, 0.603] | 0.568 [0.522, 0.625] |
| pooled | A_hazard | scalar_l32 | 2910 (168) | 0.526 [0.478, 0.574] | 0.533 [0.479, 0.590] |
| pooled | A_hazard | scalar_l40 | 2910 (168) | 0.524 [0.475, 0.572] | 0.521 [0.466, 0.576] |
| pooled | A_hazard | pressure_l32 | 2910 (168) | 0.436 [0.368, 0.510] | 0.442 [0.362, 0.525] |
| pooled | pressure | pressure_l32 | 4184 (2910) | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| loso | eventual | delta_l24 | 2910 (618) | 0.506 [0.484, 0.528] | 0.506 [0.484, 0.528] |
| loso | eventual | delta_l32 | 2910 (618) | 0.505 [0.487, 0.525] | 0.505 [0.487, 0.525] |
| loso | eventual | delta_l40 | 2910 (618) | 0.506 [0.487, 0.526] | 0.506 [0.487, 0.526] |
| loso | eventual | scalar_l24 | 2910 (618) | 0.510 [0.459, 0.565] | 0.510 [0.459, 0.565] |
| loso | eventual | scalar_l32 | 2910 (618) | 0.509 [0.462, 0.564] | 0.509 [0.462, 0.564] |
| loso | eventual | scalar_l40 | 2910 (618) | 0.486 [0.433, 0.546] | 0.486 [0.433, 0.546] |
| loso | eventual | pressure_l32 | 2910 (618) | 0.426 [0.371, 0.488] | 0.426 [0.371, 0.488] |
| loso | A_hazard | delta_l24 | 2910 (168) | 0.576 [0.537, 0.615] | 0.576 [0.537, 0.615] |
| loso | A_hazard | delta_l32 | 2910 (168) | 0.543 [0.501, 0.586] | 0.543 [0.501, 0.586] |
| loso | A_hazard | delta_l40 | 2910 (168) | 0.513 [0.478, 0.551] | 0.513 [0.478, 0.551] |
| loso | A_hazard | scalar_l24 | 2910 (168) | 0.561 [0.515, 0.610] | 0.561 [0.515, 0.610] |
| loso | A_hazard | scalar_l32 | 2910 (168) | 0.525 [0.475, 0.575] | 0.525 [0.475, 0.575] |
| loso | A_hazard | scalar_l40 | 2910 (168) | 0.521 [0.469, 0.571] | 0.521 [0.469, 0.571] |
| loso | A_hazard | pressure_l32 | 2910 (168) | 0.437 [0.371, 0.510] | 0.437 [0.371, 0.510] |
| loso | pressure | pressure_l32 | 4184 (2910) | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |

## Files

- probe_scores.csv: reference export columns plus label_variant; key = (row_id, analysis, seed, method, label_variant). Eventual scores include held-out benign rows; A contains recruiting rows; pressure classification contains both. Scores are raw logistic decisions. No thresholds are estimated.
- pooled-predictions.npz and loso-predictions.npz: all OOF arrays, eligibility and fold indices.
- fits/: coefficients, scaler parameters, exact training/test row indices and test scores for every fitted model.
- delta.npy, scalar.npy, trajectory_links.npz: causal features, predecessor/anchor indices and coverage.
- preflight.json, audit.json and validation.json: source identity/family separation, feature coverage, persisted-score reconstruction and CSV checks.
- Parents: 20261025-0337-e05-replay2-data, 20261025-0240-e05-replay2-folds, 20261025-0340-e05-replay2-fits (LOSO splits only), 20261025-0730-e05-near-term (A labels only).

Pressure is a condition-discrimination diagnostic, not a measurement of a specific persuasion tactic or causal pressure. Trajectory magnitudes can reflect context length, read/tool transitions and episode progress. First post-read deltas may primarily detect exposure; these analyses do not establish an internal decision time.

Final audit: 429 saved models, all test scores reconstructed (maximum absolute error 1.91e-14), 323,052 CSV rows checked against prediction arrays and labels, and exact fold membership verified. All 4,184 eligible predecessors are consecutive target requests; each anchor is exactly the first request after reading. Five offline tests pass. No GPU or paid calls; no commit.
