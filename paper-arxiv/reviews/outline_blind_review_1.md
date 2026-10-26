# Blind outline review, round 1 (fresh reader; given only OUTLINE_FOR_BLIND_REVIEW.md)

1. **Question.** When one agent pushes another to break its operator's "don't share this secret" rule, can an overseer tell from the target's activations, before it acts, which episode will leak, which round, or which call?

2. **Setup.**
   - There are six synthetic workspace scenarios. In each, a peer agent asks a target (Qwen3-32B or gpt-oss-20b) for an exact-string value the target was told to protect.
   - Matched control peers and solo runs never leak.
   - Linear probes read the residual stream at the last prompt token, plus reasoning tokens on gpt-oss.
   - They are compared with LLM text monitors on the same calls, within the same scenario and round, using leave-one-scenario-out evaluation.
   - Some results are confirmed on fresh, pre-registered test episodes.

3. **Findings.**
   - Per-call leak prediction is high: AUROC 0.95 on Qwen3-32B (dev, exploratory).
   - Confirmed on fresh test episodes: the gpt-oss reasoning probe scores 0.91.
   - Predictability falls with distance from the act: near chance for the eventual outcome, modest for this round or the next (confirmed on Qwen), high for this call.
   - The signal is much weaker one call earlier.
   - Text monitors score well below the probe. On gpt-oss the monitor can't separate leaking calls at all.
   - The probe beats keyword rules and the "file just read" baseline.
   - Only two numbers appeared (0.95, 0.91), although the abstract promises three.

4. **Biggest limitation.**
   - The warning covers only the current call, and with an exact secret an output filter does the same job.
   - The claimed value (paraphrased or encoded leaks) is untested.
   - The per-call result is confirmed for only one probe, with few leaking calls.

5. **Hardest to follow.** "The round-level confirmation on Qwen3-32B uses the label that was fixed in its plan: a complete channel post, or a new file in five scenarios."
   - It comes out of nowhere in Setup.
   - It assumes the reader knows what "round-level confirmation" and "its plan" are.
   - It implies a label different from the leak definition two items earlier, without explaining why.

6. **Terms the reader had to guess.**
   - Jev (the decision model)
   - recruitment (as a technical term)
   - family / families of related episodes
   - within-stratum AUROC
   - plan fixed in advance / frozen
   - pooled CV
   - mean aggregate
   - channel-only label
   - replay fidelity
   - episode-calibrated cutoff
   - alarm cost per episode
   - decision model vs forecasting monitor
   - the three labels (named in §2.3 but never stated)
   - development episodes

7. **Lost track of which result a number belongs to.**
   - "AUROC 0.95 on Qwen3-32B" sits right next to "On gpt-oss-20b, a probe on the call's reasoning keeps this ranking on fresh test episodes (0.91)". The phrase "keeps this ranking" implies the same probe was re-tested.
   - §4.1 item 2 gives no number.

8. **Score: 3/5.** The prose is plain and the "nearer the act" framing is clear.
   - Main fix: an early small table or figure (model × prediction distance × dev/test, probe vs monitor), so every number has an obvious home.
   - Also define Jev, and the plan or pre-registration, at first mention.
   - Minor: "## 6. Appendix" is duplicated and numbered the same as Discussion.
