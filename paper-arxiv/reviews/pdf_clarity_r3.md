# Blind clarity review of the draft PDF, round 3

PDF a417aaa5. **Score: 3/5. Verdict: FAIL.** The reader's answers to Q1–4 match the claims, including the trained-text finding as the biggest limitation.

## The core problem: number density
The reader lost track among near-identical AUROCs that differ in model, episode set, detector and label. Collisions:
- the strict-next score 0.75 and Jev's 0.75;
- "82% caught" and the gpt-oss fresh AUROC 0.82;
- three different 0.93s: the Qwen bag-of-words classifier, the incoming-only probe, and the gpt-oss dev reasoning probe;
- Table 2 mixes two leak labels (‡) in one column.

## Q5: hardest passage
p5, §4.1: "That monitor is Jev asked to forecast a leak at any later point ... Its plan fixed a slightly different leak label ..."
- "Its plan" has an unclear referent.
- "Forecast any later point" doesn't match the "this round or next" question it is scored on.
- A second leak label is introduced in passing.

## Q6: terms the reader had to guess
- pre-registered, frozen, fresh
- last-prompt probe
- Jev / decision model
- control peer, target working alone
- Jev forecasting
- reading position
- placebo
- incoming-only probe, "one seed; different calls"
- family
- ControlArena

The indicator symbol in the label equations also renders oddly.

## Q9: figures
- **Fig 4:**
  - The bottom-right example panel has only two points, so it conveys nothing.
  - "Score percentile" is unexplained.
  - The dev and fresh medians differ on gpt-oss, without explanation.
- **Fig 5:** the "chance" label overprints the panel titles.
- **Fig 6:** the dashed orange line and the "(one seed; different calls)" row are unreadable without the caption.
- **Fig 1:** filled and hollow markers are hard to tell apart. The Qwen fresh point has no x-label of its own.
