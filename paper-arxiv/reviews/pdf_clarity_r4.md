# Blind clarity review, round 4 (final round), PDF 8fb8fca1

**Score: 3/5.** Answers 1–4 match the claims. The story check (Q10): "Yes, mostly."
- The story it read: a per-call probe flags the call about to leak, much better than a zero-shot monitor. The signal is short-range. That supports a pause-before-acting monitor, not early warning.
- Not serving the story: Fig 3 and the round-level paragraph, a side test with a different label. The bag-of-words result is not reconciled with the "activations reveal" title.

**Q5, hardest passage:** p5, "The probe is not reading the obvious shortcuts …".
- It packs three controls into two sentences.
- "Handoff file" is never introduced.
- It is unclear what the keyword rules key on.

**Q6, terms the reader had to guess:**
- Jev
- last-prompt probe
- scored calls
- Table 1 columns (Recruit./Control/Alone/Excluded)
- y^near
- frozen (defined late)
- "within noise"
- the read / handoff file
- "middle of the ladder"
- "One call earlier?" row
- "the 2026 incident"
- confirmation plan
- placebo
- family

**Q7, where the reader lost track:**
- The intro's 82%/5% vs 68%/29% sentence doesn't name the model, dataset or threshold. It is also confusable with the gpt-oss fresh AUROC of 0.82 and with the abstract's gpt-oss "half at 2%".
- p6: the round-level 0.68 sits next to the dev 0.67 in Table 2.
- p8: "Qwen fresh not pre-registered" vs the abstract leading with 0.98.

**Q9, figures:**
- Fig 1: the gpt-oss fresh point is the reasoning probe; the fresh last-prompt 0.82 is omitted.
- Fig 3: two isolated dots.
- Fig 4: row labels overlap the chance line; gpt-oss Jev below chance is not explained.
