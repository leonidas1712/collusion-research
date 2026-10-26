# Fresh blind reviews after Leo's round-1 feedback (PDF 4ca00aa5)

## Clarity: 4/5, PASS on score
**Story check:** yes. **Intro check:** sets up the problem before the results.

Fixes:
- **§4.4 stricter-threshold paragraph:** it mixes calls and episodes and three thresholds. Split it.
- **"Because it usually leaks within a round":** the causal "because" is unclear.
- **Define at first use:** Jev (concretely), control calls, refusing episodes, the handoff file, the cascade, and the Fig 1 "fresh last-prompt" label.
- **Possible detours:** the reasoning-vs-last-prompt "within noise" paragraph (p5) and the round-level fresh side result (p7).
- **Deployment numbers:** the reader asks for a small table: threshold × population × per-call/per-episode.

## Rigour: "core finding survives; fixable important issues, none headline-reversing"
1. **"Reliable" edge:** the lower bounds are +0.004 and +0.002, on development only. Drop "reliable" and keep "small".
2. **Shortcuts:**
   - "No to all three" / "not reading the obvious shortcuts" overclaim. The read flag alone scores 0.83/0.80, and the probe adds 0.13/0.11. Reword to "beats each shortcut".
   - One call earlier, the read flag scores about as well as the probe.
3. **Trajectory:** "stays low" is too strong. Use "is lower on average".
4. **"Held on fresh episodes on both models":**
   - On gpt-oss it is the reasoning probe that held.
   - The fresh last-prompt probe scores 0.82 and catches 30.8% at its frozen threshold. State this once in the main text.
5. **Leaking-episode vs leaking-call counts:** gpt-oss development has 146 emitting episodes but 121 leaking calls. Fresh has 30 vs 26. Explain once: some emitting calls are excluded (empty reasoning), plus say how those episodes' calls are labelled.
6. **Table 18:** the call totals don't add up (1407 + 433 > 1825). State the call set.
7. **"About 23 calls":** 23 is the median, while the mean is 27.6 (Table 18). Say "median".
8. **Repro additions:**
   - TF-IDF settings (n-grams, vocabulary, C);
   - the MLP spec;
   - the incoming-only probe recipe;
   - how the inner split and families are defined;
   - the protected values and rule wording for the five other scenarios.
9. **Author calls (HANDOVER):**
   - the title and abstract "gives in" framing vs "reads the situation" being open;
   - the abstract's per-call operating point without precision (24%) and the per-episode rate (59%);
   - the 0.91 rests on 26 leaking calls.
