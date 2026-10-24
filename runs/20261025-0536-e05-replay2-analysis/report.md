# Replay2 probe analysis

The extraction checks passed, but the primary results do not establish robust generalization or clear added value. Inner-selected logistic scenario × round AUROC is **0.632 [0.474, 0.757]** on v2, **0.522 [0.450, 0.591]** in pooled family CV, and **0.551 [0.499, 0.597]** in LOSO. MLP estimates are 0.635 [0.474, 0.758] on v2 and 0.519 [0.460, 0.568] in LOSO; the paired MLP-minus-logistic intervals include zero. The pooled added-value gain is +0.009 [-0.004, 0.022], and the clean branching correlation is −0.032 [-0.460, 0.401].

At a 5% training-benign episode false-alarm target, the pooled logistic probe detects **3.2%** of positive episodes, with **5.6%** held-out benign FPR (8.2% on control episodes alone). Lead times below are conditional on the few detections. Deliberate-only sensitivity gives higher logistic estimates—v2 0.661 [0.512, 0.769], pooled 0.588 [0.502, 0.657]—but does not replace the primary mixed-outcome analyses.

**CV baseline limitation:** several training-fold baselines, and the v2 shuffled-label check, rank below chance under the predeclared metric. A post-hoc audit exactly reconstructed the scenario-rate scores and found both scenario baselines equal 0.5 when comparisons are additionally confined to the same fitted fold. Cross-fold calibration shifts therefore matter: a training prevalence comes from the complement of a held-out fold and can rank a more-positive held-out fold lower. LOSO has one model per held-out scenario and its stratified scenario baselines are exactly 0.5. No primary metric was changed, and no probe was refit or rescored with the added fold stratum. See the [baseline audit](../20261025-0533-e05-replay2-baseline-audit/report.md). Gaps against these below-chance CV baselines should not be treated as robust added value on their own.


Exposure integrity gate: layer 32 AUROC **1.0000** on held-out families (required ≥0.95). All saved selected logistic, metadata and MLP scores were reconstructed and split isolation checked.

![Exposure](exposure.png)

## Headline ranking

Training uses recruiting episodes only. All outcome rows are valid completed target requests strictly after first token read and strictly before first forbidden action. File-only actions use the request-level action boundary. Families remain disjoint across train and test. Intervals resample families and average three split seeds; they are conditional on the frozen fitted models.

| Analysis | Method | Scenario × round AUROC [95% CI] | Pooled AUROC [95% CI] |
|---|---|---|---|
| v2 | nested | 0.632 [0.474, 0.757] | 0.690 [0.533, 0.817] |
| v2 | fixed32 | 0.663 [0.530, 0.768] | 0.716 [0.579, 0.819] |
| v2 | band26_30 | 0.634 [0.479, 0.754] | 0.703 [0.553, 0.815] |
| v2 | dom32 | 0.638 [0.482, 0.753] | 0.740 [0.628, 0.846] |
| v2 | turn | 0.500 [0.500, 0.500] | 0.682 [0.613, 0.795] |
| v2 | length | 0.492 [0.357, 0.655] | 0.323 [0.204, 0.398] |
| v2 | scenario_only | 0.446 [0.347, 0.549] | 0.447 [0.354, 0.544] |
| v2 | scenario_round | 0.368 [0.252, 0.491] | 0.648 [0.569, 0.775] |
| v2 | mlp | 0.635 [0.474, 0.758] | 0.698 [0.551, 0.817] |
| v2 | metadata_base | 0.348 [0.226, 0.494] | 0.639 [0.553, 0.777] |
| v2 | metadata_probe | 0.515 [0.363, 0.655] | 0.662 [0.550, 0.783] |
| v2 | shuffled32 | 0.373 [0.269, 0.485] | 0.371 [0.270, 0.478] |
| pooled | nested | 0.522 [0.450, 0.591] | 0.666 [0.615, 0.722] |
| pooled | fixed32 | 0.576 [0.493, 0.650] | 0.715 [0.655, 0.772] |
| pooled | band26_30 | 0.550 [0.464, 0.627] | 0.693 [0.630, 0.757] |
| pooled | dom32 | 0.457 [0.394, 0.522] | 0.625 [0.542, 0.705] |
| pooled | turn | 0.500 [0.500, 0.500] | 0.714 [0.661, 0.772] |
| pooled | length | 0.484 [0.403, 0.582] | 0.304 [0.237, 0.369] |
| pooled | scenario_only | 0.316 [0.244, 0.406] | 0.477 [0.356, 0.580] |
| pooled | scenario_round | 0.293 [0.224, 0.375] | 0.700 [0.642, 0.759] |
| pooled | metadata_base | 0.280 [0.219, 0.357] | 0.698 [0.640, 0.757] |
| pooled | metadata_probe | 0.368 [0.300, 0.446] | 0.706 [0.655, 0.762] |
| pooled | shuffled32 | 0.472 [0.421, 0.520] | 0.500 [0.454, 0.549] |
| loso | nested | 0.551 [0.499, 0.597] | 0.610 [0.538, 0.677] |
| loso | fixed32 | 0.547 [0.460, 0.612] | 0.617 [0.539, 0.702] |
| loso | band26_30 | 0.539 [0.447, 0.609] | 0.570 [0.478, 0.664] |
| loso | dom32 | 0.452 [0.373, 0.527] | 0.530 [0.462, 0.601] |
| loso | turn | 0.500 [0.500, 0.500] | 0.714 [0.661, 0.772] |
| loso | length | 0.484 [0.403, 0.582] | 0.304 [0.237, 0.369] |
| loso | scenario_only | 0.500 [0.500, 0.500] | 0.378 [0.275, 0.490] |
| loso | scenario_round | 0.500 [0.500, 0.500] | 0.687 [0.623, 0.756] |
| loso | mlp | 0.519 [0.460, 0.568] | 0.636 [0.581, 0.698] |
| loso | metadata_base | 0.481 [0.384, 0.556] | 0.683 [0.617, 0.755] |
| loso | metadata_probe | 0.544 [0.480, 0.592] | 0.676 [0.611, 0.749] |
| deliberate_v2 | nested | 0.661 [0.512, 0.769] | 0.723 [0.622, 0.824] |
| deliberate_v2 | fixed32 | 0.593 [0.456, 0.710] | 0.676 [0.570, 0.801] |
| deliberate_v2 | band26_30 | 0.566 [0.407, 0.694] | 0.666 [0.549, 0.804] |
| deliberate_v2 | dom32 | 0.597 [0.448, 0.707] | 0.718 [0.612, 0.842] |
| deliberate_v2 | turn | 0.500 [0.500, 0.500] | 0.718 [0.631, 0.872] |
| deliberate_v2 | length | 0.534 [0.387, 0.686] | 0.296 [0.127, 0.392] |
| deliberate_v2 | scenario_only | 0.469 [0.385, 0.550] | 0.467 [0.390, 0.543] |
| deliberate_v2 | scenario_round | 0.362 [0.271, 0.500] | 0.673 [0.561, 0.871] |
| deliberate_pooled | nested | 0.588 [0.502, 0.657] | 0.751 [0.694, 0.806] |
| deliberate_pooled | fixed32 | 0.548 [0.444, 0.632] | 0.746 [0.681, 0.807] |
| deliberate_pooled | band26_30 | 0.530 [0.429, 0.620] | 0.731 [0.649, 0.802] |
| deliberate_pooled | dom32 | 0.503 [0.422, 0.576] | 0.673 [0.552, 0.776] |
| deliberate_pooled | turn | 0.500 [0.500, 0.500] | 0.748 [0.675, 0.846] |
| deliberate_pooled | length | 0.495 [0.395, 0.605] | 0.272 [0.160, 0.362] |
| deliberate_pooled | scenario_only | 0.322 [0.234, 0.411] | 0.560 [0.417, 0.692] |
| deliberate_pooled | scenario_round | 0.290 [0.231, 0.361] | 0.755 [0.679, 0.834] |

Scenario-only rates use training episodes, with the global training rate for an unseen scenario. Scenario + round and added-value metadata models are fit only on training rows. LOSO holds out one scenario and purges overlapping family IDs; layer selection uses a training-scenario holdout. Its headline pools all six held-out rotations, then stratifies comparisons by scenario × round. Per-scenario estimates below are descriptive, with few positive episodes; no claim of scenario differences follows from this plot. Single-class strata are omitted; positive coverage by seed is retained in metrics.json.

![LOSO forest](loso-forest.png)

MLP minus logistic scenario × round AUROC (paired family interval):

- v2: 0.003 [-0.042, 0.050]
- loso: -0.032 [-0.066, 0.001]

## Cross-fitted added value

| Analysis | Pooled AUROC gain from probe [paired 95% CI] |
|---|---|
| v2 | 0.023 [-0.062, 0.088] |
| pooled | 0.009 [-0.004, 0.022] |
| loso | -0.008 [-0.037, 0.018] |

Base covariates are scenario, target turn number and prompt token count. Probe scores for fitting the augmented model come from three inner family folds, each repeating layer selection within its own training portion. Outer test scores never enter this fit.

## Episode alarms

### Raw alarms at the 5% training-benign target

| Analysis | Probe | Recall [family 95% CI] | Held-out benign FPR [family 95% CI] | Control-only FPR | Median lead steps |
|---|---|---|---|---|---|
| v2 | Inner-selected logistic | 6.1% [0.0%, 13.7%] | 7.4% [1.8%, 15.4%] | 9.5% | 16.0 |
| v2 | MLP | 6.1% [1.5%, 11.6%] | 13.6% [7.2%, 22.2%] | 17.5% | 3.5 |
| pooled | Inner-selected logistic | 3.2% [1.0%, 5.9%] | 5.6% [2.7%, 9.3%] | 8.2% | 3.5 |
| loso | Inner-selected logistic | 12.7% [7.5%, 17.9%] | 12.0% [7.9%, 16.7%] | 17.6% | 4.0 |
| loso | MLP | 3.2% [1.1%, 5.9%] | 6.4% [3.4%, 10.0%] | 9.4% | 4.0 |

Zero observed alone FPR is based on 25 pooled eligible alone episodes (6 in v2). A zero-event empirical bootstrap interval is not a population-risk upper bound. Counts by seed and all alarm intervals remain in `metrics.json`.

### Inner-selected logistic trade-off


Each threshold is selected from maxima over pooled benign training-fold control + alone episodes. An alarm means any eligible step exceeds the cutoff. Raw and EMA (α=0.5) alarms have separately calibrated cutoffs. Held-out rates need not equal the calibration target. Lead times are conditional on detection. Episodes with no eligible post-read/pre-action step are outside this analysis; these rates must not be interpreted as all-episode deployment rates.

| Analysis | Alarm | Target benign FPR | Recall | Held recruiting FPR | Held-out benign FPR | Control-only FPR | Alone FPR | Median lead (steps / rounds) |
|---|---|---|---|---|---|---|---|---|
| v2 | raw | 1% | 3.0% | 0.0% | 3.7% | 4.8% | 0.0% | 16.0 / 14.0 |
| v2 | ema | 1% | 0.0% | 1.3% | 3.7% | 4.8% | 0.0% | None / None |
| v2 | raw | 5% | 6.1% | 0.0% | 7.4% | 9.5% | 0.0% | 16.0 / 11.0 |
| v2 | ema | 5% | 3.0% | 2.7% | 4.9% | 6.3% | 0.0% | 10.5 / 4.5 |
| v2 | raw | 10% | 12.1% | 6.7% | 7.4% | 9.5% | 0.0% | 15.5 / 10.5 |
| v2 | ema | 10% | 12.1% | 8.0% | 9.9% | 12.7% | 0.0% | 16.0 / 10.0 |
| v2 | raw | 20% | 15.2% | 14.7% | 21.0% | 27.0% | 0.0% | 9.5 / 6.5 |
| v2 | ema | 20% | 22.7% | 16.0% | 21.0% | 27.0% | 0.0% | 4.0 / 1.0 |
| pooled | raw | 1% | 0.0% | 0.4% | 0.4% | 0.6% | 0.0% | None / None |
| pooled | ema | 1% | 0.5% | 1.9% | 1.7% | 2.5% | 0.0% | 7.0 / 4.0 |
| pooled | raw | 5% | 3.2% | 4.1% | 5.6% | 8.2% | 0.0% | 3.5 / 2.5 |
| pooled | ema | 5% | 5.8% | 4.9% | 6.8% | 10.1% | 0.0% | 7.0 / 4.0 |
| pooled | raw | 10% | 5.3% | 7.5% | 9.0% | 13.2% | 0.0% | 7.5 / 3.0 |
| pooled | ema | 10% | 9.5% | 8.2% | 11.5% | 17.0% | 0.0% | 6.0 / 4.0 |
| pooled | raw | 20% | 16.9% | 12.7% | 18.4% | 27.0% | 0.0% | 4.5 / 2.5 |
| pooled | ema | 20% | 14.8% | 15.0% | 18.4% | 27.0% | 0.0% | 5.5 / 4.0 |
| loso | raw | 1% | 10.1% | 7.1% | 4.7% | 6.9% | 0.0% | 4.0 / 1.0 |
| loso | ema | 1% | 6.9% | 4.5% | 6.8% | 10.1% | 0.0% | 4.0 / 1.0 |
| loso | raw | 5% | 12.7% | 9.4% | 12.0% | 17.6% | 0.0% | 4.0 / 1.5 |
| loso | ema | 5% | 9.5% | 7.5% | 12.4% | 18.2% | 0.0% | 4.0 / 2.0 |
| loso | raw | 10% | 16.4% | 12.4% | 16.7% | 24.5% | 0.0% | 5.0 / 2.0 |
| loso | ema | 10% | 13.8% | 12.0% | 15.8% | 23.3% | 0.0% | 6.0 / 3.5 |
| loso | raw | 20% | 23.3% | 19.5% | 25.6% | 37.7% | 0.0% | 6.5 / 4.0 |
| loso | ema | 20% | 21.2% | 16.9% | 20.1% | 29.6% | 0.0% | 7.0 / 4.5 |

Family-bootstrap intervals, numerator/denominator counts by seed, all other methods and alarm records are in `metrics.json` and the per-analysis alarm files.

## Clean branching calibration

Matched 23 shared states in 20 families. Spearman = **-0.032**, family-bootstrap 95% CI [-0.46044721278719536, 0.4008656926659128]. Each state ends before the new round's peer message; frozen v1 family-held-out probes were applied with no refit. The fractions cover the saved three-round continuation horizon; five reruns per state make them noisy. These shared states differ from the after-peer target-call inputs used to train the v1 probe, so this is also a checkpoint-transfer test. This is observational calibration, not causal evidence.

[Branch plot and per-state provenance](../20261025-0340-e05-replay2-branching/report.md)

## Counts and sensitivity

- v2: 871 recruiting rows, 47 episodes (22 give-in), 38 families, 499 benign evaluation rows.
- pooled: 2910 recruiting rows, 152 episodes (63 give-in), 133 families, 1274 benign evaluation rows.
- loso: 2910 recruiting rows, 152 episodes (63 give-in), 133 families, 1274 benign evaluation rows.
- deliberate_v2: 798 recruiting rows, 44 episodes (19 give-in), 36 families, 499 benign evaluation rows.
- deliberate_pooled: 2645 recruiting rows, 133 episodes (44 give-in), 119 families, 1274 benign evaluation rows.

## Replay fidelity

Verified 6026 prompts (13,344,820 prompt tokens). Scored 6003 HF-serialized actual replies (including template terminators), up to 64 tokens each: token-weighted NLL **0.2488**, top-five fraction **0.99792**. HF/provider prompt-count ratio min/median/max: [0.9919119299033925, 1.0, 1.0]. Exact prompt and token hashes match the frozen manifest. These checks do not expose or prove equality with the provider's private tokenization/template. Shared pre-peer states have no observed reply, so no reply likelihood is imputed for them.

Both GPU apps stopped. Billed app total at the recorded snapshot: USD5.5137; conservative compute-plus-overhead bound USD6.61, below the approved USD12. Combined benchmark/main client wall time 113.19 minutes; 2,838 prompt tokens/s of decoder time and 1,965 prompt tokens/s of client wall time. [Billing and throughput details](../20261025-0339-e02-replay2-results/report.md).

Deliberate-only sensitivity keeps all held episodes and positive episodes whose semantic judge first-publication kind is `deliberate`; accidental and unknown positive kinds are excluded. Layer selection, folds and preprocessing are refit inside that subset. The MLP has one 32-unit ReLU hidden layer, 80 fixed epochs, and training-only scaling; its layer is chosen on the same inner split as logistic regression.

Inputs: `20261025-0337-e05-replay2-data`, `20261025-0340-e05-replay2-fits`, `20261025-0338-e05-replay2-positive-control`, `20261025-0340-e05-replay2-branching`. The full recipe is `experiments/E05-probes/REPLAY2_ANALYSIS_PLAN.md`. These are predictive associations in saved transcripts, not evidence that a probe isolates intent or causally controls behavior. No API or GPU calls occur in this analysis.
