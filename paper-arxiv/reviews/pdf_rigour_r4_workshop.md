# Blind rigour review r4 (28 Oct, overnight; judged at top-conference workshop level)

**Verdict: weak accept, nothing fatal.** The design is sound: whole scenarios held out, related episodes grouped, frozen detectors, a pre-registered gpt-oss test, a trained-text baseline, and negatives reported honestly. The weaknesses are in framing.

## Claim by claim

| Claim | Verdict |
|---|---|
| Per-call AUROC | Supported |
| Deployment cost | Supported |
| Short-range warning | Supported, mostly on development |
| Text classifier | "Training explains most of the gap": supported. "Activations add an edge": partly supported (development only, lower bounds near 0) |
| Counterfactual | Partly supported. The score ignores the rule text, but "reads the disclosure" is not shown. Superseded by E14. |
| Cascade | "No detectable gain": supported. "Does not help": not supported |

## Actions
**Applied (claude-2):**
- cascade wording changed to "no detectable gain", with counts;
- the probe's own interval for 82%;
- Jev matched-cutoff clause;
- gpt-oss copy-vs-giving-in sentence moved into Limitations;
- wording fixes: "any output", Jev 0.40 mechanism, "same scored calls";
- consistency fixes: 2% vs 2.4%, App F bound, 0.82 interval;
- a test-episode bag-of-words row in Table 2 (claude-4 computing).

**Counterfactual:** replaced by the E14 result ("reads giving in, not the rule").

**Abstract:** suggestions in HANDOVER for Leo.

**Declined:**
- per-row evidence-status labels in Table 2 (status clutter; §2.3 states it once);
- the discarded first replay in the main text (it stays in the history appendix).
