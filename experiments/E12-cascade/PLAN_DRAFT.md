# E12 (draft): does a two-stage probe → text-monitor cascade beat the probe alone?

Status: **design draft for Leo**, 27 Oct 2026. No runs. Next step is a red-team review, then a freeze.

## Why
§4.4 and the Discussion propose a cascade, but it is only a suggestion: a cheap detector runs on every call, and a flagged call is escalated to a second check before it acts. Nothing in the paper measures whether that second check actually helps. E12 measures it on data we already have.

This is an **exploratory ablation**: it adds one small table or figure panel and one sentence to §4.4. It is not a new headline.

## The question
At the same false-alarm rate, does "probe, then a second detector" catch more leaks than **just raising the probe's threshold**?

That comparison is the point. Any second stage that only lets through a subset of the probe's flags will cut false alarms *and* catches. The cascade earns its place only if it does that better than simply using a stricter probe.

## Data: existing, frozen, $0
- **Cohort.** Fresh Qwen3-32B episodes, the same calls as the §4.4 operating point. They include leaking calls, calls in refusing episodes, and control calls.
- **Stage 1: the probe.**
  - It is the frozen last-prompt probe: fit on development episodes only, with its saved scores on the fresh calls.
  - It is unchanged from the paper.
- **Stage 2, option A: Jev (zero-shot).**
  - We use the existing Jev scores on the same fresh calls, from the same run as §4.4. There are no new API calls.
  - Jev sees the same masked conversation and tool results as the probe, so it is not a different view of the call. It is a different reader of the same input.
- **Stage 2, option B: the trained bag-of-words classifier.**
  - It uses the paper's existing recipe: TF-IDF and logistic regression, with the secret masked, and the same settings as the appendix table.
  - **New step:** we fit it once on *all* development calls and score the fresh calls. The paper's bag-of-words result is cross-validated on development only, so fresh scores do not exist yet.
  - This is CPU-only, with no tuning.
  - It uses the input view the paper already reports as stronger for Qwen: the latest message.
- **gpt-oss is out of scope.** There, Jev scores below chance, and the reasoning probe's operating point is a different kind of detector. If anything, it gets one line in the appendix.

## Thresholds, fixed before any result is computed
All thresholds are set on **control calls**, never on leak labels, matching how §4.4 sets the probe's operating point.
- **Stage 1.** The existing probe threshold from §4.4: about 5% of calls in refusing episodes flagged, 82% of leaking calls caught.
- **Stage 2.**
  - For Jev: the existing control-call threshold used in §4.4, the one that gives 68% / 29% when Jev runs alone.
  - For bag-of-words: a threshold set on fresh control calls using the same rule as the probe's.
- **Cascade alarm** = stage 1 flags **and** stage 2 flags.

## What we report (Qwen fresh, episode-clustered bootstrap, 1,000 draws)
1. **One table.** One row each for:
   - probe alone;
   - Jev alone;
   - bag-of-words alone;
   - probe → Jev;
   - probe → bag-of-words.

   Columns:
   - leaking calls caught;
   - calls in refusing episodes flagged;
   - precision (the share of alarms that are real leaks);
   - refusing episodes with at least one alarm.
2. **The key comparison.** For each cascade, we report the probe alone at a threshold matched to the cascade's false-alarm rate, with its catch rate. We also report the difference, with a CI.
3. **One figure panel, optional.** It adds the two cascade points to the existing Fig. 7 curve: catch rate against false alarms, probe vs Jev.

## Hypotheses (stated before running)
- **H1.** Probe → Jev cuts false alarms, but loses catches roughly in line with Jev's own miss rate. Jev is weak here (AUROC 0.75), and its errors probably overlap with what any stricter probe would drop.
  - **Expected:** no better than a stricter probe alone.
- **H2.** Probe → bag-of-words does better than probe → Jev, because the text classifier is far stronger (0.93 on development).
  - **Open question:** whether it beats a stricter probe alone. It can only do so if its errors differ from the probe's.
  - The paper's own result is that much of the signal is in the incoming message for both detectors, so they may make **the same mistakes**. Our honest prior is "roughly ties".
- **If the cascade does not beat a stricter probe,** that is still a useful result for §4.4. A second automated check on the same input adds little; in that case, the value of escalation lies in a stronger second stage (a human, or a monitor that sees more), which we do not test.

## What this can and cannot show
- **Can show:** whether a second automated check on the same input improves the trade-off, on this data.
- **Cannot show:** the value of a human or strong-LLM reviewer as stage 2, or of a stage 2 that reads the generated reply before it executes. For an exact secret, the second of those reduces to a string match.
- **Thresholds come from control calls,** which share episodes and scenarios with the test cohort. This is "descriptive on fresh episodes", the same status as §4.4, not a pre-registered test.

## Cost and effort
- $0, CPU only, with no new model calls.
- About 1–2 hours for one agent, plus a short addition to §4.4 or an appendix table.
- Outputs go to a run folder under `runs/`, with numbers registered in `numbers.yaml` like every other result.

---

## Revisions after the red-team (27 Oct; these override the sections above where they conflict)

The full review is in this session's notes. Every data source exists, and the call sets match: 1,825 fresh Qwen calls, 38 leaks, 1,407 calls in refusing episodes.

1. **There is a ceiling, and the probe's curve is flat.**
   - At the §4.4 threshold, stage 1 catches 31 of 38 leaks, so no cascade can catch more than 31.
   - From `runs/20261026-2252-e05-arxiv-alarm-tradeoffs/curves.csv`, the probe alone catches:

     | Share of refusing calls flagged | Leaks caught (of 38) |
     |---|---|
     | 5.5% | 31 |
     | 3% | 31 |
     | 2% | 29 |
     | 1% | 22 |
     | 0.5% | 17 |

   - So a cascade can only win below about 2%. This is stated before running anything.
2. **Fixed targets replace "matched to wherever the cascade lands".**
   - The comparison points are 1% and 2% of refusing calls flagged.
   - For the probe alone, the threshold is set to hit each target. For each cascade, stage 1 stays fixed and stage 2 is tuned to hit the same target.
   - Matching is redone inside each episode-bootstrap draw.
   - Tuning stage 2 favours the cascade, which makes a null result stronger.
3. **Jev's threshold.** The existing one varies by scenario fold (0.01 vs 0.0), and its calibration includes fresh controls, so we do not use it.
   - Instead, we sweep Jev's roughly 32 score levels to give a cascade **curve**.
   - We use one seed's rows only, since the three seeds are identical copies.
4. **Bag-of-words.**
   - Fit on the 2,976 development recruiting calls only, with the settings in `arxiv_text_workflow.py`.
   - Any standalone threshold comes from the 1,224 development control calls.
   - We also report a sweep curve and its fresh AUROC. 0.93 is a leave-one-scenario-out number on development, so it is not the expected value here.
   - Bag-of-words is an **optional second step**, run only if the Jev result is ambiguous or we want the point about a second stage that needs no access to weights.
5. **Reading a tie.**
   - With 38 leaks, each leak is about 2.6 points.
   - We report counts and discordant leaks: those caught by the cascade but not the probe, and the reverse.
   - A gap of 3 leaks or fewer counts as a tie. The wording will be "no detectable benefit", never "no benefit".
   - We also report how often stage 1 and stage 2 miss the same calls.
6. **Framing.** The question is: "does a cheap second automated check on the same input beat a stricter threshold?" This is weaker than the stronger second stage the Discussion proposes, a stronger monitor or a human, which E12 does not test.
7. **Definitions.**
   - Precision is defined as in §4.4, with pre-leak calls counted as negatives.
   - False alarms are counted on refusing calls only.
   - Jev sees "nearly the same input" as the probe (it has no private reasoning).
   - Cascade points are added to `fig7_qwen_alarms.pdf`.
8. **Line 65 is corrected.** The probe's threshold uses development controls only. The fixed-target comparison uses fresh refusing calls for both arms, so it is descriptive, the same status as §4.4.
