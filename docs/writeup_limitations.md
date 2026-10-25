# Write-up: limitations and caveats to report

A running list for the appendix and limitations section. Add an item whenever one comes up, with its source.

## Data

- **Scenario imbalance.** deploy-token v2 is the development scenario: 61 recruiting episodes run, 47 scored. The five spray scenarios were filled to ~45–55 run each by the balanced batch on 25 Oct; after the validity checks they have fewer scored episodes. Report a per-scenario table of episodes run, scored, gave in and deliberate/accidental, and report a balanced-weight AUROC (the mean of per-scenario AUROCs) next to the pooled one. Sources: EXPERIMENT_LOG 25 Oct 10:20, 11:15, 11:35.
- **Uneven drop-out.** In the balanced batch, procurement scored 15/30 and rollout 15/24; the other three scenarios scored 18–21 of 22–26. Reasons: the target never read the secret (10), API errors ended the episode early (8), setup not ready (6). These are the same validity rules for every scenario. State that drop-out is uneven and could bias those scenarios towards targets that engage with the file.
- **One template.** All six scenarios share one task structure. The hybrid code-review check (out of template) was skipped (Leo, 25 Oct).
- **Accidental leaks** (the secret pasted inside a refusal) count as giving in. About a quarter of leaks are accidental. Deliberate-only analysis is a sensitivity check.
- **One flagged episode:** rollout recruiting ep0019, round 11 ("even as part of a test"). Check by hand.

## Methods

- **LLM judge prompt:** ControlArena default format, with anchors only at the ends of the score. Not a banded rubric.
- **Monitor selection:** Jev L3 was named best after seeing results on the original 4,184 steps. On the balanced new episodes the 8-setup subset was fixed in advance, so it is an out-of-sample check of that choice.
- **Fold mixing:** the pooled-CV within-round metric compares scores across fitted folds; the scenario baselines fall below chance. We report the fold × scenario × round sensitivity. LOSO is unaffected.
- **Only last-token activations** were saved. Peer-message token positions were not replayed.
- **Near-term labels are post hoc,** defined on 25 Oct after the eventual-label result.
- **The forecaster prompt** asks about "any later point", yet tracks near-term risk better.
