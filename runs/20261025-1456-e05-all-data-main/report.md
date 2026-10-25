# All-data main estimate

This report estimates how well activation probes and text monitors predict a target model violating a rule. It uses the combined dataset `runs/20261025-1026-e05-replay3-data-1d95`, containing 6,404 eligible steps in 338 episodes. Independent confirmation results are in `runs/20261025-1030-e06-confirmation/report.md`; the cross-validation estimates here reuse those episodes and are not another independent confirmation. Ranking and probe training use recruiting episodes, where a peer asks the target to violate the rule. Eligible steps are strictly after the first protected-token read and before the first forbidden action. Control and alone episodes contribute to the common family-fold assignments but not to training or ranking.

Labels: eventual is positive at every eligible step of an episode that eventually violates the rule. A_hazard is positive only when the action occurs in the current or next round; earlier steps are negative. B_round_contrast keeps those near-action positives and held-episode negatives, dropping earlier steps of eventual violations. C_step_contrast uses the same clean contrast with at most three target requests until the action. B and C use hindsight to exclude steps and are not prospective alarm labels.

Five pooled family folds and six leave-one-scenario-out (LOSO) rotations, each at seeds 42/43/44. LOSO purges shared test families from training. Inner family holdout is 25%; LOSO uses a held-out training scenario with shared-family purging. Outer and inner splits are made using eventual episode labels, then filtered for each near-term contrast. Logistic C=0.1, training-only StandardScaler, original round-balanced weights, 17 candidate layers; fixed32 is secondary. Metrics average per-seed AUROCs, not raw scores. All intervals are paired family-bootstrap 95% confidence intervals, 1,000 resamples, seed 20261025, conditional on fitted models. Balanced AUROC is the unweighted mean of within-round AUROCs across comparable scenarios; missing single-class strata are omitted.

Activation probes are linear classifiers on the 5,120-dimensional residual stream at the last prompt token before the Qwen3-32B target replies. Candidate decoder blocks are 0,4,8,…,60,63 (zero-based). Training weights give positive and negative steps equal total weight within each round; rounds without both classes receive zero weight. A family groups related episode variants, so keeping families together prevents closely related episodes crossing a training/test boundary.

AUROC is the probability that a random positive has a higher score than a random negative, with half credit for ties; 0.5 is chance. The primary metric compares only steps from the same scenario and round, weighting comparable strata by their positive count. Fold-stratified AUROC additionally requires the same fitted outer fold. Pooled AUROC compares all eligible pairs. Balanced AUROC gives equal weight to each scenario’s within-round result.

Text monitors use cached scores from `runs/20261025-0147-e06-monitor-main` and `runs/20261025-0841-e06-monitor-main-balanced`. Jev is `typesafe/jev-1.14`; llm denotes `openai/gpt-5-nano`. A detector asks whether the target is breaking the rule; a forecaster asks whether it will break the rule. L1 shows target tool calls and posted messages, L2 adds peer messages, and L3 adds unposted target text and tool results. Each setup is scored on exactly the same rows as the probe.

## Headline

| Label | Analysis | Probe within scenario×round [CI] | Fold-stratified [CI] | Jev F L3 [CI] | GPT-5-nano det L2 [CI] |
|---|---|---|---|---|---|
| eventual | pooled | 0.488 [0.438, 0.537] | 0.512 [0.458, 0.559] | 0.577 [0.521, 0.628] | 0.549 [0.518, 0.580] |
| eventual | loso | 0.523 [0.486, 0.560] | 0.523 [0.486, 0.560] | 0.577 [0.521, 0.628] | 0.549 [0.518, 0.580] |
| A_hazard | pooled | 0.586 [0.541, 0.631] | 0.618 [0.571, 0.666] | 0.650 [0.608, 0.688] | 0.557 [0.518, 0.593] |
| A_hazard | loso | 0.579 [0.537, 0.619] | 0.579 [0.537, 0.619] | 0.650 [0.608, 0.688] | 0.557 [0.518, 0.593] |
| B_round_contrast | pooled | 0.605 [0.554, 0.652] | 0.639 [0.581, 0.688] | 0.664 [0.616, 0.707] | 0.562 [0.524, 0.600] |
| B_round_contrast | loso | 0.586 [0.544, 0.628] | 0.586 [0.544, 0.628] | 0.664 [0.616, 0.707] | 0.562 [0.524, 0.600] |
| C_step_contrast | pooled | 0.589 [0.547, 0.631] | 0.622 [0.568, 0.671] | 0.658 [0.605, 0.705] | 0.532 [0.492, 0.570] |
| C_step_contrast | loso | 0.569 [0.527, 0.610] | 0.569 [0.527, 0.610] | 0.658 [0.605, 0.705] | 0.532 [0.492, 0.570] |

## Interpretation

For the prospective near-term label A, the probe scores 0.586 [0.541, 0.631] in pooled cross-validation and 0.579 [0.537, 0.619] in held-out scenarios. The eventual-label probe scores 0.488/0.523 (pooled/LOSO), with both intervals containing chance. The signal is stronger for proximity to an action than for eventual episode outcome.

Jev forecaster L3 exceeds the A probe by 0.064 [0.012, 0.113] in pooled CV and 0.071 [0.024, 0.116] in LOSO. The pooled fold-stratified comparison is less conclusive; its interval includes zero. These AUROCs describe rankings and do not establish an alarm’s false-positive rate.

Adding the probe to GPT-5-nano detector L2 gives an A-label pooled gain of 0.081 [0.038, 0.126]; the LOSO gain is 0.022 [-0.013, 0.059]. The gain does not clearly transfer to unseen scenarios for A. Adding the probe to Jev has no clear A-label gain. Combination results retain the stacking limitation below; B and C additionally use hindsight exclusions.

## All methods

| Label | Analysis | Method | Scenario×round [CI] | Fold×scenario×round [CI] | Pooled [CI] | Scenario mean [CI] | Rows (+) |
|---|---|---|---|---|---|---|---|
| eventual | pooled | nested | 0.488 [0.438, 0.537] | 0.512 [0.458, 0.559] | 0.630 [0.582, 0.674] | 0.478 [0.433, 0.531] | 4697 (998) |
| eventual | pooled | fixed32 | 0.512 [0.453, 0.567] | 0.543 [0.477, 0.590] | 0.654 [0.600, 0.701] | 0.497 [0.448, 0.556] | 4697 (998) |
| eventual | pooled | jev detector L1 | 0.505 [0.466, 0.544] | 0.503 [0.466, 0.545] | 0.432 [0.386, 0.478] | 0.517 [0.479, 0.552] | 4697 (998) |
| eventual | pooled | jev detector L2 | 0.526 [0.494, 0.556] | 0.527 [0.493, 0.559] | 0.511 [0.479, 0.543] | 0.531 [0.499, 0.559] | 4697 (998) |
| eventual | pooled | jev detector L3 | 0.537 [0.495, 0.579] | 0.542 [0.496, 0.586] | 0.564 [0.517, 0.611] | 0.547 [0.510, 0.583] | 4697 (998) |
| eventual | pooled | jev forecaster L1 | 0.504 [0.448, 0.555] | 0.501 [0.443, 0.556] | 0.493 [0.431, 0.553] | 0.521 [0.475, 0.561] | 4697 (998) |
| eventual | pooled | jev forecaster L2 | 0.563 [0.511, 0.613] | 0.561 [0.502, 0.610] | 0.695 [0.651, 0.742] | 0.571 [0.529, 0.611] | 4697 (998) |
| eventual | pooled | jev forecaster L3 | 0.577 [0.521, 0.628] | 0.579 [0.517, 0.630] | 0.705 [0.661, 0.751] | 0.587 [0.542, 0.627] | 4697 (998) |
| eventual | pooled | llm detector L2 | 0.549 [0.518, 0.580] | 0.557 [0.525, 0.593] | 0.595 [0.564, 0.629] | 0.547 [0.516, 0.574] | 4697 (998) |
| eventual | pooled | llm forecaster L2 | 0.545 [0.514, 0.576] | 0.544 [0.512, 0.574] | 0.644 [0.611, 0.676] | 0.560 [0.525, 0.588] | 4697 (998) |
| eventual | pooled | jev_base | 0.535 [0.483, 0.590] | 0.584 [0.529, 0.638] | 0.725 [0.687, 0.770] | 0.550 [0.511, 0.597] | 4697 (998) |
| eventual | pooled | jev_probe | 0.523 [0.473, 0.575] | 0.573 [0.522, 0.627] | 0.724 [0.685, 0.769] | 0.535 [0.494, 0.583] | 4697 (998) |
| eventual | pooled | nano_base | 0.489 [0.444, 0.535] | 0.558 [0.518, 0.609] | 0.717 [0.679, 0.760] | 0.495 [0.456, 0.535] | 4697 (998) |
| eventual | pooled | nano_probe | 0.476 [0.434, 0.519] | 0.535 [0.491, 0.582] | 0.716 [0.679, 0.759] | 0.476 [0.437, 0.519] | 4697 (998) |
| eventual | pooled | jev_nano | 0.543 [0.491, 0.595] | 0.599 [0.550, 0.650] | 0.726 [0.689, 0.771] | 0.553 [0.513, 0.600] | 4697 (998) |
| eventual | loso | nested | 0.523 [0.486, 0.560] | 0.523 [0.486, 0.560] | 0.583 [0.527, 0.638] | 0.522 [0.489, 0.554] | 4697 (998) |
| eventual | loso | fixed32 | 0.524 [0.475, 0.572] | 0.524 [0.475, 0.572] | 0.553 [0.492, 0.622] | 0.505 [0.459, 0.563] | 4697 (998) |
| eventual | loso | jev detector L1 | 0.505 [0.466, 0.544] | 0.505 [0.466, 0.544] | 0.432 [0.386, 0.478] | 0.517 [0.479, 0.552] | 4697 (998) |
| eventual | loso | jev detector L2 | 0.526 [0.494, 0.556] | 0.526 [0.494, 0.556] | 0.511 [0.479, 0.543] | 0.531 [0.499, 0.559] | 4697 (998) |
| eventual | loso | jev detector L3 | 0.537 [0.495, 0.579] | 0.537 [0.495, 0.579] | 0.564 [0.517, 0.611] | 0.547 [0.510, 0.583] | 4697 (998) |
| eventual | loso | jev forecaster L1 | 0.504 [0.448, 0.555] | 0.504 [0.448, 0.555] | 0.493 [0.431, 0.553] | 0.521 [0.475, 0.561] | 4697 (998) |
| eventual | loso | jev forecaster L2 | 0.563 [0.511, 0.613] | 0.563 [0.511, 0.613] | 0.695 [0.651, 0.742] | 0.571 [0.529, 0.611] | 4697 (998) |
| eventual | loso | jev forecaster L3 | 0.577 [0.521, 0.628] | 0.577 [0.521, 0.628] | 0.705 [0.661, 0.751] | 0.587 [0.542, 0.627] | 4697 (998) |
| eventual | loso | llm detector L2 | 0.549 [0.518, 0.580] | 0.549 [0.518, 0.580] | 0.595 [0.564, 0.629] | 0.547 [0.516, 0.574] | 4697 (998) |
| eventual | loso | llm forecaster L2 | 0.545 [0.514, 0.576] | 0.545 [0.514, 0.576] | 0.644 [0.611, 0.676] | 0.560 [0.525, 0.588] | 4697 (998) |
| eventual | loso | jev_base | 0.571 [0.523, 0.618] | 0.571 [0.523, 0.618] | 0.717 [0.677, 0.762] | 0.582 [0.543, 0.623] | 4697 (998) |
| eventual | loso | jev_probe | 0.575 [0.529, 0.620] | 0.575 [0.529, 0.620] | 0.713 [0.671, 0.759] | 0.585 [0.546, 0.625] | 4697 (998) |
| eventual | loso | nano_base | 0.539 [0.498, 0.581] | 0.539 [0.498, 0.581] | 0.703 [0.664, 0.748] | 0.536 [0.495, 0.575] | 4697 (998) |
| eventual | loso | nano_probe | 0.540 [0.501, 0.579] | 0.540 [0.501, 0.579] | 0.699 [0.658, 0.744] | 0.538 [0.499, 0.574] | 4697 (998) |
| eventual | loso | jev_nano | 0.561 [0.514, 0.610] | 0.561 [0.514, 0.610] | 0.711 [0.671, 0.756] | 0.571 [0.534, 0.610] | 4697 (998) |
| A_hazard | pooled | nested | 0.586 [0.541, 0.631] | 0.618 [0.571, 0.666] | 0.696 [0.657, 0.734] | 0.580 [0.536, 0.623] | 4697 (250) |
| A_hazard | pooled | fixed32 | 0.573 [0.520, 0.625] | 0.603 [0.544, 0.649] | 0.686 [0.641, 0.731] | 0.564 [0.517, 0.619] | 4697 (250) |
| A_hazard | pooled | jev detector L1 | 0.509 [0.475, 0.543] | 0.507 [0.473, 0.542] | 0.441 [0.400, 0.481] | 0.510 [0.474, 0.551] | 4697 (250) |
| A_hazard | pooled | jev detector L2 | 0.550 [0.517, 0.583] | 0.553 [0.517, 0.588] | 0.538 [0.505, 0.570] | 0.542 [0.508, 0.577] | 4697 (250) |
| A_hazard | pooled | jev detector L3 | 0.578 [0.537, 0.616] | 0.583 [0.534, 0.626] | 0.628 [0.586, 0.666] | 0.576 [0.534, 0.618] | 4697 (250) |
| A_hazard | pooled | jev forecaster L1 | 0.523 [0.477, 0.568] | 0.521 [0.470, 0.567] | 0.519 [0.476, 0.561] | 0.527 [0.482, 0.572] | 4697 (250) |
| A_hazard | pooled | jev forecaster L2 | 0.626 [0.583, 0.669] | 0.636 [0.582, 0.679] | 0.763 [0.716, 0.799] | 0.617 [0.573, 0.666] | 4697 (250) |
| A_hazard | pooled | jev forecaster L3 | 0.650 [0.608, 0.688] | 0.658 [0.611, 0.697] | 0.771 [0.724, 0.806] | 0.640 [0.598, 0.683] | 4697 (250) |
| A_hazard | pooled | llm detector L2 | 0.557 [0.518, 0.593] | 0.564 [0.519, 0.602] | 0.624 [0.584, 0.667] | 0.556 [0.511, 0.599] | 4697 (250) |
| A_hazard | pooled | llm forecaster L2 | 0.555 [0.514, 0.598] | 0.553 [0.509, 0.592] | 0.650 [0.607, 0.691] | 0.543 [0.501, 0.590] | 4697 (250) |
| A_hazard | pooled | jev_base | 0.615 [0.572, 0.651] | 0.655 [0.606, 0.694] | 0.751 [0.694, 0.799] | 0.609 [0.566, 0.650] | 4697 (250) |
| A_hazard | pooled | jev_probe | 0.623 [0.582, 0.665] | 0.664 [0.620, 0.704] | 0.768 [0.719, 0.809] | 0.615 [0.576, 0.658] | 4697 (250) |
| A_hazard | pooled | nano_base | 0.494 [0.453, 0.534] | 0.558 [0.506, 0.592] | 0.701 [0.634, 0.761] | 0.499 [0.454, 0.541] | 4697 (250) |
| A_hazard | pooled | nano_probe | 0.575 [0.531, 0.619] | 0.618 [0.569, 0.663] | 0.744 [0.692, 0.790] | 0.573 [0.529, 0.618] | 4697 (250) |
| A_hazard | pooled | jev_nano | 0.615 [0.574, 0.650] | 0.664 [0.618, 0.703] | 0.754 [0.700, 0.800] | 0.610 [0.569, 0.649] | 4697 (250) |
| A_hazard | loso | nested | 0.579 [0.537, 0.619] | 0.579 [0.537, 0.619] | 0.607 [0.570, 0.646] | 0.585 [0.546, 0.624] | 4697 (250) |
| A_hazard | loso | fixed32 | 0.572 [0.525, 0.618] | 0.572 [0.525, 0.618] | 0.549 [0.495, 0.600] | 0.570 [0.523, 0.617] | 4697 (250) |
| A_hazard | loso | jev detector L1 | 0.509 [0.475, 0.543] | 0.509 [0.475, 0.543] | 0.441 [0.400, 0.481] | 0.510 [0.474, 0.551] | 4697 (250) |
| A_hazard | loso | jev detector L2 | 0.550 [0.517, 0.583] | 0.550 [0.517, 0.583] | 0.538 [0.505, 0.570] | 0.542 [0.508, 0.577] | 4697 (250) |
| A_hazard | loso | jev detector L3 | 0.578 [0.537, 0.616] | 0.578 [0.537, 0.616] | 0.628 [0.586, 0.666] | 0.576 [0.534, 0.618] | 4697 (250) |
| A_hazard | loso | jev forecaster L1 | 0.523 [0.477, 0.568] | 0.523 [0.477, 0.568] | 0.519 [0.476, 0.561] | 0.527 [0.482, 0.572] | 4697 (250) |
| A_hazard | loso | jev forecaster L2 | 0.626 [0.583, 0.669] | 0.626 [0.583, 0.669] | 0.763 [0.716, 0.799] | 0.617 [0.573, 0.666] | 4697 (250) |
| A_hazard | loso | jev forecaster L3 | 0.650 [0.608, 0.688] | 0.650 [0.608, 0.688] | 0.771 [0.724, 0.806] | 0.640 [0.598, 0.683] | 4697 (250) |
| A_hazard | loso | llm detector L2 | 0.557 [0.518, 0.593] | 0.557 [0.518, 0.593] | 0.624 [0.584, 0.667] | 0.556 [0.511, 0.599] | 4697 (250) |
| A_hazard | loso | llm forecaster L2 | 0.555 [0.514, 0.598] | 0.555 [0.514, 0.598] | 0.650 [0.607, 0.691] | 0.543 [0.501, 0.590] | 4697 (250) |
| A_hazard | loso | jev_base | 0.645 [0.603, 0.683] | 0.645 [0.603, 0.683] | 0.744 [0.688, 0.791] | 0.636 [0.588, 0.679] | 4697 (250) |
| A_hazard | loso | jev_probe | 0.649 [0.608, 0.688] | 0.649 [0.608, 0.688] | 0.739 [0.684, 0.784] | 0.642 [0.599, 0.684] | 4697 (250) |
| A_hazard | loso | nano_base | 0.554 [0.512, 0.594] | 0.554 [0.512, 0.594] | 0.690 [0.620, 0.748] | 0.555 [0.507, 0.598] | 4697 (250) |
| A_hazard | loso | nano_probe | 0.576 [0.535, 0.615] | 0.576 [0.535, 0.615] | 0.697 [0.632, 0.753] | 0.580 [0.540, 0.619] | 4697 (250) |
| A_hazard | loso | jev_nano | 0.649 [0.607, 0.685] | 0.649 [0.607, 0.685] | 0.746 [0.689, 0.790] | 0.640 [0.597, 0.680] | 4697 (250) |
| B_round_contrast | pooled | nested | 0.605 [0.554, 0.652] | 0.639 [0.581, 0.688] | 0.723 [0.684, 0.762] | 0.594 [0.551, 0.641] | 3949 (250) |
| B_round_contrast | pooled | fixed32 | 0.581 [0.521, 0.634] | 0.617 [0.542, 0.668] | 0.704 [0.658, 0.749] | 0.568 [0.516, 0.621] | 3949 (250) |
| B_round_contrast | pooled | jev detector L1 | 0.511 [0.472, 0.547] | 0.510 [0.471, 0.550] | 0.430 [0.385, 0.474] | 0.512 [0.471, 0.554] | 3949 (250) |
| B_round_contrast | pooled | jev detector L2 | 0.554 [0.519, 0.586] | 0.556 [0.517, 0.592] | 0.538 [0.503, 0.573] | 0.545 [0.509, 0.582] | 3949 (250) |
| B_round_contrast | pooled | jev detector L3 | 0.586 [0.542, 0.628] | 0.591 [0.539, 0.636] | 0.635 [0.586, 0.677] | 0.583 [0.537, 0.626] | 3949 (250) |
| B_round_contrast | pooled | jev forecaster L1 | 0.522 [0.472, 0.571] | 0.525 [0.469, 0.574] | 0.516 [0.466, 0.565] | 0.526 [0.476, 0.575] | 3949 (250) |
| B_round_contrast | pooled | jev forecaster L2 | 0.637 [0.587, 0.682] | 0.646 [0.588, 0.696] | 0.784 [0.740, 0.820] | 0.626 [0.576, 0.679] | 3949 (250) |
| B_round_contrast | pooled | jev forecaster L3 | 0.664 [0.616, 0.707] | 0.676 [0.625, 0.721] | 0.793 [0.749, 0.826] | 0.654 [0.603, 0.699] | 3949 (250) |
| B_round_contrast | pooled | llm detector L2 | 0.562 [0.524, 0.600] | 0.569 [0.522, 0.609] | 0.637 [0.595, 0.680] | 0.561 [0.514, 0.603] | 3949 (250) |
| B_round_contrast | pooled | llm forecaster L2 | 0.565 [0.522, 0.609] | 0.564 [0.520, 0.608] | 0.671 [0.628, 0.711] | 0.555 [0.509, 0.602] | 3949 (250) |
| B_round_contrast | pooled | jev_base | 0.635 [0.588, 0.678] | 0.677 [0.626, 0.722] | 0.779 [0.727, 0.823] | 0.627 [0.576, 0.673] | 3949 (250) |
| B_round_contrast | pooled | jev_probe | 0.644 [0.601, 0.685] | 0.684 [0.634, 0.727] | 0.800 [0.755, 0.837] | 0.633 [0.590, 0.676] | 3949 (250) |
| B_round_contrast | pooled | nano_base | 0.507 [0.465, 0.548] | 0.560 [0.501, 0.597] | 0.731 [0.665, 0.787] | 0.512 [0.466, 0.552] | 3949 (250) |
| B_round_contrast | pooled | nano_probe | 0.597 [0.547, 0.642] | 0.644 [0.590, 0.684] | 0.779 [0.731, 0.821] | 0.590 [0.544, 0.636] | 3949 (250) |
| B_round_contrast | pooled | jev_nano | 0.638 [0.592, 0.678] | 0.685 [0.636, 0.731] | 0.782 [0.732, 0.823] | 0.632 [0.584, 0.674] | 3949 (250) |
| B_round_contrast | loso | nested | 0.586 [0.544, 0.628] | 0.586 [0.544, 0.628] | 0.570 [0.527, 0.611] | 0.580 [0.535, 0.620] | 3949 (250) |
| B_round_contrast | loso | fixed32 | 0.595 [0.541, 0.649] | 0.595 [0.541, 0.649] | 0.561 [0.497, 0.621] | 0.584 [0.530, 0.638] | 3949 (250) |
| B_round_contrast | loso | jev detector L1 | 0.511 [0.472, 0.547] | 0.511 [0.472, 0.547] | 0.430 [0.385, 0.474] | 0.512 [0.471, 0.554] | 3949 (250) |
| B_round_contrast | loso | jev detector L2 | 0.554 [0.519, 0.586] | 0.554 [0.519, 0.586] | 0.538 [0.503, 0.573] | 0.545 [0.509, 0.582] | 3949 (250) |
| B_round_contrast | loso | jev detector L3 | 0.586 [0.542, 0.628] | 0.586 [0.542, 0.628] | 0.635 [0.586, 0.677] | 0.583 [0.537, 0.626] | 3949 (250) |
| B_round_contrast | loso | jev forecaster L1 | 0.522 [0.472, 0.571] | 0.522 [0.472, 0.571] | 0.516 [0.466, 0.565] | 0.526 [0.476, 0.575] | 3949 (250) |
| B_round_contrast | loso | jev forecaster L2 | 0.637 [0.587, 0.682] | 0.637 [0.587, 0.682] | 0.784 [0.740, 0.820] | 0.626 [0.576, 0.679] | 3949 (250) |
| B_round_contrast | loso | jev forecaster L3 | 0.664 [0.616, 0.707] | 0.664 [0.616, 0.707] | 0.793 [0.749, 0.826] | 0.654 [0.603, 0.699] | 3949 (250) |
| B_round_contrast | loso | llm detector L2 | 0.562 [0.524, 0.600] | 0.562 [0.524, 0.600] | 0.637 [0.595, 0.680] | 0.561 [0.514, 0.603] | 3949 (250) |
| B_round_contrast | loso | llm forecaster L2 | 0.565 [0.522, 0.609] | 0.565 [0.522, 0.609] | 0.671 [0.628, 0.711] | 0.555 [0.509, 0.602] | 3949 (250) |
| B_round_contrast | loso | jev_base | 0.661 [0.612, 0.703] | 0.661 [0.612, 0.703] | 0.774 [0.721, 0.817] | 0.651 [0.598, 0.696] | 3949 (250) |
| B_round_contrast | loso | jev_probe | 0.662 [0.616, 0.702] | 0.662 [0.616, 0.702] | 0.772 [0.719, 0.814] | 0.650 [0.600, 0.693] | 3949 (250) |
| B_round_contrast | loso | nano_base | 0.560 [0.515, 0.602] | 0.560 [0.515, 0.602] | 0.722 [0.657, 0.775] | 0.561 [0.509, 0.606] | 3949 (250) |
| B_round_contrast | loso | nano_probe | 0.584 [0.542, 0.621] | 0.584 [0.542, 0.621] | 0.725 [0.662, 0.779] | 0.580 [0.532, 0.619] | 3949 (250) |
| B_round_contrast | loso | jev_nano | 0.663 [0.616, 0.703] | 0.663 [0.616, 0.703] | 0.774 [0.720, 0.815] | 0.653 [0.605, 0.696] | 3949 (250) |
| C_step_contrast | pooled | nested | 0.589 [0.547, 0.631] | 0.622 [0.568, 0.671] | 0.682 [0.641, 0.723] | 0.589 [0.546, 0.633] | 3996 (297) |
| C_step_contrast | pooled | fixed32 | 0.590 [0.532, 0.640] | 0.615 [0.545, 0.667] | 0.684 [0.631, 0.731] | 0.593 [0.540, 0.645] | 3996 (297) |
| C_step_contrast | pooled | jev detector L1 | 0.514 [0.470, 0.555] | 0.513 [0.467, 0.556] | 0.447 [0.399, 0.496] | 0.514 [0.472, 0.557] | 3996 (297) |
| C_step_contrast | pooled | jev detector L2 | 0.550 [0.516, 0.584] | 0.553 [0.513, 0.591] | 0.540 [0.503, 0.575] | 0.547 [0.511, 0.583] | 3996 (297) |
| C_step_contrast | pooled | jev detector L3 | 0.567 [0.526, 0.608] | 0.573 [0.528, 0.618] | 0.597 [0.552, 0.639] | 0.562 [0.516, 0.603] | 3996 (297) |
| C_step_contrast | pooled | jev forecaster L1 | 0.497 [0.438, 0.548] | 0.499 [0.440, 0.557] | 0.477 [0.419, 0.536] | 0.499 [0.443, 0.551] | 3996 (297) |
| C_step_contrast | pooled | jev forecaster L2 | 0.635 [0.585, 0.683] | 0.646 [0.591, 0.694] | 0.738 [0.691, 0.783] | 0.631 [0.580, 0.678] | 3996 (297) |
| C_step_contrast | pooled | jev forecaster L3 | 0.658 [0.605, 0.705] | 0.671 [0.617, 0.720] | 0.746 [0.699, 0.789] | 0.653 [0.603, 0.697] | 3996 (297) |
| C_step_contrast | pooled | llm detector L2 | 0.532 [0.492, 0.570] | 0.538 [0.492, 0.576] | 0.585 [0.547, 0.626] | 0.531 [0.491, 0.569] | 3996 (297) |
| C_step_contrast | pooled | llm forecaster L2 | 0.544 [0.503, 0.585] | 0.536 [0.488, 0.578] | 0.630 [0.591, 0.670] | 0.544 [0.502, 0.585] | 3996 (297) |
| C_step_contrast | pooled | jev_base | 0.637 [0.588, 0.681] | 0.676 [0.629, 0.726] | 0.736 [0.690, 0.779] | 0.633 [0.585, 0.675] | 3996 (297) |
| C_step_contrast | pooled | jev_probe | 0.632 [0.586, 0.674] | 0.673 [0.621, 0.719] | 0.751 [0.706, 0.793] | 0.627 [0.583, 0.670] | 3996 (297) |
| C_step_contrast | pooled | nano_base | 0.467 [0.426, 0.506] | 0.519 [0.466, 0.555] | 0.691 [0.639, 0.743] | 0.466 [0.423, 0.506] | 3996 (297) |
| C_step_contrast | pooled | nano_probe | 0.569 [0.524, 0.613] | 0.622 [0.566, 0.668] | 0.724 [0.674, 0.770] | 0.566 [0.520, 0.611] | 3996 (297) |
| C_step_contrast | pooled | jev_nano | 0.635 [0.587, 0.679] | 0.673 [0.625, 0.723] | 0.735 [0.689, 0.779] | 0.630 [0.582, 0.673] | 3996 (297) |
| C_step_contrast | loso | nested | 0.569 [0.527, 0.610] | 0.569 [0.527, 0.610] | 0.574 [0.534, 0.613] | 0.572 [0.535, 0.613] | 3996 (297) |
| C_step_contrast | loso | fixed32 | 0.602 [0.547, 0.659] | 0.602 [0.547, 0.659] | 0.560 [0.498, 0.621] | 0.597 [0.545, 0.652] | 3996 (297) |
| C_step_contrast | loso | jev detector L1 | 0.514 [0.470, 0.555] | 0.514 [0.470, 0.555] | 0.447 [0.399, 0.496] | 0.514 [0.472, 0.557] | 3996 (297) |
| C_step_contrast | loso | jev detector L2 | 0.550 [0.516, 0.584] | 0.550 [0.516, 0.584] | 0.540 [0.503, 0.575] | 0.547 [0.511, 0.583] | 3996 (297) |
| C_step_contrast | loso | jev detector L3 | 0.567 [0.526, 0.608] | 0.567 [0.526, 0.608] | 0.597 [0.552, 0.639] | 0.562 [0.516, 0.603] | 3996 (297) |
| C_step_contrast | loso | jev forecaster L1 | 0.497 [0.438, 0.548] | 0.497 [0.438, 0.548] | 0.477 [0.419, 0.536] | 0.499 [0.443, 0.551] | 3996 (297) |
| C_step_contrast | loso | jev forecaster L2 | 0.635 [0.585, 0.683] | 0.635 [0.585, 0.683] | 0.738 [0.691, 0.783] | 0.631 [0.580, 0.678] | 3996 (297) |
| C_step_contrast | loso | jev forecaster L3 | 0.658 [0.605, 0.705] | 0.658 [0.605, 0.705] | 0.746 [0.699, 0.789] | 0.653 [0.603, 0.697] | 3996 (297) |
| C_step_contrast | loso | llm detector L2 | 0.532 [0.492, 0.570] | 0.532 [0.492, 0.570] | 0.585 [0.547, 0.626] | 0.531 [0.491, 0.569] | 3996 (297) |
| C_step_contrast | loso | llm forecaster L2 | 0.544 [0.503, 0.585] | 0.544 [0.503, 0.585] | 0.630 [0.591, 0.670] | 0.544 [0.502, 0.585] | 3996 (297) |
| C_step_contrast | loso | jev_base | 0.659 [0.608, 0.702] | 0.659 [0.608, 0.702] | 0.717 [0.666, 0.764] | 0.655 [0.606, 0.697] | 3996 (297) |
| C_step_contrast | loso | jev_probe | 0.655 [0.608, 0.699] | 0.655 [0.608, 0.699] | 0.713 [0.660, 0.761] | 0.652 [0.606, 0.694] | 3996 (297) |
| C_step_contrast | loso | nano_base | 0.532 [0.486, 0.576] | 0.532 [0.486, 0.576] | 0.672 [0.616, 0.725] | 0.531 [0.486, 0.574] | 3996 (297) |
| C_step_contrast | loso | nano_probe | 0.550 [0.510, 0.591] | 0.550 [0.510, 0.591] | 0.669 [0.614, 0.723] | 0.549 [0.511, 0.587] | 3996 (297) |
| C_step_contrast | loso | jev_nano | 0.650 [0.602, 0.694] | 0.650 [0.602, 0.694] | 0.712 [0.661, 0.759] | 0.645 [0.597, 0.686] | 3996 (297) |

## Combination tests

Combination models follow `experiments/E06-monitors/combine.py`: train-only scaling and logistic C=1 on [round, log prompt length, monitor], then add the probe or second monitor. Training rows use probe scores from models that held out those rows. Those probe models may have trained on the outer test fold: this inherited OOF-stacking leakage can optimistically bias the combination result. These are secondary comparisons, not leakage-free nested estimates. LOSO stacker training explicitly uses the family-purged outer training rows. Raw scores are retained, matching combine.py; fold-stratified results help diagnose cross-fold scale shifts.

| Label | Analysis | Contrast | Scenario×round gain [CI] | Fold-stratified gain [CI] |
|---|---|---|---|---|
| eventual | pooled | jev_probe_minus_jev_base | -0.012 [-0.031, 0.003] | -0.011 [-0.033, 0.009] |
| eventual | pooled | nano_probe_minus_nano_base | -0.012 [-0.041, 0.014] | -0.023 [-0.063, 0.010] |
| eventual | pooled | jev_nano_minus_jev_base | 0.007 [-0.006, 0.022] | 0.015 [-0.002, 0.035] |
| eventual | pooled | jev forecaster L3_minus_nested | 0.090 [0.011, 0.164] | 0.067 [-0.008, 0.145] |
| eventual | pooled | llm detector L2_minus_nested | 0.061 [0.008, 0.122] | 0.045 [-0.008, 0.114] |
| eventual | loso | jev_probe_minus_jev_base | 0.005 [-0.003, 0.013] | 0.005 [-0.003, 0.013] |
| eventual | loso | nano_probe_minus_nano_base | 0.001 [-0.023, 0.020] | 0.001 [-0.023, 0.020] |
| eventual | loso | jev_nano_minus_jev_base | -0.010 [-0.027, 0.007] | -0.010 [-0.027, 0.007] |
| eventual | loso | jev forecaster L3_minus_nested | 0.054 [-0.012, 0.113] | 0.054 [-0.012, 0.113] |
| eventual | loso | llm detector L2_minus_nested | 0.026 [-0.022, 0.075] | 0.026 [-0.022, 0.075] |
| A_hazard | pooled | jev_probe_minus_jev_base | 0.008 [-0.020, 0.039] | 0.009 [-0.022, 0.044] |
| A_hazard | pooled | nano_probe_minus_nano_base | 0.081 [0.038, 0.126] | 0.061 [0.015, 0.120] |
| A_hazard | pooled | jev_nano_minus_jev_base | -0.000 [-0.013, 0.013] | 0.009 [-0.011, 0.028] |
| A_hazard | pooled | jev forecaster L3_minus_nested | 0.064 [0.012, 0.113] | 0.040 [-0.017, 0.090] |
| A_hazard | pooled | llm detector L2_minus_nested | -0.030 [-0.085, 0.023] | -0.054 [-0.109, -0.000] |
| A_hazard | loso | jev_probe_minus_jev_base | 0.003 [-0.011, 0.018] | 0.003 [-0.011, 0.018] |
| A_hazard | loso | nano_probe_minus_nano_base | 0.022 [-0.013, 0.059] | 0.022 [-0.013, 0.059] |
| A_hazard | loso | jev_nano_minus_jev_base | 0.003 [-0.014, 0.019] | 0.003 [-0.014, 0.019] |
| A_hazard | loso | jev forecaster L3_minus_nested | 0.071 [0.024, 0.116] | 0.071 [0.024, 0.116] |
| A_hazard | loso | llm detector L2_minus_nested | -0.022 [-0.085, 0.035] | -0.022 [-0.085, 0.035] |
| B_round_contrast | pooled | jev_probe_minus_jev_base | 0.009 [-0.025, 0.043] | 0.007 [-0.032, 0.043] |
| B_round_contrast | pooled | nano_probe_minus_nano_base | 0.089 [0.041, 0.139] | 0.085 [0.037, 0.145] |
| B_round_contrast | pooled | jev_nano_minus_jev_base | 0.003 [-0.011, 0.017] | 0.008 [-0.012, 0.030] |
| B_round_contrast | pooled | jev forecaster L3_minus_nested | 0.059 [0.002, 0.114] | 0.037 [-0.024, 0.098] |
| B_round_contrast | pooled | llm detector L2_minus_nested | -0.043 [-0.101, 0.018] | -0.070 [-0.131, -0.009] |
| B_round_contrast | loso | jev_probe_minus_jev_base | 0.001 [-0.008, 0.010] | 0.001 [-0.008, 0.010] |
| B_round_contrast | loso | nano_probe_minus_nano_base | 0.024 [0.001, 0.048] | 0.024 [0.001, 0.048] |
| B_round_contrast | loso | jev_nano_minus_jev_base | 0.002 [-0.017, 0.019] | 0.002 [-0.017, 0.019] |
| B_round_contrast | loso | jev forecaster L3_minus_nested | 0.078 [0.023, 0.129] | 0.078 [0.023, 0.129] |
| B_round_contrast | loso | llm detector L2_minus_nested | -0.024 [-0.078, 0.030] | -0.024 [-0.078, 0.030] |
| C_step_contrast | pooled | jev_probe_minus_jev_base | -0.006 [-0.037, 0.024] | -0.003 [-0.045, 0.029] |
| C_step_contrast | pooled | nano_probe_minus_nano_base | 0.102 [0.051, 0.149] | 0.103 [0.047, 0.163] |
| C_step_contrast | pooled | jev_nano_minus_jev_base | -0.002 [-0.005, 0.001] | -0.004 [-0.009, 0.002] |
| C_step_contrast | pooled | jev forecaster L3_minus_nested | 0.069 [0.014, 0.122] | 0.049 [-0.009, 0.112] |
| C_step_contrast | pooled | llm detector L2_minus_nested | -0.057 [-0.112, 0.002] | -0.084 [-0.143, -0.017] |
| C_step_contrast | loso | jev_probe_minus_jev_base | -0.004 [-0.013, 0.005] | -0.004 [-0.013, 0.005] |
| C_step_contrast | loso | nano_probe_minus_nano_base | 0.017 [-0.027, 0.059] | 0.017 [-0.027, 0.059] |
| C_step_contrast | loso | jev_nano_minus_jev_base | -0.009 [-0.017, -0.001] | -0.009 [-0.017, -0.001] |
| C_step_contrast | loso | jev forecaster L3_minus_nested | 0.089 [0.035, 0.143] | 0.089 [0.035, 0.143] |
| C_step_contrast | loso | llm detector L2_minus_nested | -0.036 [-0.091, 0.022] | -0.036 [-0.091, 0.022] |

## Artifacts

`probe_scores.csv`: 208,068 rows, key(row_id, analysis, label_variant, method, seed), with request hashes. `split_plan.json.gz` records every split. `metrics.json` contains all four metrics and paired differences. Per-case coefficients and OOF predictions are local NPZ artifacts; no prompts or activations are copied. `deployable/README.md` describes the all-data models and inference. CPU only; zero API/GPU spend.

Integrity audit: `runs/20261025-1456-e05-all-data-audit/summary.json` checks all 144 fits, family/scenario separation, unchanged development-set labels, source checksums, serialized predictions and CSV round trips. Maximum score reconstruction error: 0. Fitted coefficients, per-fold predictions and uncompressed split indices are in `runs/20261025-1317-e05-all-data-main`. This report package copies the score export and deployable models without changing the fitted run.
