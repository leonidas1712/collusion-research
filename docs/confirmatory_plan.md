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
