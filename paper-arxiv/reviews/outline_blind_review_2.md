# Blind outline review, round 2 (outline v2; score 3.5/5)

**Answers 1–4 matched the plan:**
- Question: can activations predict leaks before the act, and do they beat a text monitor?
- The ladder: ever near chance; this round or next 0.68 on Qwen fresh; this call high.
- Confirmed: the gpt-oss reasoning probe, 0.91 on fresh episodes.
- Biggest limitation: exact-string secrets, which an output filter catches.

**5. Hardest to follow.** §3.4: "Because leaks come early, we compare calls only within the same scenario and round, so 'early rounds are risky' scores exactly chance." Fix: say plainly that AUROC is computed within scenario × round groups, and why.

**6. Terms the reader had to guess.**
- Jev / "commercial decision model" (what is it?)
- "frozen with its alarm threshold"
- development vs fresh episodes (used in the abstract before being defined)
- control peer / "the target alone"
- "reruns that share a history"
- round vs call (how many calls per round?)
- "under pressure"
- matched controls
- channel-only leak label
- served replies
- "behaviour-only" (Gemma)
- screen summary
- "the frozen plan required"
- "the best text monitor" (Appendix E says three monitors; the main text says one)

**7. Lost track.**
- Abstract: "a simpler probe does the same on both models (AUROC 0.95 on Qwen3-32B)" says both models but gives one number.
- §4.1.2: the monitor's fresh-episode number is missing next to the probe's 0.68. It seems to clash with "the probe beats the text monitor".
- It's unclear whether 0.95 is held-out-scenario on development episodes.
- The gpt-oss last-prompt number is missing.
- §4.3: gpt-oss "near chance at the round level" sits oddly beside Qwen's confirmed 0.68.

**8. Score: 3.5/5.** The main suggestion is one early results grid where every number has one home (Figure 1 was not visible to the reader).
