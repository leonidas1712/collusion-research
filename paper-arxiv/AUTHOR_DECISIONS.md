# Author decisions for the arXiv rewrite (26 Oct 2026, before the overnight run)

1. **Headline.** The headline figure and the abstract lead with the ladder (predictability rises as the question nears the act), with the per-call probe at the top. The confirmed gpt-oss fresh-episode result is the confirmed anchor.
2. **Per-call leak label.** Unify the per-call question on "any public emission": the secret written into a reply, a channel message, or any file outside the protected one.
   - Keep gpt-oss as is, including its frozen confirmation.
   - Refit and recompute the Qwen per-call results under that label from saved activations, as a new run folder. Log what changed in the analysis history.
   - For the round-level question, keep the pre-registered Qwen confirmation numbers on their original label. Define the round-level label once, in Setup or the appendix, and do not mention it in the main text beyond that.
3. **Compute.** Modal GPU spend up to $10 in total, only if a recomputation needs re-extracting activations. Everything else is CPU from saved scores and activations.
4. **Title.** Agents propose a title, keeping "Recruited" as the lead word, with alternatives in HANDOVER.md.
5. **Repository.** Work only on the `followup` branch of a fresh clone. Agents may push to `followup` all night. Never commit to `main`. Never move or delete the `apart-submission` tag. `BRIEF.md` and `WRITING.md` may be public on `followup` only.
6. **Blind-review rounds are bounded.** Run at most 3 to 5 rounds of the clarity and rigour reviews. Stop earlier when the reviewers are only raising small or irrelevant points, since an AI reviewer asked to find problems will always find something. Fix only what matters: anything under WRITING.md §8 questions 6–7, and anything that changes a headline. Record the final verdicts and the reason for stopping in HANDOVER.md.
7. **Qwen per-call fresh-episode test (route 1, approved).**
   - Fit the Qwen per-call probe on the development episodes only.
   - Commit a freeze file (probe recipe, layer rule, label, metric, comparison, pass threshold) before any fresh-set scoring.
   - Score the 89 fresh episodes once.
   - Report it plainly in the main results as a held-out test on fresh episodes. Add one line in the analysis-history appendix noting that the sprint's pooled analyses had already looked at those episodes, so the test was not pre-registered.
   - Write the result in plain, confident sentences. Do not hedge it.
8. **Logged for later, not tonight (route 2).** A clean pre-registered confirmation of the per-call result on brand-new Qwen episodes: freeze, collect new episodes, score once. It needs GPU and peer API, roughly $20–40. Revisit only if needed, e.g. for a workshop submission.
9. **How codex/GPT feedback is used.** Codex and GPT-harness agents are valuable for checking accuracy, but they tend to push toward softening, hedging and qualifier-heavy wording. That is the main source of the sprint paper's poor readability. Their accuracy findings must be acted on. But the *wording* of every fix is decided by a Claude writer under WRITING.md: make the claim precisely true in plain words, or move the detail to the appendix or Limitations. Never paste a codex-suggested qualifier into prose verbatim.
10. **Two new figures, approved.**
    - **Probe score through an episode.** Include it only if the spike-at-the-leak behaviour really is there. Choose the episode or episodes by a fixed rule, not by cherry-picking.
    - **Alarm trade-off curve.** Plot the share of leaks caught against the false-alarm rate, for the probe and for the text monitor, with the operating point marked.
    The writers decide where each figure goes, keeping the main text at 9–10 pages.
11. **Calibrate the rigour bar.** This is a solo author polishing sprint work into a solid arXiv preprint, close to workshop or conference quality. It is not a lab-scale paper.
    - Match the rigour of the closest published papers; the calibration memos are `reviews/rw_calibration_*.md`.
    - Do not chase every reviewer request. Anything beyond that norm goes to Future work or Limitations in one line.
    - No new analyses tonight.
