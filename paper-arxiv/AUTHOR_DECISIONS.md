# Author decisions for the arXiv rewrite (26 Oct 2026, before the overnight run)

1. **Headline.** The headline figure and the abstract lead with the ladder (predictability rises as the question nears the act), with the per-call probe at the top. The confirmed gpt-oss fresh-episode result is the confirmed anchor.
2. **Per-call leak label.** Unify the per-call question on "any public emission": the secret written into a reply, a channel message, or any file outside the protected one.
   - Keep gpt-oss as is, including its frozen confirmation.
   - Refit and recompute the Qwen per-call results under that label from saved activations, as a new run folder. Log what changed in the analysis history.
   - For the round-level question, keep the pre-registered Qwen confirmation numbers on their original label. Define the round-level label once, in Setup or the appendix, and do not mention it in the main text beyond that.
3. **Compute.** Modal GPU spend up to $10 in total, only if a recomputation needs re-extracting activations. Everything else is CPU from saved scores and activations.
4. **Title.** Agents propose a title, keeping "Recruited" as the lead word, with alternatives in HANDOVER.md.
5. **Repository.** Work only on the `followup` branch of a fresh clone. Agents may push to `followup` all night. Never commit to `main`. Never move or delete the `apart-submission` tag. `BRIEF.md` and `WRITING.md` may be public on `followup` only.
