# Blind rigour review of the draft PDF, round 2

PDF a417aaa5. **Verdict:** the core result holds up by the norms of comparable probe-monitoring papers. Nothing is headline-changing. **Four important framing fixes** would make it "a solid workshop paper":

1. **"Beats a text monitor" rests on a zero-shot baseline.** A trained bag-of-words classifier nearly matches the probe (Qwen 0.93 vs 0.96; gpt-oss 0.84/0.86 vs 0.91).
2. **The Qwen fresh 0.98 is not a blind confirmation.** The intro says "fresh episodes it never saw", but the analyst had already inspected those episodes.
3. **Per-episode false alarms are missing next to "pauses an agent just before it gives in".** At least one alarm fires in 59% of refusing Qwen fresh episodes and 26% on gpt-oss. These figures appear only in appendix Table 16.
4. **Don't read the signal as a decision forming.** The incoming-only probe (0.93) and the early chosen layers point as much to it reading the input.

## Other items
- The placebo is scored on the "ever" label, so it cannot rule out request or input detection.
- The metric drops single-class scenario × round groups. This should be stated.
- Chosen layers: early on gpt-oss (6, 6, 13) and unstable on Qwen (48, 16, 48). Not discussed.
- Excluded-episode counts are not reported. There is also no pre-registration commit or timestamp, and no per-scenario call counts for the fresh sets.
- "Pooled" has three meanings across Tables 11, 13 and 19.
- Section E.2 vs Section J: the round-level setups' cohort is unclear. The probe scores 0.67 in Table 2 but 0.57 in Table 17.
- L.2 and P.3 describe the gpt-oss control episodes differently.
- The full-input TF-IDF scores 0.71, against 0.93 for latest-input only. This is unexplained.
- The "flat before the leak" wording is too strong for the gpt-oss curves.
- The reasoning-on screen has only n=8.
