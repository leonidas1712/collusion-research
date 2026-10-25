# Abstract and contributions (draft v1)

*Written from the three findings in `docs/report_plan_outline.md` §1. Second-model clause left as a slot.*

## Abstract (draft, ~200 words)

When AI agents work together, one agent may need something that only another agent is allowed to access. We study the moment a second agent is asked to break its operator's rule on the first agent's behalf, and ask whether that break can be seen coming. A peer agent repeatedly asks a target agent (Qwen3-32B) for a protected value, over up to 20 rounds, across six workflow scenarios; the target sometimes gives in and sometimes holds. We compare linear probes on the target's activations with text monitors (an LLM judge and two decision models) that read the target's actions, the conversation, or everything the target saw. All methods are scored on the same steps: after the target has read the value and before it discloses it. Three findings emerge. First, whether the target will eventually give in is not predictable from a single step: probes are at chance and the best monitor is barely above it. Second, whether it gives in this round or the next is modestly predictable: a probe reaches 0.58 AUROC on held-out scenarios and the best monitor 0.65, and the result held on 89 new episodes under a plan fixed in advance. Third, a monitor asked "will it break the rule?" outperforms one asked "is it breaking the rule?", and probes add to a weaker monitor. [SECOND-MODEL CLAUSE, if a result: one sentence.]

## Contributions (draft)

1. **A recruitment setup and a matched scoring protocol.** A multi-round setting in which a peer asks a target to break an explicit operator rule, with mixed outcomes and clean controls; and a protocol that scores activation probes and text monitors on exactly the same steps, between reading the protected value and disclosing it. With this protocol, eventual give-in turns out to be essentially unpredictable from a single step.
2. **Imminent give-in is modestly predictable, and the probe is not just detecting pressure.** Probes and the best monitor rank steps above chance on held-out scenarios and on new episodes under a frozen plan. A probe trained to detect pressure separates pressured from unpressured steps perfectly but cannot tell who gives in, while the near-term probe can.
3. **How to set up the text monitor.** Asking a monitor to forecast beats asking it to detect; the peer's side of the conversation is what makes forecasting work; seeing everything the target saw helps a decision model but not the LLM judge; and probes add to a weaker monitor and make different errors from the best one, which argues for combining them.
4. **[If the second model produces a result.]** The same pipeline, applied unchanged to a second model family (gpt-oss-20b) with a different route to giving in.

> Open for the author: the wording of finding 1 (corrected: probe at chance, best monitor weakly above chance at 0.577); whether the second-model contribution is item 4 or a clause in item 2; title.
