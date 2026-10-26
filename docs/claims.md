# Claims list (PROPOSED; not yet signed off by the author)

Every Results paragraph in `paper-arxiv/` serves one of these claims. Headline numbers are `numbers.yaml` keys, owned by codex-2. Values shown here come from the sprint paper and are placeholders until the recomputations land; the registry is authoritative.

Named datasets (defined once, in Setup):
- **development episodes**: per model, every episode collected before the analysis plan for that model's test was frozen. Evaluated by held-out scenarios: train on five scenarios, test on the sixth, rotate.
- **fresh test episodes**: per model, episodes collected after a plan was frozen. Scored once by frozen models trained only on development episodes.

Leak label for every per-call and ladder result: **any public emission**, implemented as the gpt-oss frozen detector: the first call that writes the secret into its reply or into any tool-call argument (author decision 2; boundary case recorded in HANDOVER). The round-level confirmation on Qwen keeps its pre-registered label, a complete channel post or a new file. It is defined once, in Setup.

---

## C1. The call that leaks is readable before it acts (headline)

- **Claim.** A linear probe on the target's activations, read before a call writes anything, picks out the call that will leak the secret. On gpt-oss-20b this held on fresh test episodes under a plan fixed in advance.
- **Headline number.** `gptoss_fresh_reasoning_probe_auroc` (0.91, confirmed). Supporting: `qwen_percall_probe_auroc` (to be recomputed on any public emission; sprint value 0.95 on the give-in rule) and `gptoss_percall_lastprompt_auroc` (0.91), both development.
- **Status.** Confirmed for the gpt-oss reasoning probe. Exploratory for the last-prompt probes on both models.
- **Dataset / evaluation.** Fresh test episodes, gpt-oss-20b, frozen model scored once. Development episodes, held-out scenarios, for both models.
- **Figure.** Fig. 1(b) (fresh test) and Fig. 3 (development, with comparators).
- **Travelling caveat.** The warning is about the current call. One call earlier the signal is much weaker, so this does not establish warning rounds ahead.

## C2. The nearer the question is to the act, the more predictable the leak

- **Claim.** Asked on the same calls whether the episode will ever leak, whether it leaks this round or next, and whether this call leaks, the probe goes from near chance, to modest, to high, on both models. The middle rung held on fresh test episodes for Qwen3-32B.
- **Headline number.** The ladder top and bottom on development (`qwen_ladder_ever_auroc`, `qwen_ladder_call_auroc`; gpt-oss equivalents). Confirmed anchor: `qwen_fresh_nearterm_probe_auroc` (0.68).
- **Status.** Ladder exploratory. Qwen near-term on fresh test episodes confirmed.
- **Dataset / evaluation.** Development episodes, held-out scenarios, same calls for every rung. Fresh test episodes for the anchor.
- **Figure.** Fig. 1(a) (headline).
- **Travelling caveat.** None inline. The anchor uses the round-level label, which is defined once in Setup and drawn as a separate panel.

## C3. A text monitor shown the same conversation does worse

- **Claim.** A decision-model text monitor, shown the same conversation and tool results as the probe and asked whether this call will leak, scores well below the probe on both models. On gpt-oss-20b it flags almost every call made under pressure, so it cannot separate the calls that leak.
- **Headline number.** `qwen_percall_jev_auroc` (sprint 0.74, to be recomputed), with the probe-minus-monitor difference and its interval in the figure.
- **Status.** Exploratory.
- **Dataset / evaluation.** Development episodes, same calls as C1.
- **Figure.** Fig. 3.
- **Travelling caveat.** One monitor, asked one question, with no tuning. This goes in Limitations, not inline.

## C4. The probe is not just reading pressure, the secret string or the read step

- **Claim.** Every call that does not leak was also made under pressure, so the probe is not detecting the request. It also beats keyword rules and a flag for "the protected file was just read".
- **Headline number.** `gptoss_readstep_flag_auroc` against the probe (difference in the figure). Placebo and keyword scores go in the figure.
- **Status.** Exploratory.
- **Dataset / evaluation.** Development episodes, same calls as C1.
- **Figure.** Fig. 4.
- **Travelling caveat.** What the probe reads is not established. A probe that sees only the incoming peer message and tool results also scores high. This is stated once, in this subsection, because the claim would mislead without it.

## (Setup fact, not a claim) The setup produces mixed outcomes

The same model under the same pressure leaks in some episodes and not in others. Control and target-alone episodes never leak. Number: `qwen_leak_rate_dev`. This stays in Setup as a description of the data, with no Results subsection.

## Biggest limitation (Discussion, stated once)

Narrow setting: two models, six scenarios from one task template, one peer, exact-string secrets. Second: the per-call last-prompt results are exploratory, and only the gpt-oss reasoning probe was confirmed on fresh episodes.
