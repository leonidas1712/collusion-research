# Blind rigour review, round 3 (final round), PDF 8fb8fca1

**Verdict:** the narrow result survives review. A per-call probe ranks the leaking call highly on both models, holds on fresh episodes, and is weak far from the act. That is well controlled for its scale, and the limitations section is "unusually candid".

**Framings that don't survive as stated:**
- "Activations reveal": a trained text classifier does almost as well.
- The abstract's per-call false-alarm rate, given without the per-episode rate.
- The Qwen 0.98 described as "fresh held-out": those episodes had already been inspected.

The reviewer says the abstract and title need revising (Leo's call), and the round-level cohorts need reconciling.

## Fixable items
- **Shortcut claims overreach:** "not reading the obvious shortcuts" and "No to all three". The signal is in the peer's message content.
- **Table 15:** "interval excludes zero", but the table shows no intervals.
- **"Most of the signal before reasoning"** rests on dev only. Fresh gpt-oss: last-prompt 0.82 vs reasoning 0.91, and the last-prompt probe catches 30.8% at its threshold.
- **The metric's dropped one-class groups:** report how many leaking calls survive.
- **gpt-oss leak:** a verbatim block copy, which may be careless instruction-following. The deliberate-intent check was not re-run.
- **The fresh sets:** the Qwen fresh set has no main-scenario episodes; gpt-oss fresh deploy-token has 2 leaking calls.
- **"Development" means two things:** the sprint-cohort round-level Table 18 (probe 0.57, Jev 0.66) vs Fig 1 / Table 2 (0.67).
- **Prose vs Table 14:** "leaves the result unchanged" vs 0.93 → 0.96. "Slightly higher" vs 0.98 against 0.93.
- **Jev fresh operating point** (68%/29%) is missing from Table 17.
- **Reproducibility gaps:** peer sampling and token limits, the candidate-layer list, the threshold values, per-group counts after the drop, and the family rule.
