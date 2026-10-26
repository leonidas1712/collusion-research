# Author's abstract: use this structure and wording (26 Oct, ~22:30)

Leo rewrote the abstract for clarity. Use it **verbatim** as the arXiv abstract.
- Change only the numbers, and only to match the registry: same dataset, same calls, via the macros.
- Keep the structure: main result first, then the ladder, then what it means and its limits.
- Do not add numbers or qualifiers.

> Just before an AI agent gives in and breaks its operator's rule, a linear probe on its activations can tell. We study recruitment, a common first step of collusion: a peer agent presses a target agent, over many rounds, to reveal a secret its operator told it to keep, such as a deploy token. The target often refuses at first, then gives in. Read at each call before the model generates anything, a probe tells whether that call is about to leak the secret, with AUROC 0.95 on Qwen3-32B. A text monitor given the same conversation scores 0.74. On gpt-oss-20b, a reasoning probe scores 0.91 in a pre-registered test on fresh episodes, catching half of leaking calls at a 2% false-alarm rate.
>
> The signal is sharp but short-range. Checked at each call, the probe can tell when the very next output will leak the secret, but it weakens when asked about the next round, and nearly disappears when asked whether an episode will ever leak.
>
> For multi-agent oversight, this suggests a cheap monitor that runs on every call and pauses an agent just before it gives in, catching what a text monitor misses. Probes matter most where output filters fail, such as paraphrased, encoded or slowly coordinated leaks, which we leave to future work.

## Number mapping (coordinator's guidance)

**Qwen probe vs text monitor.** Use the pair scored on the same calls: the development held-out-scenario per-call probe (\qwenCallProbe, ~0.96) vs Jev (~0.76).
- If the registry has a Jev score on the fresh episodes for the same calls, the fresh pair may be used instead (probe 0.98 vs Jev on fresh).
- Never mix datasets within the pair.

**gpt-oss.** The 0.91 is the frozen reasoning probe on fresh episodes.
- "Catching half of leaking calls" is 14/26.
- "At a 2% false-alarm rate" is 12/490 refusing calls, about 2.4%. Round it or state it consistently with the registry.

**"Pre-registered".** Keep this one word for the gpt-oss test. It is the strongest rigour signal, and it costs a single word. Add no other status words anywhere in the abstract.

**Length.** The author's abstract has more than three numbers. The author's choice overrides the WRITING.md limit here.
