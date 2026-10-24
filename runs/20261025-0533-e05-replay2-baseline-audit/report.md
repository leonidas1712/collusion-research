# Post-hoc baseline audit

All scenario-only scores exactly reconstruct from unique training episodes. There is no test-label input to those scores. Both scenario-only and scenario + round baselines score exactly 0.5 when comparisons are additionally confined to the same fitted fold (among comparable strata).

Their below-chance values under the predeclared CV metric arise when comparing scores from different fitted folds within a scenario and round. For example, a training scenario rate is the rate in the complement of the held-out fold: held-out folds with more positives can receive lower training-rate predictions. LOSO has one fitted model per held-out scenario per seed and its within-scenario × round baselines are exactly 0.5.

This is a post-hoc diagnostic, not a replacement metric. No probe was refit or re-evaluated under the additional stratification, and the primary estimates are unchanged. Pooled out-of-fold scores can reflect cross-model calibration shifts; comparisons against these below-chance CV baselines should not be treated as evidence of robust added value. The v2 shuffled-label score is also below chance under the original metric; its family interval conditions on the three frozen label shuffles and fits, not on a new permutation experiment.
