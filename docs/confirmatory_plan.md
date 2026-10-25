# Confirmatory test on the balanced-batch episodes (frozen before analysis)

Written 25 Oct 2026, ~09:05 SGT. It must be committed before any near-term grading of the new episodes. When it was written:

- replay 3 (codex-3) was still running on Modal;
- the 8-setup monitor subset on the new episodes was still running, and its scores had not been graded against any label;
- nothing from the new episodes had been looked at except episode-level outcome counts (`EXPERIMENT_LOG.md`, 08:30–08:36).

## Why

We defined the near-term labels after seeing the eventual-label result, so on the replay-2 data they are exploratory. The 129 balanced-batch episodes (`runs/20261025-0817-e01-spray-*`) are new episodes from the same five spray scenarios that no model or choice has touched. Fixing every choice now, training only on replay 2 and testing only on the new episodes, turns the near-term result into a confirmatory test.

## Fixed choices

- **Primary label: near-term A (hazard).** A step is 1 if the first forbidden action comes in this round or the next (`action_round − round ∈ {0, 1}`); otherwise 0. That includes earlier steps of episodes that give in later. A is chosen because it is the question a deployed alarm asks and it uses every eligible recruiting step. B (clean contrast) and C (within 3 calls) are secondary.
- **Eligible steps:** the same rules as replay 2: valid episodes; after the first token read; strictly before the first forbidden action; recruiting condition.
- **Probe:**
  - Logistic, the inner-selected layer, the same recipe as codex-2's near-term refit (`experiments/E05-probes/near_term.py`).
  - Trained once on **all replay-2 recruiting rows**, all six scenarios, with the layer chosen by its inner split on replay-2 data only.
  - Applied unchanged to the new episodes. No refit, no retuning.
  - Secondary: the fixed layer-32 version.
- **Monitors:** Jev forecaster L3 (named primary) and GPT-5-nano detector L2. The other six setups of the subset are secondary. Scores are taken as they are; no fitting.
- **Combination:** stacked logistic models fit on replay-2 rows only, then applied to the new episodes:
  - `[round, log length, Jev F L3]` vs `[round, log length, Jev F L3, probe]`;
  - `[round, log length, GPT-5-nano det L2]` vs the same + probe.
- **Metric:** within scenario × round AUROC (E05 `within_round`, stratum = scenario) on the new episodes' eligible recruiting steps. 95% CIs by family bootstrap over the new episodes. Every model here is fitted once, so fold mixing does not arise.
- **Primary comparisons:**
  1. Probe vs 0.5.
  2. Jev F L3 vs probe, as a paired difference.
  3. Gain from adding the probe to each monitor, paired.
- **Success criteria, stated in advance:**
  - (1) the probe's CI lies above 0.5;
  - (3) the gain CI lies above 0 for GPT-5-nano det L2.
  - We expect about 0 for Jev, based on the replay-2 result.
- **Reporting:** all of the above whatever the outcome, together with the replay-2 numbers. Any deviation from this plan is reported as a deviation.

## Not covered

- Alarm metrics on the new data. There are few benign episodes (19), so they go in the appendix only.
- Eventual-label results on the new data: reported, but not part of the confirmatory claim.

## Addendum (25 Oct ~09:20 SGT, before any new-data grading): after the confirmation test

The confirmation test above runs once, exactly as frozen. Afterwards the new episodes join the old ones:

- **Main estimate:** the same family-grouped CV recipe and held-out-scenario (LOSO) recipe, rerun on **all** data (replay 2 + replay 3, ~240 recruiting episodes) for the near-term and eventual labels and for the 8 monitor setups scored on both sets. This gives the headline numbers with the tightest intervals.
- **Deployable probe:** the same recipe trained on everything.

The paper reports both the confirmation result, as the protection against our label choices, and the all-data estimate.

## Addendum 2 (25 Oct ~09:20 SGT, before replay 3 has landed): implementation details

These fill gaps in the plan above. Nothing from the new data has been seen.

- **Probe seeds:** the "trained once" probe is three models, one per split seed (42/43/44). Each chooses its layer on its own inner family split (25% of replay-2 recruiting families) and is then fit on all replay-2 recruiting rows. The **primary score is the mean of the three models' scores**. Seed 42 alone is reported as a check.
- **Stacker inputs:** the stacker's training rows use the replay-2 out-of-fold near-term probe scores (`runs/20261025-0730-e05-near-term/probe_scores.csv`, pooled, nested, seed mean). New-episode rows use the final probe's scores. The difference in scale between fold models and the final model is a known limitation of this simple stacking.
- **Monitor scores:** replay-2 rows from `runs/20261025-0147-e06-monitor-main`; new rows from `runs/20261025-0841-e06-monitor-main-balanced`. Same prompts, same models.
- **CIs:** family bootstrap over the new episodes' families, 1,000 resamples, seed 20261025.

## Addendum 3 (25 Oct ~09:30 SGT, after a dry run on replay-2 families only; replay 3 has still not landed)

The dry run treated 25% of the replay-2 families as "new" and never touched the confirmation set. It showed that the three seed models choose very different layers (4, 60, 63), and their raw scores sit on very different scales, so a plain mean is dominated by one model. Fix: before averaging, each seed model's scores are z-scored against that model's own training-row scores (mean and SD). This uses no test information. Everything else is unchanged. Note that the CIs will be wide: the dry run's 31 episodes gave ±0.2. The real set has ~129 episodes.

## Addendum 4 (25 Oct ~09:35 SGT, still before replay 3 has landed): common probe scale for the stacker

A side review pointed out that the stacker learns its probe weight from replay-2 out-of-fold scores, which come from fold models, but is applied to scores from the final model, so the two can sit on different scales. Fix, which replaces the z-scoring in addendum 3:

- each out-of-fold (seed, fold) model's scores are z-scored over the rows that model scored;
- each final seed model's scores are z-scored over the new rows it scores. This uses no labels.

In both cases the three seeds are then averaged. In the dry run the two now match: SD 0.80 vs 0.80, means ≈0. The probe-alone AUROC is unaffected, since z-scoring doesn't change rankings within a model.

## Addendum 5 (25 Oct ~10:15 SGT, before any replay-3 outcome analysis): one extra secondary hypothesis

The replay-2 per-layer diagnostic (`runs/20261025-1003-e05-layer-diagnostic`) shows that for near-term B, the late layers (48–63) sit consistently higher than the middle ones, in both pooled CV and LOSO (~0.63–0.66 vs ~0.55–0.60). That pattern was found by looking at test results, so on replay 2 it is post hoc. Testing it on the confirmation set is clean.

- **Secondary hypothesis (not part of the primary claim):** a "late-band" probe beats chance on the new episodes and scores at least as well as the primary inner-selected probe. The late-band probe fits one logistic probe per layer 48, 52, 56, 60 and 63 on all replay-2 rows (same recipe, seed 42), z-scores each over the new rows, and averages them.
- It is reported alongside the primary result and labelled as a hypothesis from the replay-2 diagnostic. It does not replace the primary probe.
