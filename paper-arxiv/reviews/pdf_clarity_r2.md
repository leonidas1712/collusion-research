# Blind clarity review of the draft PDF, round 2

PDF 64d447c6. **Score: 3/5. Verdict: FAIL.** The fresh reader's answers to questions 1–4 matched the claims list.

**5. Hardest to follow**
- p6: the strict-next sentence shows a literal "pending" (now filled at 0.75), and it is hard to parse.
- p5: the Qwen round-level paragraph introduces a different label and a different monitor question in passing.
- App. Tables 7 and 8 read "Pending verified analysis".

**6. Terms the reader had to guess**
- Jev / decision model
- last-prompt token / reading position
- frozen / committed plan
- control peer, target working alone
- public emission
- families
- placebo
- incoming-only probe, single-seed recipe
- recruitment
- AUROC within scenario and round

**7. Where the reader lost track**
- The abstract says Qwen 0.96 (dev), but Table 2 shows 0.98 (fresh). The reader could not tell which is the headline.
- p5: the reasoning-probe 0.93 on dev is not in Table 2.
- Table 2's fresh row for "this round or next" (0.68/0.64) uses a different label from the dev 0.67 row below it, and the table doesn't say so.

**8. Overall.** 3/5. Many "Section X" pointers make the text choppy. The single most useful fix: tag every number's split and label, and fill all pending values.

**9. Figures**
- **Fig 1:** the x labels "Ever / This/next round" are cryptic. It is unclear why "this call" has three markers.
- **Fig 5:**
  - Its notes read as unedited annotations, e.g. "Lower rule/control scores leave a gap to explain".
  - The dashed and dotted lines are hard to tell apart.
  - The grey box with in-plot text is confusing.
- **Fig 4:** works on its own, but should flag that the monitor scores below chance on gpt-oss.
