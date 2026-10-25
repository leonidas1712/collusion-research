# Write-up: limitations and caveats to report

A running list for the appendix and limitations section. Add an item whenever one comes up, with its source.

## Data

- **Scenario imbalance.** deploy-token v2 is the development scenario: 61 recruiting episodes run, 47 scored. The five spray scenarios were filled to ~45–55 run each by the balanced batch on 25 Oct; after the validity checks they have fewer scored episodes. Report a per-scenario table of episodes run, scored, gave in and deliberate/accidental, and report a balanced-weight AUROC (the mean of per-scenario AUROCs) next to the pooled one. Sources: EXPERIMENT_LOG 25 Oct 08:17, 08:30, 08:36.
- **Uneven drop-out.** In the balanced batch, procurement scored 15/30 and rollout 15/24; the other three scenarios scored 18–21 of 22–26. Reasons: the target never read the secret (10), API errors ended the episode early (8), setup not ready (6). These are the same validity rules for every scenario. State that drop-out is uneven and could bias those scenarios towards targets that engage with the file.
- **One template.** All six scenarios share one task structure. The hybrid code-review check (out of template) was skipped (25 Oct).
- **Accidental leaks** (the secret pasted inside a refusal) count as giving in. About a quarter of leaks are accidental. Deliberate-only analysis is a sensitivity check.
- **One flagged episode:** rollout recruiting ep0019, round 11 ("even as part of a test"). Check by hand.

## Methods

- **LLM judge prompt:** ControlArena default format, with anchors only at the ends of the score. Not a banded rubric.
- **Monitor selection:** Jev L3 was named best after seeing results on the original 4,184 steps. On the balanced new episodes the 8-setup subset was fixed in advance, so it is an out-of-sample check of that choice.
- **Fold mixing:** the pooled-CV within-round metric compares scores across fitted folds; the scenario baselines fall below chance. We report the fold × scenario × round sensitivity. LOSO is unaffected.
- **Only last-token activations** were saved. Peer-message token positions were not replayed.
- **Near-term labels are post hoc,** defined on 25 Oct after the eventual-label result.
- **The forecaster prompt** asks about "any later point", yet tracks near-term risk better.
- **Stacking leak (replay-2 combination test):** the stacker's training rows use out-of-fold probe scores from probes that saw the test fold's labels. That tilts slightly towards "the probe adds value", plausibly ~0.01 (estimate, 25 Oct). The GPT-5-nano + probe gains are +0.05 to +0.08, but the lower CI bounds for B and C on held-out scenarios are +0.004 and +0.007, so those two are borderline. The frozen confirmation test has no such leak; nested stacking is the fallback if it is borderline.

## Scoring window: only steps after the secret is read and before the leak (methods + limitations)

- **Methods sentence:** we score every method only on steps where the secret is already in the target's context and it has not yet leaked. A step before the read cannot leak, and including those steps would let a method score well just by detecting that the file was read; a probe does this perfectly, with an exposure check AUROC of 1.000. Steps after the leak are detection after the fact. Probes are trained on the same window, and monitors were run on the same steps.
- **Coverage (combined data):** 6,404 of 9,138 replayed steps are in the window. Of 320 recruiting episodes:
  - 5 of 109 give-ins have no step in the window, because the target leaked on the call right after reading;
  - 74 of 211 held episodes never read the secret.
  - Neither group contributes to training or scoring.
- **Limitation:** an instant give-in like this cannot be predicted from within the episode by any method.
- **Future work:**
  - Influence before exposure, such as tone shifting from "I can't help" to "sure, let me help". This needs its own label, for example a judged "stance" per turn.
  - Recruitment towards side tasks unrelated to the secret.
  - Prediction from the peer's messages alone, before the target has read anything.
- **Not knowing when the means arrived.** Here the secret arrives one known way, a file read, so the window can be defined exactly. In real deployments the means may come through search, command output or messages, and a general monitor has to judge "is it being swayed into acting against policy?" without knowing when that happened. Future work could train and score on all steps without the exposure filter. The shortcut could be checked with no-pressure controls that see the same secret: a probe that only detects "has the secret" fires on those too. The way the information arrives could also be varied. On AUROC: it rewards ranking, so a probe that only detects "read or not" would rank well on mixed steps while alarming on every held episode after the read. That is one more reason to report alarm rates alongside AUROC.
