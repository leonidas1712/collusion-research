# Blind clarity review, round 5 (28 Oct, overnight)

**Score:** 3.5 / 5. Reviewer saw only main.pdf.

**Story as the reviewer understood it:**
- Can an overseer tell beforehand which call gives in under multi-round peer pressure?
- Probes vs a zero-shot monitor vs bag-of-words, all scored on the same calls, with AUROC within scenario and round.
- Findings:
  - test AUROC 0.98 on Qwen and 0.91 for the gpt-oss reasoning probe;
  - the signal is short-range;
  - a trained text classifier nearly matches the probe;
  - the probe tracks the emission, not the violation;
  - halting is costly.

The reviewer judged it one focused story.

## Issues and actions (12 ranked, plus minor ones)
1. "Before generation" is overstated for the reasoning probe. **Body fixed.** Abstract: suggestion for Leo.
2. Negatives and flag-rate denominators are unclear ("benign", "control" and "refusing" used interchangeably). **Body fixed.** Abstract: suggestion for Leo.
3. The Evidence paragraph is a wall of status labels; "frozen" has two meanings. **Fixed.**
4. The §4.4 per-episode threshold reads as tuning then rebutting itself; "26%" has three meanings. **Fixed.**
5. Table 2 caption, the blanks, and Jev's 0.40. **Fixed.**
6. Fig 1 caption says "same leak label". **Fixed.**
7. Vague numbers in §4.1 and §4.3. **Fixed.**
8. The Fig 3 claim is stronger than the plot. **Softened.**
9. "Section L" should be "Appendix L". **Fixed.**
10. "Decision-model monitor" is undefined. Abstract: suggestion for Leo. Body unchanged (Method defines Jev).
11. Intro run-on sentence. **Split.** The suggestion to move "What is new" was **declined**: the intro structure is Leo-approved.
12. The string-filter caveat appears three times. **Reduced to two.** Layout faults on p1, p9 and p11. **Fixed.**

Minor:
- Table 1 names. **Fixed.**
- Fig 1 y-axis starting at 0.3. **Declined**: a 0 baseline is honest.
- Abstract last sentence. Suggestion for Leo.
