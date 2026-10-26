# Blind clarity review of the draft PDF, round 1

Draft PDF 993ac707, 27 pages, some numbers still pending. **Score: 3.5/5. Verdict: FAIL** (a pass needs 4 or more, and nothing serious under Q6 and Q7).

## Q1–Q4: what the reader took away (these match the claims list)
- **The question:** can a linear probe predict a leak to a pressuring peer, and does it beat a text monitor?
- **Findings it reported:**
  - gpt-oss reasoning probe, frozen: 0.91 [0.78, 0.99];
  - last-prompt probe: Qwen 0.96 (dev), Qwen 0.98 (fresh, not pre-registered), gpt-oss 0.91;
  - the ladder;
  - Jev: 0.76 (Qwen) and 0.40 (gpt-oss).
- **Biggest limitation, as the reader saw it:** the incoming-only probe scores 0.93, so the signal may mostly reflect what just arrived. On top of that, the fresh sets are small and only one monitor is used.

## Q5: hardest passage
p5, §4.1 Qwen paragraph: "The strongest monitor here is Jev asked to forecast ... This test uses the leak label fixed in its plan, which differs only slightly from the one above." The reader could not tell:
- what "the one above" refers to;
- how the two labels differ;
- why the forecaster is the comparison here.

## Q6: terms the reader had to guess
- Jev / decision model (p4)
- frozen probe (abstract)
- matched controls (p2)
- scored calls (p3)
- placebo (p7, Fig 5)
- protected-read flag (Fig 5)
- incoming-only probe (one seed) (Fig 5)
- source confidence intervals (Figs 4–5)
- original frozen label/window (Fig 3)
- public emission (p13)
- family (pp. 14–15)

## Q7: where the reader lost track
- **Abstract:** "A simpler probe ... does the same on held-out scenarios (AUROC 0.96 on Qwen3-32B)". "The same" follows a fresh-episode result, but 0.96 is a development number.
- **Fig 1:**
  - For gpt-oss at "this call", it is unclear which probe the filled and hollow markers show.
  - Qwen's "this/next round" is pending in Fig 1, while Fig 3 shows 0.68 under a different label.
- **§4.1** mixes a per-call result (gpt-oss) with a round-level result (Qwen), and only the limitations section says which Qwen result was pre-registered.

## Q8: the one change that would help most
One results-at-a-glance table early on. Each row is a claim, with columns: model, label, probe or monitor, dev or fresh, pre-registered (yes/no), AUROC [CI].

## Q9: figures that don't work without their captions
- **Fig 3:** the font is tiny. "Original frozen label/window" is jargon.
- **Fig 1:**
  - The "pending" text and the footnote annotations make it look broken.
  - The filled and hollow markers overlap.
- **Figs 4 and 5:**
  - The marker shapes are never explained.
  - "Source confidence intervals" is unclear.
  - In Fig 5, the reader can't tell that low scores are good for the controls, while the incoming-only 0.93 is a caveat.
