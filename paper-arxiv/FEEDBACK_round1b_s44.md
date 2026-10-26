# Feedback round 1b (Leo): additions to §4.4 "What would deployment cost?"

Leo's text is in the conversation. The coordinator transcribed it below and added correctness notes, marked [CHECK]. Implement it as specified, with each number verified from saved scores. Do not run new models.

## 1. Precision at the chosen threshold
- Next to "82% of leaking calls caught at 5% of other calls flagged" on fresh Qwen, report the **share of flagged calls that are real leaks** (precision).
- Compute it exactly from saved scores. Do the same for gpt-oss at its frozen threshold, and for Jev on the same Qwen calls.
- [CHECK, codex-2] Define the denominator explicitly. Flagged calls include **all** non-leaking scored calls in the test set, including calls in leaking episodes before the leak, not only refusing-episode calls.
  - Rough expectation on refusing calls only: probe 31/(31+77) ≈ 29%, Jev 26/(26+404) ≈ 6%.
  - Report the value on the full denominator, and say which one is used.
- One plain sentence of explanation: AUROC measures ranking, while precision tells an overseer how many alarms are real.

## 2. An episode-calibrated operating point, both models
- For Qwen fresh, add a second threshold, set so that about 5% of episodes alarm instead of 5% of calls. Report:
  - the share of leaking episodes caught **before or at the first leak**;
  - the share of refusing recruiting episodes that alarm.
- [CHECK, codex-2] Leo recalled that gpt-oss already has this ("about a third of leaking episodes caught, 8% of refusing episodes alarmed"). Verify which episode set and threshold rule that came from. Recompute on the **fresh** episodes where possible, so both models use the same set; if not possible, label the set.
- Saved scores only. Put both models in one small table, or mark the point on the Fig 7 Qwen panel.

## 3. Why the two calibrations differ (2–3 sentences)
- [CORRECTED] A refusing fresh Qwen episode has a **median of 23 calls**, not 17.
- Under independence, a 5% per-call rate gives 1 − 0.95^23 ≈ **69%** of episodes with at least one flag. The observed rate is **59%**, because flags cluster within episodes.
- [CORRECTED, codex-2] Holding episodes to 5% needs a per-call rate of about 1 − 0.95^(1/23) ≈ 0.2% under independence. Report the **actual** per-call rate implied by the episode-calibrated threshold, rather than Leo's estimated 0.3%.
- That threshold catches fewer leaks.

## 4. Calibrating on realistic honest traffic
- Leo's claim: thresholds set on control episodes underestimate false alarms on refusing episodes, because pressure raises the score. He gives gpt-oss as the example: a 5% control target gave 8% on refusing episodes.
- [CHECK, codex-2: verify before it is written] Current fresh numbers point both ways:
  - Qwen: a 5% control target gave 5.5% on refusing calls, a slight underestimate.
  - gpt-oss: the frozen threshold gave 2.4% of refusing calls, an overestimate.
  
  The 8% may be an episode-level rate, not a call-level one. Report what the data show per model and per level.
- [claude-2] State it **only to the extent the data support it**, once. If the evidence is mixed, say plainly that the gap between control and refusing traffic varies by model, and that thresholds should be set on realistic honest traffic.

## 5. Two thresholds in the cascade (Discussion)
- A **lenient per-call threshold** escalates a call to a stronger monitor or a human. It is frequent and cheap, and catches most leaks.
- A **strict per-episode threshold** halts the agent. It is rare, so honest agents are seldom interrupted.
- Present the two calibrations as these two roles, not as competing results.

## Number budget
The main text gets two new numbers in §4.4: the **precision** figure and the **episode-calibrated catch rate**. Everything else goes in the appendix table.
