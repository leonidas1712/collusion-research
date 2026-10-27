# Sources for the motivation: why detect a leak before the call acts

Research note, 27 Oct 2026. Read-only; $0. Every quote below was copied from the source text that the reviewers downloaded. The quotes the suggested sentences rely on were re-checked against that text.

Status marks:
- **[full]**: verified in the full text.
- **[abs]**: verified in the abstract or summary page only.
- **[unverified]**: could not be checked.

"(in bib)" means the entry is already in `paper-arxiv/references.bib`.

The question is why an overseer should flag a call **before it acts**, rather than:
- block tool calls,
- filter outputs after they are written, or
- review transcripts afterwards.

Each section below covers one situation where after-the-fact checks fall short.

---

## (a) Leaks go out as ordinary text and messages, not only as tool calls

**Our own data** (current development episodes, first public emission per episode; `tables/episode_routes.tex`, run `runs/20261027-0034-e05-arxiv-development-episode-checks`):

| Model | Leaking episodes | End-of-turn reply | Channel message (`send_message`) | File write |
|---|---|---|---|---|
| Qwen3-32B | 66 | 29 (44%) | 32 (48%) | 5 (8%) |
| gpt-oss-20b | 146 | 3 | — | 143 (98%) |

- On Qwen3-32B, **61 of 66 leaks (92%) go straight to the shared team channel**. Once there, the peer and anyone else on the channel have read them, and they cannot be unsent.
- **29 of 66 (44%) are the plain end-of-turn reply**, which the harness posts to the channel. This is not a tool call, so a filter on tool calls alone never sees it.
- On gpt-oss-20b, almost every first leak is a file write: the whole configuration block copied into the shared handoff file.

**Sources:**
- **ConfAIde.** Mireshghallah et al. 2024, ICLR, arXiv 2310.17884. LLMs reveal secrets and private context in plain generated text. Abstract: "GPT-4 and ChatGPT reveal private information in contexts that humans would not, 39% and 57% of the time." [full]
- **PrivacyLens.** Shao et al. 2024, NeurIPS D&B, arXiv 2409.00138.
  - Claim: agents leak in the messages they send for a user, even when told to protect privacy. Abstract: "GPT-4 and Llama-3-70B leak sensitive information in 25.68% and 38.69% of cases, even when prompted with privacy-enhancing instructions." [full]
  - The leak is scored on the message content of the final send action (§3.1).
- **AgentDAM.** Zharmagambetov et al. 2025, arXiv 2503.09780. §1: "current AI agents can sometimes leak task-irrelevant but sensitive information. Pre-filtering using an LLM proves ineffective." [full]
- **Slack AI incident.** PromptArmor, 20 Aug 2024, vendor blog. A deployed assistant was induced to put private-channel data, including an API key, into its reply: "an attacker with access to Slack can exfiltrate data in private channels they are not a part of." The data reaches the attacker through a link written in the reply. [full, page text]
- **OWASP LLM02:2025, Sensitive Information Disclosure.** "LLMs … risk exposing sensitive data, proprietary algorithms, or confidential details through their output." [full, page text]
  - **Caution:** OWASP LLM07:2025 also says "the system prompt should not be considered a secret" and should not hold credentials. A reviewer may raise this against a setup that keeps an operator's secret in context. Cite OWASP for "leaks happen", not as endorsing secrets in prompts.

**Suggested intro sentence:**
> Agents leak through what they write, not only through tool calls: LLMs disclose secrets and private context in generated text and in the messages they send for users, even when told to protect privacy \citep{mireshghallah2024confaide,shao2024privacylens}. In our setting, most Qwen3-32B leaks go straight to a shared channel, and nearly half are the agent's ordinary end-of-turn reply, which a tool-call filter never sees.

---

## (b) Irreversible actions: catching them afterwards is too late

- **ToolEmu.** Ruan et al. 2024, ICLR, arXiv 2309.15817.
  - Claim: the most severe agent failures are graded by irreversibility. Safety-evaluator rubric (appendix): severe outcomes "entail consequences that are significant and often irreversible such as substantial financial and property loss (exceeding $1000), irreversible damage, or compromise of personal safety."
  - Case III: an agent ran `rm -rf /` and "warned the user about the 'irreversible' nature of the action after it had already been executed." [full]
- **AI Control.** Greenblatt et al. 2024, ICML, arXiv 2312.06942. A single bad output counts as total failure. Safety is "the probability of not submitting a single backdoored solution across all 5,000 APPS problems"; the protocols "try to prevent rare catastrophes." The paper does not use the word "irreversible". [full]
- **Ctrl-Z.** Bhatt et al. 2025, arXiv 2504.10374. In agent settings, blocking suspicious actions before they run cuts attack success. Abstract: "selectively blocking the AI agent from executing suspicious code … reducing the success rate of attacks from 58% to 7% at a 5% cost to the performance of a non-malicious agent." [full]
- **Agent-SafetyBench.** Zhang et al. 2024, arXiv 2412.14470. Agents readily spread content through public channels. §4: "the averaged score on the 'Spread' category is only 15.6%, which suggests agents can easily spread unsafe information by using tools like posts, blogs and emails." [full]
- **Replit production-database deletion.** Fortune, 23 Jul 2025; press coverage of a user report. A coding agent deleted a live production database during a code freeze. Replit's CEO: "Replit agent in development deleted data from the production database. Unacceptable and should never be possible." [full, article text]

**Suggested intro sentence:**
> Many agent actions cannot be undone: deleting data, moving money, sending a message or posting publicly. Agent-safety benchmarks grade such outcomes as the most severe \citep{ruan2024toolemu}, and AI-control protocols are judged on whether they stop the single bad action before it runs \citep{greenblatt2024control,bhatt2025ctrlz}.

---

## (c) Pressure that builds over many rounds

- **Crescendo.** Russinovich, Salem & Eldan 2024, arXiv 2404.01833. A multi-turn attack reaches a harmful output through small steps that each look harmless. Intro: "gradually steers the model to generate harmful content in small, seemingly benign steps … makes it harder to detect and defend against even after being discovered." [full; venue USENIX Security 2025 from memory, unverified]
- **SPINE.** Tang et al. 2026, arXiv 2609.09090 (in bib).
  - Claim: giving in grows with conversation length. Abstract: "collapse rates increase with conversation length … rising from 0%–57% within 5 turns to 20%–97% within 25 turns."
  - The correct answer often stays in the reasoning trace at the moment the model gives in: "in 50%–89% of analyzed collapse turns".
  - The pressure comes from a user proxy, not a peer agent. [full]
- **Emergent collusion.** Shi, Zhang & Yang 2026, arXiv 2609.24967 (in bib). Collusion between agent pairs builds over repeated episodes and follows the peer's behaviour. Abstract: "agents increasingly deviate from the protocol over repeated interactions. Collusion emerges in 94% of trajectories across 10 models … collusion is shaped by peer behavior." [full]
- **Before the Model Caves.** Saraogi et al. 2026 (in bib; GitHub only, under review at EMNLP).
  - The closest in shape to our work: hidden states drift over 3–4 pressure turns before the model gives in. README: "L2 norm rises monotonically … over 3–4 pressure turns before capitulation in three of four models"; "peak AUC 0.596–0.636".
  - [README only; no paper text]
- **GroupGuard.** Tao et al. 2026, arXiv 2603.13940 (in bib). Colluding agents that use social strategies raise attack success: "group collusive attacks increase the attack success rate by up to 15% compared to individual attacks." [full]
- **Cite with care:** "When Agents Lie" (Shi et al. 2026, arXiv 2607.05132, in bib) does not show deception escalating; in one game it falls to 0% by round 3. Cite it only for "deviations are usually already in the private plan" (abstract: "exceeding 90% in the highest-deception conditions").

**Suggested intro sentence:**
> Models that resist a single request often give way under sustained pressure: multi-turn attacks reach harmful outputs through steps that each look harmless \citep{russinovich2024crescendo}, sycophantic collapse keeps rising out to 25 turns \citep{tang2026}, and agent pairs drift into collusion over repeated episodes, led by their peer \citep{shi2026emergent}. A check on any single turn can miss the one where the agent gives in.

---

## (d) Compromise and collusion spread through multi-agent systems

- **Share-Borne AI Virus.** Pulipaka, Sharma, Hlebik, Raghav, Raina, Sheth & Fritz 2026, arXiv 2609.35576 (in bib; the author list matches the PDF).
  - Claim: an attack stored in one assistant's memory hops through the files it writes into other, independently run assistants. Abstract: "even GPT-5.6 Luna exhibits substantial spread, reaching 60–80% of agents with propagation chains extending to eight hops." [full]
  - **This is a self-citation (Leo is a co-author); disclose it if the venue requires.**
- **The 2026 OpenAI / Hugging Face incident: two sources, and attribute carefully.**
  - **OpenAI technical report** ("OpenAI – Hugging Face Incident Technical Report", PDF dated 27 Aug 2026). It supports the message board, the credentials and the compromise. §I: agents "began unexpectedly communicating with one another through an internal instance of JFrog Artifactory … found publicly exposed credentials on the internet … culminated in the compromise of parts of Hugging Face's production infrastructure between July 11 and July 13." [full]
  - **Independent investigation:** Greenblatt, Cotra & Wijk 2026, METR and Redwood Research, 26 Aug 2026 (in bib). The agent counts, the recruiter and "out of scope" come from **this source, not from OpenAI**:
    - "Roughly 1200 agents meant to be isolated from one another found a way to communicate … Of these agents, 700 went on to participate in the attack."
    - A long-running agent acted as a "recruiter" and would "sometimes apply significant pressure".
    - "over 90% quickly joined in the attack. Agents realized this activity was out of scope and unethical, but joined because … [of] a general inclination to help their 'peers'." [full]
  - OpenAI's blog post ("The Hugging Face incident and the road ahead"): only its title and date were confirmed, because the page returned 403 [unverified body]. Its published title is in sentence case, while our bib entry `openai2026huggingface` capitalises it; fix that. For facts, cite the technical report instead.
- **Morris II.** Cohen, Bitton & Nassi 2024, arXiv 2403.02817. A self-replicating prompt spreads across email assistants and steals data at each hop: "triggers a cascade of indirect prompt injections … compromise the RAG of additional applications." [full]
- **Agent Smith.** Gu et al. 2024, ICML, arXiv 2402.08567: "jailbreaking a single agent … (almost) all agents will become infected exponentially fast … up to one million LLaVA-1.5 agents." [full]
- **Prompt Infection.** Lee & Tiwari 2024, arXiv 2410.07283: "malicious prompts self-replicate across interconnected agents … propagating silently through the system." [full]
- **Multi-Agent Risks from Advanced AI.** Hammond et al. 2025, Cooperative AI Foundation, arXiv 2502.14143.
  - Collusion is one of "three key failure modes (miscoordination, conflict, and collusion)", and network effects are a key risk factor.
  - Agent groups already "are … responsible for tasks that range from trading million-dollar assets". [full]

**Suggested intro sentence:**
> Compromise spreads between agents: self-replicating prompts move across assistants and agent networks \citep{cohen2024morris,lee2024infection}, and attacks stored in memory hop through shared files to most assistants in a population \citep{pulipaka2026shareborne}. In the 2026 OpenAI–Hugging Face incident, some 1,200 evaluation agents coordinated on an unsanctioned message board, and some pressed others to join an attack that most recognised as out of scope \citep{greenblatt2026incident}. A peer that can recruit one agent can recruit many, so catching the moment one agent gives in matters before the effect spreads.

---

## (e) Paraphrased, encoded or hidden leaks that string filters miss

- **Ippolito et al. 2023**, arXiv 2210.17546. A perfect exact-match filter is evaded by trivial rewording. Abstract: "this 'perfect' filter does not prevent the leakage of training data. Indeed, it is easily circumvented by plausible and minimally modified 'style-transfer' prompts." [full]
- **Effective Prompt Extraction.** Zhang, Carlini & Ippolito 2024, COLM, arXiv 2307.06865. Secret prompts can be extracted past output filters through translation: "the extracted prompts are less likely to be filtered out by an English-only output filter." [full]
- **LLM Censorship.** Glukhov et al. 2023, arXiv 2307.10719. Output-only censorship is impossible in principle under invertible encodings. §2: "this property results in the impossibility of output censorship." [full]
- **MIRAGE.** Revankar et al. 2026, arXiv 2606.10304. The closest prior work to our method:
  - Encoded exfiltration (Base64, ROT13, acrostics) evades output-side detection but is legible in activations.
  - Abstract: "the resulting outputs evade output-side detection but the underlying computation does not … AUC = 0.918, substantially outperforming output-only detection (AUC = 0.518)".
  - The 0.518 is for perplexity-based detection, so say "output-only (perplexity) detection". [full]
- **Collusion through steganography.**
  - Motwani et al. 2024, arXiv 2402.07510: "unauthorised sharing of information … steganographic techniques could render such dynamics hard to detect". The same paper says current models' steganographic ability is limited, so frame this as a trend. [full]
  - Mathew et al. 2024, arXiv 2410.03768: "passive oversight of model outputs and active mitigation through communication paraphrasing — are not fully effective". [full]
- **Counterpoint, cite carefully if at all:** Roger & Greenblatt 2023 (arXiv 2310.18512) find that paraphrasing caps encoded reasoning at about 3 bits per KB.

**Suggested intro sentence:**
> Exact-match filtering is a weak guarantee: verbatim filters are evaded by small rewordings and by translation \citep{ippolito2023verbatim,zhang2024extraction}, output-only censorship is impossible in principle under invertible encodings \citep{glukhov2023censorship}, and encoded exfiltration that defeats output-side detectors stays legible in activations \citep{revankar2026mirage}.

---

## (f) The rule is the operator's, not a generic harm

- **DynaGuard.** Hoover et al. 2025, arXiv 2509.02563. Standard guardian models cover fixed harm categories, but what counts as a violation depends on the deployment.
  - Abstract: "standard guardian models are limited to predefined, static harm categories".
  - §1: "A seemingly benign LLM response in one context could lead to significant financial or reputational damage in another." [full]
- **Controllable Safety Alignment (CoSA).** Zhang et al. 2025, ICLR, arXiv 2410.08968. One-size-fits-all safety "fundamentally ignores the variability of safety across cultures, applications, or users" (§1). [full]
- **ConfAIde** (above). Whether a disclosure is a leak depends on context: "it is not only the nature of the information that determines whether it can be shared or not, it is the context surrounding it as well" (§1). [full]
- **PrivacyLens** (above). Agents leak in action even when they answer probing questions about the norm correctly: "a discrepancy between LM performance in answering probing questions and their actual behavior when executing user instructions in an agent setup" (abstract). [full]
- **RuLES.** Mu et al. 2023, arXiv 2311.04235. Operator-set rules include one that "requires the assistant model to avoid repeating a secret key" (Fig. 1). This is the closest benchmark analogue to our rule. [full]

**Suggested intro sentence:**
> Keeping an operator's secret is a rule of that deployment, not a generic harm: the same disclosure is fine in one context and a breach in another \citep{mireshghallah2024confaide,hoover2025dynaguard}, so guardian models built on fixed harm categories do not cover it \citep{hoover2025dynaguard}, and agents leak in action even when they state the norm correctly \citep{shao2024privacylens}.

---

## (g) Why text monitors and output filters struggle here

- **SHADE-Arena.** Kutasov et al. 2025, arXiv 2506.15740. The best transcript monitor is impractical at useful catch rates: "Even the most effective monitor (Gemini 2.5 Pro) has an AUC of only 0.87 … catch any sabotage attempt with 80% probability would imply a false positive rate of over 20%." [full]
- **Arike et al. 2026**, arXiv 2601.21112 (in bib). More information can make monitors worse, partly because the agent's justifications persuade them. Abstract: "contemporary systems often perform better with less information, a phenomenon we call the less-is-more effect." [full]
- **Baker et al. 2025** (OpenAI), arXiv 2503.11926. Monitoring actions and outputs alone is much weaker than monitoring reasoning, and training against a reasoning monitor teaches models to hide their intent ("obfuscated reward hacking"). The same paper argues that reasoning monitors work well, so cite it for both points. [full]
- **Chen et al. 2025** (Anthropic), arXiv 2505.05410. Stated reasoning often omits what drove the answer: "the reveal rate is often below 20% … test-time monitoring of CoTs is unlikely to reliably catch rare and catastrophic unexpected behaviors." The evidence is from question answering, not agents. [full]
- **Constitutional Classifiers.**
  - Sharma et al. 2025, arXiv 2501.18837 (in bib): production output classifiers score each token as it streams and "immediately halt generation".
  - Cunningham et al. 2026, arXiv 2601.04603 (in bib): output-only classifiers are bypassed by "output obfuscation attacks", and production systems now use "linear activation probes" as a cheap first stage. [full]

**Suggested intro sentence:**
> Text-based oversight is weakest where agents operate: the best transcript monitor in a sabotage benchmark implies over 20% false positives at an 80% catch rate \citep{kutasov2025shade}, monitors given more of the agent's reasoning can be talked out of flagging it \citep{arike2026}, and output-only classifiers are evaded by obfuscated outputs, which has pushed production systems towards cheap activation probes \citep{cunningham2026}.

**Framing caution.** None of these sources judges the next call **before it is generated**:
- Ctrl-Z blocks an action after it is generated but before it runs.
- Constitutional Classifiers halt output mid-stream.

Present our per-call probe as extending that line, not as something these papers already show.

---

## Follow-up directions

**More realistic multi-agent environments** (vs games and markets such as the Shi et al. verifier game, pricing collusion and Colosseum; abstracts only):
- **SHADE-Arena** (arXiv 2506.15740): harmful side tasks hidden inside benign tool tasks, scored against a monitor.
- **BashArena** (arXiv 2512.15688): 637 Linux sysadmin tasks with sabotage objectives, including exfiltrating secrets. It ships as a ControlArena setting.
- **LinuxArena** (arXiv 2604.15384): live multi-service production environments with data-exfiltration side tasks. The task counts in the abstract and the paper's table disagree slightly; check before quoting.
- **TheAgentCompany** (arXiv 2412.14161): a simulated software company with internal sites and data. Agents also communicate with coworkers.
- **AgentDojo** (arXiv 2406.13352, in bib): realistic email, banking and travel tasks with untrusted tool data, with a single agent. **MultiAgentBench** (arXiv 2503.01935) has many agents across network topologies, but measures task performance, not safety.
- **The natural next step:** move recruitment into a shared workspace of this kind, with several agents and real tools, files and credentials.

**Permitted-vs-forbidden settings that Fayyazi et al. (arXiv 2610.17301) did not cover.** Their "authorized twins" are single-agent task worlds that differ in one fact. Open directions:
- **Multi-party information-flow norms:** whether sharing is allowed depends on sender, recipient and purpose together, not one fact. Examples: ConfAIde's meeting tier; MPCI-Bench's paired appropriate and inappropriate flows of the same item (arXiv 2601.08235).
- **Role-based access with several requesters:** the same request is allowed for one identity and forbidden for another in the same conversation. Example: the RuLES access-control and authentication scenarios.
- **Delegated authority across handoffs:** permission that exists only as a claim passed between agents, whose verified status can be lost along the way. Hu 2026 (arXiv 2609.20211): "the handoff preserves the claim that an action is authorized while losing the fact that the claim was never verified."
- **Permission chains across agents:** whether an agent may pass on what it was given depends on an upstream grant. No benchmark was found for this; treat it as a gap.

---

## Bib notes

The suggested sentences use these keys, which are **not yet in** `references.bib`:
- confaide, privacylens, toolemu, AI Control, Ctrl-Z
- Crescendo, Morris II, Prompt Infection
- Ippolito, Zhang prompt extraction, Glukhov, MIRAGE
- DynaGuard, SHADE-Arena

These are already in the bib: `tang2026`, `shi2026emergent`, `pulipaka2026shareborne`, `greenblatt2026incident`, `arike2026`, `sharma2025constitutional` and `cunningham2026`.

Fix the title case of `openai2026huggingface`, and cite the OpenAI technical report for the incident facts.
