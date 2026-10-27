# Does related work separate "about to do the action" from "about to break the rule"?

Research note, 27 Oct 2026. No paper edits, no runs, $0 spend.

## The question

Our E08 counterfactual re-ran the same calls with the operator's rule changed to permit sharing. The frozen per-call probes barely moved. So they track that the agent is about to write the protected value out, not that writing it breaks the rule. This note asks whether related work separates three cases:

- **(a)** an action that discloses or does harm and is **forbidden**;
- **(b)** the **same** action when it is **permitted** or authorised;
- **(c)** the same situation with **no** such action.

For each paper we checked, in the full text where possible:
- the labels;
- whether the classes differ in the action itself, or only in its permission;
- whether there is a matched control that varies only permission, and what it showed;
- where the probe reads.

## Answer in one paragraph

Almost all probe and monitor work compares (a) with (c): the positive class does the harmful action and the negative class does not. Separating "doing it" from "doing it when forbidden" is therefore rare.

One preprint does build the (a)-versus-(b) contrast with probes on agents. Fayyazi et al. (2026) give each scenario an "authorized twin" that differs in one fact, so the same critical action is allowed. They train their probe with those twins as negatives. Even so, the probe separates a violation from the same permitted action less well (AUROC 0.92) than from a different action (0.985). A text classifier that can read the permission line does better than the probe on that contrast (0.945–0.949).

Two non-peer-reviewed notes report the same split. One claims an "authorization direction" at the tool-call token, but its own scope note says the result is not isolated from wording. Its follow-up finds that the frozen direction lets through 21 of 21 unauthorised deletes, because it tracks "the authorization the model feels, not the one the user granted".

The deception literature points the same way:
- Its probes respond to deception-related context even when the answer is honest.
- They fire on falsehoods the user explicitly requested.
- On average they partly track instruction compliance rather than truth.

**So our E08 result is expected, not surprising.** A probe that is not trained on permission reads the coming act, and permission is easier to read from the text where it is stated. E08's own contribution is narrower: it holds the calls fixed and flips only the operator's rule, on a frozen per-call probe in a peer-recruitment setting.

## Table

Full text was read unless marked otherwise. Section and table numbers are from each paper. "Action differs?" asks whether the positive and negative classes differ in the action itself.

| Paper | Setup | Positive vs negative | Action differs? | Permission-only control? | Result | Relevance to us |
|---|---|---|---|---|---|---|
| **Fayyazi, Kamal & Pedram 2026**, "The Agent Knew" (arXiv 2610.17301) | 24 agent task templates in 8 safety families, mock tools, 4 open models. Probe on the residual stream at 5 depths, last reasoning token before the tool call; LDA (§2, §3.2, App. G). | **+** the critical action when unauthorised. **−** (1) the agent's other actions; (2) the **same critical action in an "authorized twin"** that differs in exactly one fact: a policy line, an owner's message or a ticket status (§3.2, App. C). | Against twins: **no**, both take the same action. Against other actions: yes. | **Yes.** Twins are training negatives, built to "force g to read whether the action is authorized, not which action it is" (§3.2). | Probe AUROC **0.917** vs twin; **0.985** vs other actions. Text beats the probe on the twin contrast (0.945–0.949) "because the permission itself is written in the context". The probe's lead over text comes only from action vs no-action (App. I, Table 2). Holding out a safety family, the twin AUROC falls to 0.81 (App. O). | **Closest prior work.** Our (a) vs (b), with a probe *trained* on permission. Permission is readable, but better from text. |
| **Vicentino 2026a**, "The Authorization Direction" (Zenodo 10.5281/zenodo.20683623; **not peer-reviewed**) | 6 simulated irreversible tools; Qwen3.6-27B and gpt-oss-20b. Late-layer difference-of-means read at the tool-name token. | **+** the trusted user authorised the action. **−** the agent initiated it itself, or an injected message asked for it. | Same tool and parameters, but the prompts differ in **who asked**. | Partly. The author's scope section says the AUROC 1.0 has a "surface-lexical component [that] is not fully isolated". | AUROC ≈ 1.0 (n = 24 per condition, Qwen). | Claims authorisation is decodable at the action, but the contrast is the requester, not a rule flip with the request held fixed. |
| **Vicentino 2026b**, "Felt, Not Granted" (Zenodo 10.5281/zenodo.20685264; **not peer-reviewed**) | Qwen3.6-27B file agent with real deletes in a sandbox. The frozen direction above scores each proposed delete; compared with an LLM judge that reads the user's task. | **+** unauthorised deletes elicited by "momentum" framing. **−** explicitly authorised deletes. | **No**: the same delete in both classes. | **Yes**: only the grant differs. | The probe **allows 21 of 21** unauthorised deletes (Wilson CI 0.845–1.0), with 0 of 12 false positives. The judge blocks 21 of 21 (§4). | **Closest match to E08.** The probe "tracks the authorization the model feels, not the one the user granted". |
| **Dong et al. 2026** (arXiv 2608.02657) | AgentDojo injection exposure, 8 models. Linear probe on the prefill residual at the post-assistant token (§3.2). | **+** the latest tool result contains an injection. **−** otherwise (§3.1). | No. The label is a property of the input, not of the action. | No. | Held-out AUROC 0.93–0.98. 22% of flagged exposed turns resist the injection (§4.1). | Reads "an injection is in context", not compliance or violation. |
| **Yu et al. 2026** (arXiv 2610.05295) | (i) Role probe on identical text framed as an instruction or as data. (ii) Hijacked vs resisted AgentDojo runs that saw the same injection. Residual at the last input token (§4–6). | (i) "Execute this request: X" vs "Summarize this note: X". (ii) Executes the injected command vs ignores it. | (i) Only the framing differs, though the resulting action also differs. (ii) The action differs. | (i) Nearest analogue: only the authorising frame changes. | Role AUROC 0.92 (Table 3). Applied unchanged to hijacked vs resisted runs: 0.82–0.84. **Steering along it does not change attack success** (33.8% vs 34.6%, Table 11); only the action-derived direction does. | Authorisation is readable, but the direction the behaviour runs on is the action one. |
| **Jia et al. 2026** (arXiv 2610.24048) | Branching from identical injection-exposure states, 5 models. Logistic probe averaged over the reasoning prefix (§3, App. B). | Comply (a later call carries an attacker identifier) vs resist. | Yes. | No. Same-tool pairs control for which tool is called, not for legitimacy (§5.1). | Early probes, after removing per-state means, are no better than TF-IDF (Table 1, §5.4). | Comply vs not only. |
| **Fomin et al. 2026** (arXiv 2606.30449) | Three probe families: an insecure fine-tune, harmful advice, the blackmail scenario. | Continue vs correct; blackmail vs not. | Yes. | No. Here "situation" means the prompt's domain and context, not permission. | Domain decodes at AUROC 0.999, behaviour at 0.80 (§5.2). | Probes read context more easily than action. Does not test permission. |
| **Gao 2026** (arXiv 2610.04575) | Alarm-policy audit of probes; AgentDojo, layer 14, last token. | Executes the injected task vs a safe attempt on the same case. | Yes. | No. | AUROC 0.80, but 2 of 38 caught at a 5% alarm budget. No gain from activations over an observable comparator (Table 6). | Action contrast only. Also: AUROC is not alarm validity. |
| **Rose et al. 2026**, NARCBench (arXiv 2604.01151) | Committee vote; 2 of 4 agents are secretly told to collude. Probe at the last token of each agent's response, mid layers (App. C). | Colluders vs honest agents, and collusion runs vs control runs. | Yes: different instruction *and* different votes and arguments (App. L.4). | No. Agents that refused were dropped (App. J.7). | AUROC 1.00 in distribution. Transfer to emergent collusion only 0.49–0.73 (§6.3, Table 1). | Instruction and action are confounded. |
| **Goldowsky-Dill et al. 2025** (arXiv 2502.03407) | Deception probes on Llama-3.3-70B, layer 22, mean over response tokens (§3). | Training: the *same* true response after an "honest" vs "dishonest" instruction. Evaluation: lie vs no lie, including insider trading and sandbagging. | Training: only the instruction differs. Evaluation: the behaviour differs. | Partial. App. A.1 compares honest answers with and without an incentive to lie. | The probe scores **higher on honest answers when there is an incentive to lie** (Fig. 7b; values only in a plot, **not verified**). It "activates more on deception related dialogues (even if the response is honest)" (§5.1), "seems to track something close to morality" (§4.1.2), and fires on falsehoods the user requested (App. C). | Reads context and "morality", not violation. Fires on permitted falsehoods. |
| **von Klinski et al. 2026** (arXiv 2609.39807) | Stress-tests 8 published lie detectors on 3 models; logistic probes, mostly at the end-of-turn token. | Lie vs truth, including answers a persona was instructed to give. | Controls hold the instruction fixed and vary truth. | Yes, the mirror image of E08: shared-persona prefill, and a set where truth and instruction compliance are anti-correlated. | Goldowsky-Dill's RepE probe: 0.862 on-policy → **0.438** with the persona shared → **0.170** on the compliance set. "Many existing probes strongly track instruction compliance or response likelihood" (abstract; Table 2). | Deception probes partly read compliance. Ours did not move with permission, so it is not a compliance or violation detector. |
| **Spontaneous vs instructed deception**, arXiv 2609.00180 (**first author not verified**) | Llama-3.1-70B; deception that is instructed vs deception that arises from an in-scenario incentive. Layer 35. | Deceptive vs honest, in each setting. | The behaviour is shared; only the reason for it differs. | Transfer across the two settings. | Spontaneous → instructed 0.999 on response tokens. At the last prompt token, spontaneous deception scores only 0.60 (Table 1). | The signal is on the act and is shared whether or not it was instructed. |
| **Wang, Xiong & Shu 2026**, privacy norms (arXiv 2604.00209) | Probe read at a *judgement* prompt ("this practice is…"), 4 models. | Appropriate vs inappropriate information flow; 500 matched pairs differing in recipient or norm. | Context-only, and no action is taken. | Yes (context). | AUROC > 0.90 in deep layers, yet the model still leaks in 42.5% of role-plays (§3.3). | Appropriateness is decodable when the model is asked to judge, but behaviour does not follow it. |
| **Scheurer et al. 2023**, insider trading (arXiv 2311.07590; behaviour only, no probes) | A five-level system-prompt ladder from "strongly encouraging" to "strongly discouraging" insider trading (§3.3.2, App. A.3.1). | (Behaviour rates.) | — | Permission varied; behaviour measured. | Rates swing towards 0% or 100% but never quite reach them. An in-context cue that the trade is illegal stays in every condition. Exact rates are in a chart only (**not verified**). | A ready-made permission ladder that no one has probed. |

**Also checked, less central:**
- *Actions or behaviours, not permission (one line each):*
  - MacDiarmid et al. 2024, sleeper-agent probes: they read upcoming defection, AUROC 99.3%.
  - Kortukov et al. 2026: they read upcoming behaviour from the chain of thought.
  - McKenzie et al. 2026, high-stakes probes: "responsible money laundering" fools them.
  - Saraogi et al. 2026, read from the repo only: about the sycophantic flip, with a weak signal.
  - Ruan et al. 2026: forecasts task failure.
  - Advani et al. 2026, abstract only, **full text not verified**: predicts which tool comes next.
  - Chauhan & Revankar 2026 (arXiv 2606.04141): credential-exfiltration probe, leak vs no leak, AUROC 0.998.
  - NeuroFilter (arXiv 2601.14660): detects the request, not the action.
  - Zhao et al. 2025 (arXiv 2507.11878): harmfulness and refusal live at different tokens, which may explain why an action-time probe misses the rule.
- *Permission-only contrasts, but text monitors or behaviour rather than probes:*
  - Hu 2026 (arXiv 2609.20211): approval jumps from 0.05 to 0.60 when a "verified" marker is dropped.
  - MPCI-Bench (arXiv 2601.08235): agents leak in more than 90% of inappropriate traces.
- *AI-control benchmarks:* the benign runs in SHADE-Arena, BashArena and LinuxArena are honest runs of the main task, not the same side action done legitimately.
- AgentHarm's benign set changes the content, not just the permission.

## What this means for us

**(i) Wording the E08 finding.**
- Present it as consistent with prior work, not as a surprise. Pre-action probes read the coming act.
- A probe not trained on permission does not separate a forbidden disclosure from a permitted one. Even probes trained with permitted twins do this less well than text that can read the rule (Fayyazi et al., who are already cited).
- Do not claim to be the first to test permission. Our narrower contribution is the counterfactual itself: the calls are held fixed, only the operator's rule flips, and the probe is a frozen per-call probe in a peer-recruitment setting.
- "Mostly tracks the coming disclosure" stays accurate.
- One clause citing Fayyazi's authorized twins in the E08 appendix section would place it. Vicentino's "Felt, Not Granted" is the closest match, but it is not peer-reviewed: cite it only as a note, if at all.

**(ii) Would E09 be novel?** Only modestly.
- The core contrast, the same action permitted vs forbidden with probes on agents, is Fayyazi's authorized-twin design. It is done there at scale: 24 templates, 4 models, fresh data. Its result already predicts E09's likely main finding: text matches or beats the probe on the violation question when the rule is in the context.
- What E09 would add:
  - the peer-recruitment setting;
  - the same value with one permitted and one forbidden destination inside one episode;
  - an on-policy swap test with destinations counterbalanced against permission.
- If E09 goes ahead, frame it as testing whether that result holds under peer pressure. Pre-register that a trained text classifier may match or beat the probe on the violation question.

## Sources and checks

- Four reading agents fetched each PDF from arXiv (or Zenodo, or the GitHub repo for Saraogi) and read the extracted text.
- I re-checked the claims this note leans on against that text:
  - Fayyazi: the twin definition, "forces g to read whether the action is authorized", 0.917 / 0.985 / 0.941, and text 0.945–0.949.
  - Vicentino: "allows 21/21", and the scope caveat "not fully isolated".
  - Goldowsky-Dill: "activates more on deception related dialogues (even if the response is honest)", and "track something close to morality".
  - von Klinski: 0.862 / 0.438 / 0.170, and "strongly track … instruction compliance".
- Anything not confirmed in the full text is marked **not verified** above.
