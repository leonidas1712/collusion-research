# Claims list (PROPOSED, round 1; author sign-off pending)

Every Results paragraph in `paper-arxiv/` serves one of these claims. Headline numbers are `numbers.yaml` keys (macro names in brackets); the registry is authoritative.

Named datasets (defined once, in Setup):
- **development episodes**: per model, the episodes used to build and evaluate every method, evaluated on held-out scenarios (train on five, test on the sixth, rotate).
- **fresh test episodes**: per model, episodes collected later and scored once by models frozen on development episodes.

Leak label for every per-call and ladder result: the first call that writes the secret into its reply or into any tool-call argument (the gpt-oss frozen detector, applied to both models). The pre-registered Qwen round-level test keeps its own round-level label, defined in Appendix B.

"Pre-registered" is used for the gpt-oss reasoning-probe test. The Qwen per-call result is "on fresh episodes held out from training".

---

## C1. The call that leaks is readable just before it acts (headline)

- **Claim.** A linear probe read before a call generates anything picks out the call that will leak, on both models. On gpt-oss-20b this held in a pre-registered test on fresh episodes; on Qwen3-32B a probe frozen on development episodes held on fresh episodes, catching most leaking calls at a low per-call flag rate.
- **Headline numbers.** `\gptossFreshReasoning` (0.91, pre-registered); `\qwenFreshCallProbe` (0.98); operating point `\qwenFreshProbeCaught` / `\qwenFreshProbeAlarm` (82% / 5%).
- **Dataset / evaluation.** Fresh test episodes (both models); development episodes, held-out scenarios.
- **Figures.** Fig. 1, Table 2, Fig. 3 (score trajectory).
- **Travelling caveat.** The warning is about the current call, not calls or rounds ahead (C2).

## C2. The signal is sharp but short-range

- **Claim.** On the same calls, the probe goes from near chance for "will this episode ever leak?", to modest for "this round or the next?", to high for "this call?". One call earlier it is already much weaker. The "this round or the next" result held in a pre-registered Qwen3-32B round-level test (probe 0.68, best text monitor 0.64).
- **Headline numbers.** `\qwenEverProbe`, `\qwenCallProbe` (development ladder ends); `\qwenFreshNearProbe` (0.68).
- **Dataset / evaluation.** Development episodes, held-out scenarios, same calls for every rung; fresh test episodes for the round-level test (its own label).
- **Figure.** Fig. 1.
- **Travelling caveat.** None inline.

## C3. Who can read the signal: a zero-shot monitor does far worse; a trained text classifier comes close

- **Claim.** A zero-shot decision-model monitor (Jev), shown the same conversation and tool results, scores well below the probe on both models; on gpt-oss-20b it flags most pressured calls. A bag-of-words classifier trained on the same labelled development calls comes close to the probe, which keeps a small edge whose interval excludes zero. Most of the probe's lead over the zero-shot monitor comes from training on labels; activations add a small, reliable edge; much of the signal arrives with the incoming message.
- **Headline numbers.** Fig. 4 bars; paired gaps in Appendix H (`\qwenProbeMinusTextLatest`, `\gptossProbeMinusTextFull`).
- **Dataset / evaluation.** Development episodes, held-out scenarios, same calls.
- **Figure.** Fig. 4.
- **Travelling caveat.** The text classifier result is on development episodes; whether it holds outside templated scenarios is open (Discussion).

## C4. Deployment cost is a per-call review workload

- **Claim.** At a threshold set on control calls, the probe flags few calls in refusing episodes and far fewer than the zero-shot monitor. Per episode, most refusing episodes see at least one flag, so the intended use is a cascade that escalates single calls, not an alarm that stops the agent.
- **Headline numbers.** `\qwenFreshProbeAlarm` vs `\qwenFreshJevAlarm`; `\qwenFreshRefusingEpisodeAlarm` (59%).
- **Dataset / evaluation.** Qwen3-32B fresh test episodes.
- **Figure.** Fig. 5 (Qwen alarm trade-off).
- **Travelling caveat.** None inline; the per-episode rate is explained in the same subsection.

## Supporting (not a separate claim): the probe is not explained by three simple shortcuts

The request, keywords for the secret, and the file read or write (Section 4.1, Appendix H).

## Biggest limitation (Discussion, stated once)

Narrow setting: two models, six templated scenarios, one peer, exact-string secrets that an output filter would catch.
