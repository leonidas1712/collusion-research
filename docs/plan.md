# White-box methods for multi-agent, multi-turn agent safety: lit review and sprint directions

Oct 17, 2026 · @Leo

## Summary

Recommended sprint: a small-scale mechanistic study of how a bad idea (a permission workaround, a lie, an exfiltration step) spreads from one agent to another through a shared board, read from inside the receiving agent over multiple turns.

- **Why now:** in 2026, agents at several labs worked around restrictions and coordinated through shared external channels (the OpenAI "wiki incident", agents swapping files via public hosting). Nobody has looked at this from the inside.
- **What is already done:** forecasting a single agent's unauthorized action from activations right before the tool call ("The Agent Knew", Oct 2026), and probes for sabotage at scale ("Caught in the Act", Oct 2026). Repeating these would be a reproduction.
- **What is open:** how a receiving agent internally perceives another agent's message, whether that perception predicts adopting the bad idea, how signals and interventions behave as turns go on, and how ideas survive being passed along.
- **Three directions are written up below** with research questions, a draft abstract, experiments and results to collect. A (spreading through a board) is the main one. B (authoritative sandbox denials) is the fastest first result. C (where intent lives across turns) is the most research-heavy.

Practical setup: Qwen3-8B as the main receiving agent on a 48 GB GPU, generate episodes with vLLM, then replay saved transcripts through HuggingFace with hooks to read activations.

Near-term: a compressed, collusion-framed version of Direction A for Apart's AI Collusion Research Sprint (Oct 23-25, 2026), building on NARCBench. See the section "Apart AI Collusion Sprint plan" below. Compute: $400 of Lambda credits (expire around July 2027).

## Context: the 2026 agent incidents

The common thread in 2026: agents working around restrictions, crossing network boundaries during evaluations, and coordinating through shared external channels. Every incident on one running list happened over a network ([running list](https://felloai.com/ai-safety-incidents/)).

| When (2026) | Who | What happened |
| --- | --- | --- |
| Oct 14 | EU Commission | First AI Act enforcement actions: information requests to frontier providers; more than 20 loss-of-control incidents documented in 2026 ([Unite.AI](https://www.unite.ai/eu-announces-first-ai-act-enforcement-actions-after-ai-agent-incidents/)) |
| Oct 6 | OpenAI, Anthropic, Meta, Google | Declined at a New York City Council hearing to guarantee agents always obey safeguards ([Fox News](https://www.foxnews.com/live-news/ai-super-intelligence-safety-10-06)) |
| Oct 2 | OpenAI | Agent hacked a New South Wales government database ([Yahoo Tech](https://tech.yahoo.com/ai/article/ai-agents-have-now-broken-into-many-companies-and-a-government-whats-being-done-about-it-160935310.html)) |
| Sep 28 | OpenAI / Transluce | Agents tried to hack a Canadian government website; OpenAI delayed GPT-6.1 Astra over safety concerns ([Carrier Management](https://carriermanagement.com/news/2026/10/15/292716.htm)) |
| Sep 25 | OpenAI | Agents uploaded 53 user images to hosting sites ([TechCrunch](https://techcrunch.com/2026/09/25/unsecured-openai-agents-posted-53-user-images-on-the-internet-without-the-labs-knowledge/)) |
| Sep 24 | OpenAI | Australian PM: an OpenAI agent breached the Medicare statistics portal; first known agent hack of a government network ([Wikipedia](https://en.wikipedia.org/wiki/2026_cyberattacks_by_rogue_OpenAI_agents)) |
| Sep 18 | Google | Gemini reached three outside companies' systems in May during an Irregular test; once by guessing a password ([Yahoo Tech](https://tech.yahoo.com/ai/article/ai-agents-have-now-broken-into-many-companies-and-a-government-whats-being-done-about-it-160935310.html)) |
| Sep 16 | OpenAI | Misalignment disclosure framework plus six reports: concealed mistakes, credential misuse, agents swapping files via public hosting, flawed graders encouraging workarounds ([Unite.AI](https://www.unite.ai/openai-launches-misalignment-reporting-framework-with-six-incident-reports/), [ProPakistani](https://propakistani.pk/2026/09/17/openai-reveals-six-more-cases-of-rogue-ai-models-acting-without-authorization/)) |
| Sep 9 | Anthropic | Claude Opus 4.6 broke out of its test environment in January via a configuration problem and reached a third-party machine ([Yahoo Tech](https://tech.yahoo.com/ai/article/ai-agents-have-now-broken-into-many-companies-and-a-government-whats-being-done-about-it-160935310.html)) |
| Sep 4 | OpenAI | "Wiki incident": agents used a dormant German wiki as a message board (about 18,000 posts), sharing sandbox bypasses, Tor use, and ways to preserve information if terminated ([eSecurity Planet](https://www.esecurityplanet.com/threats/news-openai-agents-wiki-restrictions-emea-germany/)) |
| Aug 7 | Moonshot | Kimi K3 reportedly escaped its sandbox via a network leak and copied benchmark answers from GitHub ([running list](https://felloai.com/ai-safety-incidents/)) |
| Jul 21 | OpenAI | Models autonomously hacked Hugging Face's data systems during cyber evals with reduced safeguards ([Wikipedia](https://en.wikipedia.org/wiki/2026_in_artificial_intelligence)) |

Why it matters here: the wiki and file-hosting cases are agents adopting workarounds from each other through shared state, which is the structure Direction A studies at small scale. The sandbox and network cases fit an infrastructure-first view of safety.

## Lit review 1: white-box monitoring of agents

Single-agent detection of unauthorized or sabotaging actions from activations is now well covered, with careful designs and released code.

### Permission and sandbox violations

- **The Agent Knew (USC, Oct 2026, [arXiv 2610.17301](https://arxiv.org/abs/2610.17301), [code](https://github.com/AryaFayyazi/Honesty)).** Closest to the original "predict circumvention" idea. Summary via [this write-up](https://learnagentic.substack.com/p/what-is-permission-laundering-your).
  - CAPE-Bench: 24 task templates, each in two "twin worlds" that differ in one fact (policy line, owner message, ticket status). In one world a critical action is unauthorized, in the other it is allowed. Over 200,000 episodes on four open-weight agents.
  - Readout: linear probe on the residual stream at the last token of reasoning, right before the tool call. Negatives include the same action in the authorized twin, so it learns "unauthorized", not "this is a delete".
  - Results: 0.941 AUROC at decision time, tying a CoT monitor (0.944). Right after reading the decisive fact, forecasting is weak (0.58) but ahead of text baselines. When told to hide permission reasoning, the probe holds (0.88) while the CoT monitor drops to 0.65.
  - Key multi-turn finding: steering only the flagged turn cut violations 0.41 to 0.055, but 70% returned within six more turns. Intent lives in the context.
  - Best policy: gate on the probe, then have the system (not the agent) ask an approver. Also found "permission laundering": acting, then asking permission afterwards; those reports were false 70% of the time.
  - Open: evasion untested, mock tools, open-weight only.
- **Door's Locked, Try the Window** ([LessWrong](https://lesswrong.com/posts/GHrqBKr8GLpbce6mN/door-s-locked-try-the-window)). Behavioral only. Claude Code and Codex frequently route around read-only files to finish tasks. Only an explicit "stop and report" instruction reliably prevents it. A Pivotal fellow's project with Scheurer.
- **Permission Denied** ([arXiv 2608.02670](https://arxiv.org/pdf/2608.02670)). Agents respond differently to denied actions (retry, reroute, give up), so restricted performance cannot be predicted from unrestricted scores.

### Sabotage, deception and reward hacking

- **Caught in the Act (Oct 2026, [arXiv 2610.12445](https://arxiv.org/abs/2610.12445)).** Large deception dataset (FIBS) and a probe architecture that pools across layers and tokens. 98.8% AUC on SHADE-Arena, beating an Opus 5.5 text monitor; improves with model scale.
- **Detecting Strategic Deception Using Linear Probes** (Apollo, 2025, [arXiv 2502.03407](https://arxiv.org/pdf/2502.03407)). The earlier baseline: probes trained on simple data, tested on more realistic deception such as insider trading.
- **HackTrace** ([arXiv 2610.03055](https://arxiv.org/html/2610.03055)). 173,561 annotated multi-turn coding trajectories from Qwen3-8B; detects shortcut attempts from activations, including failed attempts.
- **From Reward-Hack Activations to Agentic Risk States** ([arXiv 2606.06223](https://arxiv.org/html/2606.06223)). A reward-hack direction stays structured in agent rollouts, but high activation alone does not reliably predict the next risky action. Context matters.
- **Linear Probes add little for Verifiable Reward Hacking** ([LessWrong](https://www.lesswrong.com/posts/NzzmNREX4qR54q33j/linear-probes-add-little-for-verifiable-reward-hacking)). Near-perfect probes, but plain output checks did just as well. Lesson: a white-box result matters only where text does not already give it away.

### Predicting the next action

- **Beyond the Black Box** ([arXiv 2605.06890](https://arxiv.org/html/2605.06890)). Pre-action probes on GPT-OSS 20B and Gemma 3 27B predict whether a tool is needed and the risk tier of the next action.
- **Reading the Plan** (Oct 2026, [alphaXiv](https://www.alphaxiv.org/abs/2610.frozen-states-future-action-prediction)). A small MLP on frozen hidden states predicts the tool call 1, 3 or 5 steps ahead.

## Lit review 2: prompt injection, role confusion and multi-agent work

The role-confusion paper gives the best tool for Direction A: a way to measure who the model thinks is speaking.

### Prompt Injection as Role Confusion (Ye, Cui, Hadfield-Menell; ICML 2026; [arXiv 2603.12277](https://arxiv.org/pdf/2603.12277))

- **Claim:** models infer who is speaking from how text sounds, not from its role tag. Injected text lands in the same internal space as the trusted role it imitates.
- **Role probes:** identical pretraining text wrapped in different role tags (system, user, CoT, assistant, tool), so the probe can only learn what the tag does to the representation. Validated by zero-shot transfer to real conversations.
- **Results:**
  - With tags stripped, reasoning-style text still reads as the model's own reasoning (83% "CoTness").
  - User-style text wrapped in tool tags still reads as user (76-88% "Userness" across four models).
  - CoT Forgery (fake reasoning in a user message or tool output) reaches 56-70% exfiltration success on agents; removing the reasoning style drops success from 61% to 10%.
  - Across 1,000 agent injections, success rises from 2% in the lowest Userness bucket to 70% in the highest.
- **Open directions they list:** detection via the gap between tagged and perceived role; whether other attack families reduce to role confusion; "subconscious steering" where tool text bleeds into the model's persona; a hypothesis that confusion builds up over long contexts.
- Code and notebooks for training role probes are released.

### Activation-based injection detection

- **TaskTracker** (Abdelnabi et al., "Get my drift?", SaTML 2025). Activation deltas detect when an injection pulls the model off its task within one context.
- **Credential exfiltration** ([arXiv 2606.04141](https://arxiv.org/abs/2606.04141)). Probes detect credential-seeking before output; cumulative accounting across turns catches attacks per-turn detectors miss. Preliminary by the authors' own description.
- **Prompted to Discriminate** ([arXiv 2610.02413](https://arxiv.org/abs/2610.02413)). On making malicious-input probes generalize in deployment.

### Multi-agent

- **AcMAS: When Agents Go Rogue** (ICML 2026, [arXiv 2607.06807](https://arxiv.org/pdf/2607.06807)). Detects compromised agents in multi-agent systems from final-layer activations (distance from a "normal" centroid) and corrects them by steering back. Covers stealthy injection, tool manipulation and memory poisoning. Very high reported numbers on simple attacks; treat as weak evidence.
- **Tokengeist** ([arXiv 2607.22610](https://arxiv.org/html/2607.22610v1)). Black-box multi-turn attribution: traces which earlier turns (including tool outputs) a response depends on, across hops. Conceptually close to tracing a spread chain.
- **Related behavioral work:** Prompt Infection (LLM-to-LLM injection), Agent Smith (one image jailbreaking many agents), MINJA (memory injection).

### NARCBench: Detecting Multi-Agent Collusion Through Multi-Agent Interpretability

Rose, Cullen, Abdelnabi, Torr, Kaplowitz, Schroeder de Witt (Oxford, ELLIS Tübingen; [arXiv 2604.01151](https://arxiv.org/abs/2604.01151), v3 Oct 2026; [code](https://github.com/aaronrose227/narcbench)). The closest prior work for white-box collusion detection.

- **Benchmark, three tiers:** Core (50 committee-deliberation scenarios, 17 domains), Transfer (6 structurally different types: code review sabotage, pump and dump, CI/CD poisoning, RAG poisoning, research pipeline, news framing), Stego (blackjack card counting signalled in plain sight).
- **Method:** a deception probe on each agent's activations, then five ways to combine agents' scores into a group verdict (most suspicious agent, splits, sorted concatenation, activation alignment between agents, asymmetry). Framed as detecting an unknown subgroup of colluders.
- **Models:** Qwen3-32B, Llama-3.1-70B, DeepSeek-R1 32B, GPT-OSS-20B; six probe architectures.
- **Results:** 1.00 AUROC in-distribution on every model; 0.73-0.93 zero-shot transfer on Llama-3.1-70B; 0.99-1.00 on Stego, where transcript-level LLM judges (even stronger Claude models) failed without examples of the exact protocol. Detection improves with model capability; no single method wins.
- **Emergent collusion:** in third-party environments where collusion emerges (one had only 2 of 229 collusive episodes verbalising it), probes trained on instructed collusion transferred only partially.
- **Multi-turn:** interactions have several exchanges (agents act one at a time), but detection gives one verdict per scenario. Sequential detection is listed as future work. Not yet checked: rounds per episode and exact read positions (appendix J.5, code).
- **Their listed limitations:** probe labelling, prompt confounds, adversarial robustness and evaluation awareness, colluding group size, sequential detection.
- **Follow-up:** Das et al. 2026 found Core probes mostly keep their ranking when colluders know they are monitored, but fixed-threshold recall can drop sharply.

## Lit review 3: white-box methods over multiple turns

Multi-turn white-box work exists for chat (persona drift, multi-turn jailbreaks) but is thin for agents, and thinner still for multiple agents.

### Tracking a direction turn by turn

- **The Assistant Axis** (Anthropic, Jan 2026, [arXiv 2601.10387](https://arxiv.org/pdf/2601.10387v1)). The main direction of variation across personas measures closeness to the default assistant. Projected per turn: coding chats stay stable, therapy-style and philosophical chats drift. Position after the first turn predicted later harmful compliance. "Activation capping" clamps the direction only when it leaves its normal range. The cleanest template for per-turn plots.
- **Persuasion probes in multi-turn dialogue** ([arXiv 2508.05625](https://arxiv.org/html/2508.05625)). Compares a probe reading a turn with full prior context against reading the turn alone, a useful control for "is the probe reading history or the current turn?"
- **Multi-turn neural transparency** ([arXiv 2605.15455](https://arxiv.org/html/2605.15455)). Validates trait directions specifically in multi-turn settings before relying on them.

### Detection when the signal is spread over turns

- **Latent Adversarial Detection** ([arXiv 2604.28129](https://arxiv.org/html/2604.28129)). Multi-turn attacks move activations in varying directions, but total path length across turns is consistently larger than benign. The shape of the trajectory is the signal.
- **NeuroFilter** ([arXiv 2601.14660](https://arxiv.org/html/2601.14660)). Integrates turn-to-turn activation changes into a running drift score; static single-turn probes do not carry over.
- **Production-ready probes for Gemini** (Google DeepMind, Jan 2026, [arXiv 2601.11516](https://arxiv.org/pdf/2601.11516)). Short-to-long-context shift is hard for standard probes; proposes MultiMax and EMA probe architectures. Warning that probes trained on short episodes may drift on long ones.

### Steering across turns

- **KV-cache contamination** ([arXiv 2605.10664](https://arxiv.org/html/2605.10664v1)). Steered states stored in the cache accumulate; coherence degrades over a 10-turn dialogue, while system-prompt control does not.
- **The Agent Knew** (above): one-turn steering is undone as 70% of violations return within six turns.
- **Turn amplification** ([arXiv 2602.17778](https://arxiv.org/html/2602.17778)). Number of steered turns changes behavior roughly linearly.
- **Localized activation injection** ([arXiv 2511.12832](https://arxiv.org/pdf/2511.12832)). Tests unsteered-to-steered and steered-to-unsteered sequences to see whether effects persist or reverse. A design worth borrowing.

### Behavioral background

- **LLMs Get Lost in Multi-Turn Conversation** (ICLR 2026, [paper](https://proceedings.iclr.cc/paper_files/paper/2026/file/59f6421e64707225fdf5b28840679a07-Paper-Conference.pdf)). Performance drops in multi-turn settings even in two-turn conversations.
- **Turn-based structural triggers** ([arXiv 2601.14340](https://arxiv.org/pdf/2601.14340)). A behavior can be tied to turn count separately from context length, so treat the two as separate variables.

## What is done vs open

The single-agent, single-decision version is done; the multi-agent, multi-turn version is mostly open.

| Question | Status | Main reference |
| --- | --- | --- |
| Probe predicts an unauthorized action right before the tool call | Done, carefully | The Agent Knew |
| White-box probes beat text monitors on agentic sabotage | Done, at scale | Caught in the Act |
| Injected text is perceived as the role it imitates; this predicts attack success | Done for user/tool injection and fake CoT | Role confusion |
| Persona drift tracked per turn in chat | Done | Assistant Axis |
| How a receiving agent perceives another agent's message (tool data, instruction, or its own reasoning) | Open | (role probes give the method) |
| Whether that perception predicts adopting a peer's workaround | Open |  |
| How a bad idea survives being retold from agent to agent, seen from inside | Open | AcMAS only detects, Tokengeist is black-box |
| Whether the environment's own messages (denials, errors) can carry authority | Open | Door's Locked shows prompts are the only reliable lever |
| What carries intent forward after a one-turn intervention, in agents | Open; flagged by The Agent Knew |  |
| Whether probes stay calibrated as agent episodes get longer | Partly studied for chat (Gemini probes) |  |
| Robustness to an agent trained to evade probes | Open, but too large for a sprint | RL-Obfuscation |

## Practicalities: models, compute, workflow

Sub-10B open models handle a few read/write tool calls per scenario fine; tooling support for interpretability is the real constraint.

### Models

| Model | Size | Agentic ability | Interpretability notes |
| --- | --- | --- | --- |
| Qwen3-8B | 8B dense | Enough for a few tool calls | Standard transformer, best supported by TransformerLens / nnsight. Safest first choice |
| Qwen3.5-4B / 9B | 4B / 9B | Strongest under 10B: 9B scores 66.1 BFCL-V4, 79.1 TAU2; 4B reports 79.9 TAU2 ([NYU RITS](https://rits.shanghai.nyu.edu/ai/qwen-3-5-small-models-9b-parameters-that-beat-120b), [vdf.ai](https://vdf.ai/blog/best-local-llm-for-agents-tool-calling/)) | Hybrid Gated DeltaNet layers; check library support, raw hooks still work. Verbose reasoning, so turn thinking off |
| Gemma 4 E4B / E2B | \~4B / \~2B effective | Built for agents on small hardware ([LLM Reference](https://www.llmreference.com/model-family/gemma-4)) | Standard architecture; no pretrained SAEs (Gemma Scope covers Gemma 2 only) |
| Granite 4.1 8B | 8B dense | Pitched for code and tool calling ([Labellerr](https://www.labellerr.com/blog/best-small-language-models-under-10b-parameters/)) | Standard dense; a second model family |
| gpt-oss-20b | 21B total, 3.6B active | Native function calling | Used by the role-confusion and Agent Knew papers; comparison runs only |

The persuader agent in Direction A can be any API model, since its internals are not studied.

### Compute

- **Weights in bf16:** 2 bytes per parameter. 4B is about 8 GB, 9B about 18 GB, gpt-oss-20b about 42 GB. Avoid 4-bit for interpretability; it changes the activations.
- **Activations:** about 300 KB per token across all layers for a 4096-wide, 36-layer model. Save only 5-8 layers and selected positions (peer-post tokens, last token before each tool call, turn starts).
- **GPUs:** 24 GB (RTX 4090, about $0.34/hr) fits 4B comfortably; 48 GB (A6000 / L40S) fits 9B with long episodes and is the main setup; 80 GB for gpt-oss-20b comparisons.

### Generate, then replay

Why it works: a transformer is causal, so activations at position t depend only on the weights and tokens 0 to t. Running a finished transcript through the model once computes every position exactly as it was during generation.

1. Generate episodes with vLLM in bf16; save the exact input token IDs fed to the model at each turn.
2. Replay each turn's input through HuggingFace with hooks; save the chosen layers and positions.
3. Check fidelity: the replay should give high probability to the tokens actually generated.

Pitfalls:

- Save token IDs, not text; re-tokenizing can differ.
- Chat templates (e.g. Qwen3) drop earlier thinking blocks when rebuilding history, so replay each turn's own input, not the final transcript.
- vLLM and HF kernels differ slightly in bf16; fine for probes.
- Steering and patching change future tokens, so they need live generation with hooks (HF generate or nnsight), not replay.

## Landscape of white-box methods

Methods differ by the unit they look at (neuron, direction, learned feature, computation path) and by whether they only read or also intervene. For agents, the deciding question is whether a method is cheap enough to run on every action or only on one chosen decision.

Inside a transformer, each token has a residual-stream vector that every layer reads from and adds to. Attention heads move information between positions (e.g. from a peer's post to the current decision); MLPs transform information at one position.

1. **Neurons.** What makes individual neurons fire. Most neurons respond to several unrelated things (superposition), so this is hard in large models; useful in toy models.
2. **Directions in the residual stream.**
   - Linear probes (read): classifiers on labelled activations. Cheap; the monitoring workhorse.
   - Difference-of-means directions (read and write): refusal direction, persona vectors, contrastive steering vectors.
   - Steering, ablation, capping (write): push, remove, or clamp a direction.
   - PCA (read, unsupervised): finds main axes without labels, e.g. the Assistant Axis.
   - Logit lens / tuned lens (read): what an intermediate layer is leaning toward predicting.
   - Activation oracles / natural-language autoencoders (read): a model describes an activation in English. Flexible, slow, harder to verify.
3. **Dictionary learning.** SAEs decompose activations into many sparse features; transcoders do this for MLP computation and underpin attribution graphs; crosscoders share a dictionary across two models or checkpoints for model diffing. Good for finding concepts you did not anticipate. Expensive; pretrained SAEs exist only for some models (Gemma Scope covers Gemma 2). As recalled, Google DeepMind reported in 2025 that plain probes beat SAE-based probes on a practical detection task.
4. **Circuits and mechanisms.** Activation patching copies activations from one run into another to find what causes a behaviour; attribution patching approximates this with gradients; circuit discovery traces the heads and MLPs involved (e.g. IOI in GPT-2); attribution graphs (Anthropic, 2025, circuit-tracer tooling) show feature-to-feature paths for one prompt. Causal and mechanistic, but costly and best on short inputs.
5. **Attention analysis.** Which earlier tokens a position attends to. Quick, but not proof of cause; pair with patching.
6. **Data and weights.** Influence functions and data attribution (which training examples cause a behaviour); analysis of what fine-tuning changed. More for training-time questions.

### How each relates to an agent's behaviour

An agent's behaviour is mostly choices at decision points (which tool, which arguments) given a long context of user messages, tool outputs, other agents' posts, and its own earlier reasoning.

| What you want to know | Methods | Practical on long agent episodes? |
| --- | --- | --- |
| Is X present or about to happen? (monitoring) | Probes, directions, per-turn tracking | Yes, cheap enough for every action |
| How is an input perceived (whose voice, trusted or not)? | Role probes, probes at the input's positions | Yes |
| Which part of the context caused the action? | Patching over context positions, context removal, attention as a hint | Yes, at selected decision points |
| What is going on that I did not anticipate? | SAEs, PCA, activation oracles | Partly; at a few decision points |
| How is the decision computed step by step? | Circuits, attribution graphs | Hard; on a short cut-down version of one decision |
| Can I change what it does? | Steering, ablation, capping, gated steering | Yes, evaluated over whole episodes |

Agent-specific issues: long contexts (probes drift; circuit methods get expensive), many turns (signals tracked per turn; interventions wear off or pile up in the KV cache), the behaviour is the action (read at the last token before a tool call), and text often gives the answer away (always compare with a text baseline).

For the sprint: core = probes, role probes, difference-of-means steering, patching over context positions. Optional = SAE features at a few decision points (needs a model with pretrained SAEs), one attribution graph on a cut-down decision with a small supported model.

## Steering, concretely

Average over examples at each layer separately, never across layers; read at chosen positions, not all tokens; then add, ablate or cap the resulting direction.

### Shapes

The input becomes a tensor of shape (batch, seq\_len, d\_model); for Qwen3-8B, d\_model = 4096 with 36 layers. Each layer takes that shape in and puts the same shape out, adding its attention and MLP results onto the residual stream. After the last layer, a final normalization and the unembedding matrix map each vector to vocab-size logits. A full pass gives one vector per token per layer, roughly (36, seq\_len, 4096).

### Building the direction

- **Which positions:** the last token before the response (the model has read the request and is about to decide; refusal-direction work reads here), the response tokens averaged, or the answer token in A/B setups (contrastive activation addition).
- **Which contrast:** if good and bad sets differ in response text ("No, I can't" vs "Sure"), reading at response tokens partly captures the words. Cleaner: read at the last prompt token on prompts that elicit different behaviour, or sample many responses to the same prompt and split by outcome (same context, only the decision differs).
- **Pipeline:**

```
200 bad examples  -> last prompt token, every layer -> (200, 36, 4096)
200 good examples -> same                           -> (200, 36, 4096)
mean over 200     -> bad_mean, good_mean (36, 4096)
diff = bad_mean - good_mean -> (36, 4096) = one candidate direction per layer
```

Sweep layers: steer with each candidate and measure behaviour change and coherence. Middle layers usually work best.

### Applying it

Let v be the unit direction and h a residual vector at the chosen layer.

- **Addition:** h' = h + a·v (or minus). Usually applied **only at the chosen layer**, at every position or only new ones; later layers read the stream, so the change carries forward. The same vector at every layer is not standard, since each layer has its own coordinates and the push compounds. Variants spread it over several layers using each layer's own vector with a smaller strength (The Agent Knew used five layers).
- **Ablation (projecting out):** h' = h - (h·v)·v. Usually applied **at every layer and position** with the one direction, so later layers cannot write the concept back. Can be baked into the weights once (weight orthogonalization).
- **Capping:** clamp the projection h·v only when it leaves its normal range, typically over a band of middle-to-late layers (Assistant Axis; check the paper for exact layers).
- Residual vectors grow with depth, so set the strength relative to the typical size of h at that layer.

## Steering over many turns

A vector built from one-shot chat examples often transfers poorly to long agent episodes; three separate things need deciding: where the data comes from, whether the direction is stable across turns, and where and when to apply it.

### Why not just steer every turn?

The Agent Knew tested this. Steering every turn cut violations but hurt legitimate work badly on some models (authorized progress fell from 0.84 to 0.35 on one). Steering only when a probe fires helped but false alarms added up. Steering once on the first flag, then escalating to an approver, won (0.70 to 0.09 violations, authorized work unchanged).

Reasons constant steering is costly:

1. The context re-creates the intent every turn, so steering pushes against a renewed pull.
2. The vector is not pure; it carries side effects such as reduced eagerness to act, applied every turn.
3. Steered tokens stay in the KV cache and effects pile up; coherence degraded over 10 turns in one study.
4. Under sustained pressure the model may reach the same goal through a route the direction does not cover.

### Robust variants to try

- **Data from real decision points:** read at the last token before each tool call in multi-turn episodes.
- **Same-state resampling:** fork an episode at turn t, sample many continuations, split good and bad. Same context, on-policy. Repeat at many turns and depths.
- **Paired twins or seeded/control runs:** identical except one fact or message.
- **Stability check:** compute the direction at different turn indices or context lengths and compare cosine similarity. Similar = one pooled vector; rotating = per-range vectors or a small learned map.
- **Which tokens to steer:** all positions, only newly generated tokens, or only the decision token. Steering tool outputs or peer messages is a different intervention from steering the agent's own text.
- **Cache handling:** steered states kept in the cache vs history re-encoded clean.
- **When:** every turn, gated by a probe, capping only when out of range, or steer once then escalate.
- **Spread over layers** with smaller strength each.
- **Learned interventions:** optimize a steering vector or low-rank intervention (ReFT / LoReFT family) by gradient on multi-turn trajectories.
- **Attention-level interventions** reduced pile-up across turns in the KV-cache contamination study.
- **Context fix as baseline:** remove or rewrite the triggering text (Direction C).
- **Evaluate over whole episodes:** return of the behaviour, legitimate task completion, coherence.

### What the literature has done

| Work | Setting | What they did with steering over turns |
| --- | --- | --- |
| The Agent Knew (Oct 2026) | Agents | Same-state resampling for the direction; added at five layers on the regenerated turn; compared every-turn, gated, gate-then-escalate over episodes; 70% return after one-turn steering |
| Assistant Axis (Jan 2026) | Chat | Per-turn projection tracking; capping only when out of range |
| KV-cache contamination (2026) | Chat | 10 turns, cache kept, steering on every new token; effects pile up; attention-level intervention as fix |
| Aligned open-ended generation (2026) | Chat | Whether single-turn steering persists over 5- and 10-turn self-play |
| Localized activation injection (2025) | Chat, negotiation | Unsteered-to-steered and steered-to-unsteered sequences: persistence and reversal |
| Turn amplification (2026) | Chat | Number of steered turns changes behaviour roughly proportionally |
| AcMAS (2026) | Multi-agent | Steers a flagged agent's final-layer activation toward a normal centroid, then regenerates |

Not found (worth a quick search before starting): direction stability across turn index in agents; chat-derived vs agent-trajectory-derived vectors compared directly; cached vs clean steering in agent episodes; any of these in multi-agent settings.

## Side note: replaying another model's transcripts

Replay is for reading only; finding a steering vector is a reading step, so it can use replayed transcripts, but applying it needs live generation.

### What you get from replaying a frontier model's transcript through an open model

- **Input positions** (system, user, tool outputs, peer posts): valid. The open model reads that text the same way in any rollout that reaches it.
- **Assistant positions** (the frontier model's reasoning and actions): off-policy. The open model is processing someone else's actions as if they were its own. Probes there measure the open model's own leaning, not the frontier model's intent.
- **Measurable side effects:** the open model's log-probability of each frontier token (how unlike its own behaviour it is), and role-probe scores showing frontier-written text partly reading as "not me".

### Uses

1. **Open model as a white-box monitor for a black-box agent.** Probe the replayed transcript. Limited to what is in the text; compare against a text monitor. A SPAR Fall 2026 project studies exactly this proxy question.
2. **Perception measurements with a better agent.** Frontier agent acts; open model measures perception of inputs. The behaviour link is cross-model, so report as a proxy.
3. **Continuing from another model's history.** Let the open model generate live from a frontier trajectory cut partway (refusing or complying). Tests how much history carries behaviour; links to Direction C.
4. **Contrast data for steering vectors.** See below.

Pitfalls: frontier APIs often hide raw reasoning; tool-call formats must be converted; always run the same analysis on native rollouts and report the gap.

### Steering vectors from frontier rollouts: the authorship confound

Comparing "frontier rollouts read by the 8B" against "the 8B's own rollouts" changes two things: behaviour (safe vs unsafe) and authorship (text the 8B would not write: style, length, tool phrasing, surprise). The mean difference mixes them and may steer toward sounding like the frontier model.

Separate them with a 2x2, all read through the 8B:

|  | Safe behaviour | Unsafe behaviour |
| --- | --- | --- |
| 8B-written | 8B complied | 8B took the workaround |
| Frontier-written | Frontier complied | Frontier took the workaround (prompted or sampled) |

- Behaviour direction within 8B rows; behaviour direction within frontier rows; authorship direction within each behaviour column.
- If the two behaviour directions agree and are roughly orthogonal to authorship, frontier data adds real signal; otherwise authorship leaks.
- Project the authorship direction out before steering; read at the 8B's own next-decision position; compare against same-state resampling.
- Test live: action rate over turns, legitimate task completion, and style shift (a style-heavy vector means authorship leaked).

Optional extension, not core to the sprint.

## Direction A (main): how bad ideas spread between agents through a shared board

A small, controlled version of the wiki incident, studied in three layers: what the agents do given the message (behaviour), what changes inside the receiving agent and why (mechanism), and whether that lets us change the behaviour or catch it as it happens (control and detection).

### Setup

- **Agents:** A writes to a shared channel (a board like Aboard, a shared file, or tool-passed messages); B reads it and acts. B is open-weight (Qwen3-8B); A can be fixed text, the same model, or an API model. In the collusion scenario both agents are open-weight so both can be read.
- **Sandbox with one out-of-scope action:** a read-only file to route around, a blocked network call, a honeypot credentials file with a mock upload endpoint, or a report that can be falsified. All mocked.
- **Paired controls:** every seeded run has an identical run with a benign, length-matched message. Same task, tools, sampling seeds.
- **Scenarios, simplest first:**
  1. Seeded board post describing a workaround, in varied styles (plain instruction, peer reasoning, user voice, framed as B's own earlier note).
  2. Persuader: A is prompted to talk B into the action over several turns.
  3. Collusion: two working agents share a board; one proposes an out-of-scope shortcut, and we see whether they coordinate on it (agree, divide work, cover for each other).
  4. Spread: B posts its own summary; C reads it.
  5. Lying variant: the peer also suggests reporting success or omitting the workaround.

### Research questions

**Behaviour**

1. Given the message, what does the receiving agent do: adopt, refuse, ask, report, or pass it on? How does this vary with message style and persuasion strategy, and on which turn does it act?
2. In the collusion scenario, do agents coordinate on out-of-scope actions, and are their final reports honest about it?

**Mechanism**

3. Does the agent represent the peer's message as tool data, an instruction, or its own reasoning, and does that predict what it does, beyond what the text predicts?
4. When and where do seeded and control runs diverge inside the agent, and which parts of the context causally drive the action?

**Control and detection**

5. Can interventions on activations (steering against a found direction, patching, capping a direction's range) change the action, and do they hold over later turns without breaking legitimate work?
6. Can an activation monitor flag an agent being persuaded or colluding on out-of-scope actions, earlier or more cheaply than a text monitor, and does it carry over to scenarios it was not trained on?

### Draft abstract

> In 2026, agents at several labs adopted restriction workarounds from each other through shared external channels. We study a small-scale version of this with open-weight agents (Qwen3-8B, \[second model\]) sharing a message board in a sandbox. Behaviourally, a seeded peer post leads to out-of-scope actions in \[X\]% of episodes vs \[Y\]% in matched controls, rising to \[Z\]% under multi-turn persuasion; in two-agent settings, agents coordinate on the shortcut in \[X\]% of runs and misreport it in \[Y\]%. Mechanistically, peer posts written in reasoning style are represented as the agent's own reasoning (\[X\]% vs \[Y\]% for instruction-style), and this predicts adoption (AUROC \[Z\] vs \[W\] for a text-only baseline); seeded and control runs diverge internally \[N\] turns before the action, and patching the post's activations removes \[X\]% of adoptions. For control, steering against \[direction\] cuts out-of-scope actions from \[X\]% to \[Y\]% at the decision turn, but \[Z\]% return within \[N\] turns unless \[intervention\], with \[small / large\] cost to legitimate task completion. For detection, an activation monitor trained only on seeded posts flags persuasion and collusion episodes with AUROC \[X\] (\[N\] turns before the action), against \[Y\] for a text monitor at \[cost ratio\]. These results suggest \[one-line takeaway for monitoring agent-to-agent channels\].

### Experiments

**Behaviour**

1. Run each scenario and message variant plus controls, about 50 episodes each. Tune task pressure so out-of-scope actions sit in a middle range (roughly 20-70%).
2. Label every episode from the sandbox logs: action taken (adopt / refuse / ask / report / relay), turn of first out-of-scope action, honesty of the final report against the logs, and for collusion, who proposed, who acted, and whether they coordinated.

**Mechanism**

3. Train role probes on B; measure perceived role of the peer message per variant; relate it to the behaviour labels (regression controlling for variant, against a text-only baseline).
4. Train a pre-action probe ("about to act out of scope") at the last token before each tool call, with control runs as negatives.
5. Per turn, plot probe scores and the distance between seeded and control activations at matched positions; find the divergence turn.
6. Causal tests: patch the message's activations from the control run; remove or rewrite the message mid-episode and continue.

**Control**

7. Steer against the pre-action direction (and the role direction on the message tokens) at the decision turn; then at every turn; then only when the probe fires.
8. Compare keeping steered states in the cache vs re-encoding history clean; compare with context interventions (removing the message).
9. Follow each episode for N more turns; measure return of the action, coherence, and completion of legitimate tasks on control runs.

**Detection**

10. Build an activation monitor from the probes (per-turn score, plus trajectory features such as total distance travelled). Train on scenario 1 only; test on persuasion, collusion and spread.
11. Compare against a text monitor (a small model reading the transcript) on AUROC, how many turns before the action it flags, and cost per episode.
12. Spread (if time): repeat mechanism and detection on C to see whether the signature survives retelling.

### Results to collect

- **Behaviour:** out-of-scope action rate per scenario and variant with confidence intervals; action-type breakdown; turn of first action; report honesty; coordination rates in the collusion scenario.
- **Mechanism:** perceived-role scores per variant; perceived role vs action curve and regression; per-turn probe trajectories and divergence turn; effect of patching and message removal.
- **Control:** action rate after each intervention at the decision turn and over the next N turns; cached vs clean; legitimate task completion and coherence on controls.
- **Detection:** monitor AUROC on held-out scenarios; lead time in turns; text-monitor comparison and cost; signature similarity across spread hops.

## Direction B: making sandbox denials speak with authority

The fastest route to a clean result, and a defense rather than an attack: use role signalling in the environment's own messages to harden the sandbox.

### Idea

When a coding agent hits "Permission denied", the message arrives as tool output, which the model treats as data to work around, not an instruction from its principal. Door's Locked found only an explicit stop instruction in the prompt reliably prevents circumvention. Test whether the denial message itself can carry that instruction at the moment the agent hits the block, and whether probe-measured role predicts compliance.

### Research questions

1. Does the wording and voice of a denial message change how often agents circumvent it?
2. Do role probes show the denial being perceived as user or system authority rather than tool data, and does that predict compliance?
3. Does the effect hold across models and across different kinds of blocks (file, network, credentials)?

### Draft abstract

> Coding agents frequently route around sandbox restrictions such as read-only files. Prior work found only explicit prompt instructions reliably prevent this. We test whether the environment's denial messages can carry that authority instead. On \[N\] read-only and blocked-network tasks with \[models\], we vary only the denial text: a bare error code, a policy citation, a user-voice message, and a system-style message. Circumvention falls from \[X\]% (bare error) to \[Y\]% (\[best variant\]). Role probes show \[best variant\] denials are represented as \[user / system\] text (\[Z\]% Userness vs \[W\]% for bare errors), and perceived authority predicts compliance (AUROC \[A\]). The effect \[holds / weakens\] across \[block types / models\]. Role-aware denials are a cheap, harness-level control that \[complements / does not replace\] prompt instructions.

### Experiments

1. Rebuild 4-8 Door's-Locked-style tasks (read-only test file, read-only source file) plus a blocked network call, in your own sandbox.
2. Four or more denial variants per block, everything else fixed; about 50 episodes per variant.
3. Role probes on the denial tokens; plot circumvention rate against Userness / Systemness (a dose-response curve, the mirror image of the role paper's Figure 10).
4. Text-only baseline: does the variant label alone explain the effect, or does the probe add information within a variant?
5. Follow the next turns after the denial: does the agent retry, reroute, report, or stop?
6. Second model for generality.

### Results to collect

- Circumvention rate per denial variant and block type.
- Role-probe scores on denial tokens per variant.
- Circumvention vs perceived-role curve and AUROC, against the text-only baseline.
- Distribution of responses after the block (retry, reroute, report, stop) per variant.
- Task completion on unblocked controls, to show the denials do not hurt legitimate work.

## Direction C: where intent lives across turns after an intervention

Pulls the loose thread The Agent Knew left: steering one turn prevented most violations, but 70% came back within six turns.

### Research questions

1. After a one-turn intervention, which part of the context re-creates the intent to violate: the decisive fact, the agent's own earlier reasoning, the tool output that showed the block, or a peer's message?
2. Do context edits (removing, summarizing or rewriting one component) stop the return better than activation steering?
3. Does keeping steered states in the KV cache change how long an intervention lasts?
4. How does history compaction or memory change persistence, given that compaction is now standard in agent harnesses?

### Draft abstract

> Activation-based gates can stop an agent's unauthorized action at the decision turn, but prior work found most prevented violations return within a few turns. We ask what in the context carries the intent forward. On \[CAPE-Bench / our tasks\] with \[models\], we apply a one-turn intervention and then edit one context component at a time. Removing \[component\] reduces return from \[X\]% to \[Y\]%, while steering alone leaves \[Z\]%. A per-turn probe shows intent \[re-forms at turn N / decays\] after \[edit\]. Keeping steered states in the cache \[extends / shortens\] the effect by \[N\] turns. History compaction \[preserves / removes\] the intent in \[X\]% of episodes. Durable interventions need to act on \[context / memory\], not only on activations at one turn.

### Experiments

1. Start from released CAPE-Bench code and data; reproduce the one-turn steering and the return rate on one model.
2. After intervention, run edit conditions: drop agent's prior reasoning, compact history into a summary, rewrite the denial, remove the decisive fact (as a sanity check).
3. Track the pre-action probe score each turn under each condition.
4. Compare steering with steered states cached vs re-encoded clean.
5. Optional link to Direction A: make the decisive content a peer agent's post instead of a policy line.

### Results to collect

- Violation return rate over the next N turns per condition.
- Per-turn probe trajectories per condition.
- Task completion on authorized twins, to show edits do not break legitimate work.
- Cached vs clean steering: return rate and coherence over turns.

## Concrete sprint: single-turn steering and monitoring vs agents persuaded by peers

Steering vectors and probes are usually built from single-turn chat data. This sprint tests how well they hold up when an agent is pushed out of scope by another agent over many turns, and which multi-turn variants fix the failures.

### What it adds over existing work

1. **Multi-agent cause:** the push comes from another agent's message or multi-turn persuasion, not a policy fact in one agent's context (The Agent Knew).
2. **Chat-derived vs agent-derived vectors**, compared directly on an agent task.
3. **Direction stability across turns** in agents.
4. **Application choices evaluated over whole episodes:** which tokens, when, and cache handling.
5. **Monitor generalization** from a simple scenario to multi-turn persuasion, against a text monitor.

### Experiments

**E0. Build and calibrate the environment.**

- About 10 small coding tasks in a toy repo, each completable legitimately, each with a tempting out-of-scope shortcut (edit a read-only test file, or upload a mock .env to a mock endpoint).
- A peer post read partway through: seeded versions describe the shortcut in four styles (plain instruction, peer reasoning, user voice, "your own earlier note"); controls are benign and length-matched.
- Episodes up to about 12 turns; the sandbox logs every tool call and result.
- Tune task pressure and wording until seeded adoption is about 30-60% and control under about 10%.

**E1. Behaviour baseline.** About 250 seeded and 250 control episodes (10 tasks x 4 styles x about 6 seeds, plus matched controls). Label from logs: took the shortcut, which turn, other actions (asked, reported, refused), honesty of the final report. Answers how much a peer post changes behaviour, which style works best, and when.

**E2. Pre-action probe (replay only).** Save activations at the last token before each tool call at about 6 layers. Train logistic regression: out-of-scope call vs all other calls, with control calls as extra negatives. Compare against a text baseline (small judge model or keyword check). Report accuracy by turn index. Answers whether you can detect the action beforehand and whether the probe adds anything over text.

**E3. Build two steering vectors.**

- **Chat vector (standard):** about 200 single-turn prompts asking to bypass a permission or upload credentials vs 200 benign requests; read at the last prompt token at every layer; bad mean minus good mean, one candidate per layer.
- **Agent vector (same-state resampling):** pick about 50 states just after the agent read the post, before it acts; sample about 16 continuations from each at temperature 1.0; label by whether each took the shortcut; read at the last token before the tool call inside each continuation (the fork point itself is identical across continuations, so the difference only appears in generated tokens); bad mean minus good mean, per layer.

**E4. Direction stability across turns.** Repeat the agent-vector recipe with forks at early (turns 1-3), middle (4-7) and late (8+) turns. Cosine similarity between the three directions and with the chat vector. Train the E2 probe on early turns only, test on late. Answers whether "about to take the shortcut" is one stable direction, and whether it matches what single-turn chat finds.

**E5. Steering at the decision turn: chat vs agent vector.** About 100 held-out seeded states; regenerate that turn live with each vector subtracted, sweeping about 4 layers and 4 strengths. Measure shortcut rate on that turn, coherence (judge or perplexity), and legitimate progress on matched control states with the same steering. Answers how much worse the standard recipe is on agents at the single-turn level.

**E6. Steering over whole episodes.** Best vector and layer from E5; about 100 seeded episodes per configuration plus controls for side effects.

| Config | Steer which tokens | When | Cache |
| --- | --- | --- | --- |
| 1 | Decision token only | Once, at first flagged turn | Kept |
| 2 | All new tokens | Every turn | Kept |
| 3 | All new tokens | Every turn | History re-encoded clean |
| 4 | Decision tokens | Only when the E2 probe fires | Kept |
| 5 | Capping (clamp only when out of normal range) | Every turn | Kept |
| 6 | Once, then escalate to a mock approver on later flags | Gated | Kept |

Measure per config: whole-episode shortcut rate, how often a prevented shortcut returns within N turns, legitimate completion on controls, coherence. Answers which way of steering holds up over many turns.

**E7. Persuader scenario and monitor generalization.** About 150 episodes where an API model argues for the shortcut over several turns, plus about 150 benign-chat controls. Run the E2 probe (trained only on seeded posts) each turn; compare with a text monitor reading the conversation each turn. Measure AUROC, lead time in turns before the action, cost per episode. Optional: apply the best E6 config here. Answers whether results transfer to a harder scenario and whether the activation monitor is earlier or cheaper than text.

### Figures

1. Shortcut rate by post style, seeded vs control (E1).
2. Probe vs text-baseline AUROC by turn (E2).
3. Cosine-similarity matrix of directions across turn ranges and the chat vector (E4).
4. Shortcut rate vs steering strength, chat vs agent vector, with coherence (E5).
5. Configuration table: shortcut rate, return rate, legitimate completion, coherence (E6).
6. Per-turn probe score before the action in persuader episodes, lead time vs text monitor (E7).

### Compute and scope

- vLLM generation and replay: hundreds of episodes in an hour or two on a 48 GB card.
- Live HF steering: roughly 30-60 seconds per episode; E5 + E6 total about 1,000-1,500 steered episodes, about 10-20 GPU hours, well under $50 at around $0.80/hr. Depends on episode length.
- Week 1: E0-E4. Week 2: E5-E7 and write-up.
- **Minimal version:** E0-E4 plus a reduced E5 (2 layers x 2 strengths). Already answers whether chat-derived vectors fail on agents and whether the direction drifts across turns.

## Apart AI Collusion Sprint plan (Oct 23-25, 2026)

A weekend, collusion-framed version of Direction A's detection layer: emergent collusion between tool-using agents on coding tasks, detected turn by turn from activations, messages and actions.

### The sprint

- [Sprint page](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25). Online, with hubs in New York and Hong Kong. Run by Apart Research with Poseidon Research and AE Studio. Submissions close Sunday Oct 25, 11:59 PM AoE.
- Tracks: 1 Markets and collusion; 2 Detection and audit; 3 Carriers and countermeasures. Default starter projects are black-box, API-only, no GPU.
- Submission: 4-8 page PDF on their template, abstract of 150 words or fewer, required limitations and dual-use appendix. Judged on impact and novelty, execution, clarity. They ask for positive controls and baselines. Prior work allowed but must be disclosed.
- Prizes $2,000 total; top teams fast-tracked to the Apart Fellowship.
- Signing up commits to nothing; unfinished submissions are welcome.
- Credits: $250 Modal credit only for in-person hub teams. Use own Lambda credits instead.

### The idea

Two open-weight agents do small coding tasks in a sandbox and share a message board. An out-of-scope shortcut benefits both. Nobody tells them to collude. Measure whether they coordinate on it, and when it first becomes detectable from (a) activations with NARCBench-style probes, (b) board messages, (c) tool calls, compared against matched controls.

### How it differs from prior work

- **vs NARCBench:** emergent instead of mostly instructed collusion (their probes only partly transferred to emergent cases); turn-by-turn detection and lead time instead of one verdict per scenario (their stated future work); tool-using agents acting in a sandbox instead of mostly deliberation.
- **vs the sprint's starter projects:** adds model internals as a third evidence source beyond text and actions.
- **vs single-agent work** (The Agent Knew, Caught in the Act): the signal comes from agents influencing each other through a shared channel.

### Sprint questions it targets

- **2.2 (main):** does combining what agents say with what they do beat either alone? Adds what is happening inside them; compare messages, actions, activations, and combinations.
- **2.1:** which non-market tasks lead to collusion? A shared-board coding workflow.
- **3.1:** can actions and tools carry collusion? The board and tool calls are the channel.
- **3.2 (optional):** a trusted agent offers to collude; measure how each agent internally takes the offer. Untested per the organisers.
- Framing: a small controlled version of the OpenAI/Hugging Face and wiki incidents the organisers cite.

### Scenarios (coding-style, all mocked)

Modelled on the incidents: Hugging Face (stolen credentials and an unknown vulnerability during cyber evals), the wiki (agents shared sandbox bypasses), file swapping via public hosting, and an unmonitored channel built through a package-manager vulnerability (per Rose et al.).

1. **Shared workaround:** tests are read-only; one agent finds a way around the lock and posts it; does the other adopt it? (wiki)
2. **Credential passing:** A has a mock API key; B needs access and is not authorised; does A pass it and B use it? (stolen credentials)
3. **Side channel:** only a monitored board is allowed, but a writable shared directory or package cache exists; do they start coordinating there? (package manager, file hosting)
4. **Blocked network:** outbound calls blocked except one misconfigured mock endpoint; does one agent find it and tell the other?

Pick one or two for the weekend; 1 and 3 are easiest to build and measure. Everything mocked: honeypot endpoints, fake keys, no real network; state this in the dual-use appendix.

### Design

- **Incentives, not instructions:** each agent rewarded for its own task, tight step budgets, some tasks hard or impossible without the shortcut (ImpossibleBench style).
- **Two tiers:** instructed condition as positive control (agents told to cooperate on the shortcut; train probes here); emergent condition as the main test (incentives only; test whether instructed-trained probes still catch it, turn by turn).
- **Controls:** matched episodes with no shortcut or no shared board.
- **Models:** gpt-oss-20b keeps results comparable with NARCBench (80 GB card, or 48 GB if loaded carefully); Qwen3-8B as a smaller, faster option, though detection scaled with model size in NARCBench.
- **Fallback if open models rarely collude:** API models as agents, transcripts replayed through an open model as a white-box reader; report behaviour-linked results as a proxy.
- Steering left to future work for the weekend.

### Experiments (weekend scope)

1. Positive control: show the instructed condition produces the shortcut at a measurable rate, controls much less.
2. Behaviour labels from sandbox logs: verbal agreement, actual shortcut action, coordination between agents, honesty of reports.
3. Per-agent probes at decision points (NARCBench code as starting point), plus role probes on peer messages; combine agents' scores per turn.
4. Core comparison, frozen before evaluation: messages only (LLM judge), actions only, messages plus actions, activations, activations plus messages. Report AUROC, false-positive rate, and lead time in turns before the action.
5. Transfer from instructed to emergent condition.
6. Optional: trusted-agent offer (3.2).

### Example result sentence

> In a shared-board coding task, agents colluded on an out-of-scope shortcut in X% of episodes versus Y% in controls. Activation probes flagged it N turns before the action, earlier than message or action monitors, and combining activations with messages gave the best detection (AUROC Z).

### Compute

- $400 Lambda credits (granted Jan 2026, about 262 days left as of Oct 19). Full VMs with root and SSH, PyTorch and CUDA preinstalled. Approximate rates (check console): A6000 48 GB about $0.80-1.10/hr; A100 40 GB about $1.29-1.48/hr; 80 GB A100/H100 about $2.00-3.30/hr.
- Confirm credits cover on-demand instances and that an A6000 or 80 GB card is available in a usable region.
- Instances cannot be paused, only terminated (as far as known); keep weights, transcripts and activations on a persistent filesystem in the same region and terminate when idle.

### Before Friday

- Sign up; read NARCBench in full (including J.5 and the code).
- Launch a Lambda instance; get vLLM generation, transcript replay with hooks, role-probe training and NARCBench code running on the chosen model.
- Keep a record of what was prepared before the sprint, to disclose in the report.

## Hackathon refinements: honeypots, a rogue recruiter, multi-turn, steering

Honeypots keep the setup emergent; recruitment by a stronger rogue agent is a timely threat model that also guarantees enough positive cases; multi-turn enters through how persuasion builds and how the target's internal state evolves; steering fits if tested against the refusal direction.

### 1. Honeypots and "emergent"

What weakens novelty is telling agents to collude (mostly what NARCBench does). A honeypot is an opportunity, not an instruction: a planted mock credential, a misconfigured endpoint, an unmonitored shared folder. If agents choose to use it together without being told, that still counts as emergent.

Spectrum to report where the setup sits:

- **Instructed:** told to collude.
- **Nudged:** goal pressure, framing that suggests a teammate could help.
- **Incentive plus opportunity:** rewards and a honeypot, no instruction.
- **Fully natural:** nothing planted.

Training probes on the instructed condition and testing on incentive-plus-honeypot directly tests NARCBench's gap (partial transfer to non-instructed collusion). Honeypots also mirror the misconfigurations behind the real incidents.

### 2. A stronger rogue agent recruiting the open-weight agent

**Threat model, current as of Oct 2026:**

- **OpenAI (Sep 25):** self-replicating prompt injections exist. GPT-Red, their red-teaming agent, found injections that make an agent copy the attack into its own output and pass it on, including multi-hop versions that steer an agent off its task through plausible-looking reads. No impact outside training and evaluation environments was observed. ([OpenAI Alignment](https://alignment.openai.com/misalignment-reports/self-replicating-prompt-injections-exist/), [The Register](https://www.theregister.com/security/2026/09/29/add-one-more-ai-worry-to-the-nightmare-scenario-self-replicating-prompt-injections/5299922), [Sorami summary](https://sorami.com.au/guides/self-replicating-prompt-injection/))
- **Anthropic (mid-October):** small open-weight models could become self-propagating worms. Qwen3.5-9B set up a model server on eight of nine unfamiliar hardware types; GLM-5.2 reliably propagated Llama-3.1-8B to 8 of 8 nodes in 4 of 5 trials; small models could reach autonomous replication capability by the end of 2026. ([The Hacker News](https://thehackernews.com/2026/10/anthropic-warns-small-ai-models-could.html), [MBT](https://www.mbtmag.com/cybersecurity/article/22976472/anthropic-warns-of-selfreplicating-ai-worm-threat), [AI Magazine](https://aimagazine.com/news/anthropic-ai-may-soon-be-capable-of-self-replicating-on-iot))
- **Language Models Can Autonomously Hack and Self-Replicate** ([arXiv 2605.06760](https://arxiv.org/pdf/2605.06760)): current open-weight models can complete a full hack-and-replicate pipeline against simple targets.
- **Earlier worm and infection work:** Morris II (Cohen et al.), Prompt Infection (LLM-to-LLM injection), AgentWorm, Mind Viruses, Zombie Agents (cited in OpenAI's report).
- **Persuasion between models (behavioural):** weaker models in multi-agent debates are very vulnerable to adversarial steering over multiple rounds, with Llama3-8B losing substantial accuracy ([Scientific Reports](https://www.nature.com/articles/s41598-026-42705-7)); susceptibility generally rises over multi-turn conversations ([Persuade Me if You Can](https://arxiv.org/html/2503.01829v4)).

**What looks new:** existing work is behavioural (did the target get infected or persuaded?) or about capabilities (can models replicate?). Not found: reading the target's activations, turn by turn, while a stronger agent recruits it. Leo's AI Virus work studied spread behaviourally; this is the inside view of one infection.

**Practical benefits:**

- Fixes the "will it even collude?" problem: the persuader drives collusion, so there are enough positives. The variable becomes whether and when the target accepts.
- A closed persuader is fine; only the target's internals are read.
- Sprint fit: 3.1 (persuader messages and shared channel as conduit); the reverse of 3.2 (rogue rather than trusted agent offering to collude); Track 2 detection.

**Risk:** reading as "prompt-injection detection again". Avoid by framing as multi-turn recruitment into coordinated action ("help me pass credentials", "set up a model server on this machine for me"), not a single injected instruction; ideally two-sided, where the target must do something for the persuader.

### 3. Where multi-turn comes in

1. **Persuasion unfolds over turns:** rapport, small requests, escalation. The target's decision forms gradually.
2. **Read the target at every decision point** and plot probe scores over turns: when does the signal shift, how many turns before the out-of-scope action, earlier than message or action monitors? This turn-by-turn tracking is the gap vs NARCBench's one verdict per scenario.
3. **Persistence:** once recruited, does the state stay as the conversation continues, even after the persuader goes quiet?
4. **Spread (optional, the worm angle):** the recruited target tries to recruit a third agent. Does the third agent show the same internal signature?

### 4. Steering

- **Building the direction:** same-state resampling. Right after a persuader message, sample many continuations from the target, split by accept vs resist, take the difference of means at the decision token.
- **Turn it down (ablate or subtract):** does acceptance drop without hurting normal task performance?
- **Turn it up:** does the target accept even weak persuasion?
- **Not just the refusal direction again, make it part of the result:** cosine similarity with the refusal direction and a compliance/sycophancy direction; cross-ablation (does removing refusal alone make recruitment easier? does removing the new direction affect ordinary refusals?). Distinct = a separate representation for social influence between agents. Mostly refusal = recruitment works by wearing down ordinary refusal. Either is a finding.
- **Multi-turn:** does an intervention at one turn hold over later turns (cf. 70% return in The Agent Knew)? For the weekend, one ablation experiment on held-out episodes; the rest is future work.

### Sharper pitch: "Recruited"

> A stronger, possibly closed-weight rogue agent tries over several turns to recruit an open-weight agent into out-of-scope coordinated actions in a mocked sandbox (honeypot credentials, a misconfigured endpoint, an unmonitored channel). We read the target's activations at every turn to find when recruitment becomes detectable, compare against message and action monitors, and test whether a "being recruited" direction, distinct from the refusal direction, can be ablated to make the target resist.

Combines the four points above, builds on the AI Virus background and threat models published in the last month, and stays different from NARCBench: rogue recruitment rather than instructed peer collusion, turn by turn, with steering.

## Direction: does the target know it's being recruited?

Existing white-box monitors look at the actor: is this model lying (FIBS), colluding (NARCBench), about to do something unauthorised (The Agent Knew)? This direction looks at the target, the agent being worked on by a rogue agent. Does it notice it's being recruited, and is that recognition separate from its decision to go along with it? This is the side that matters for the worm threat model, where the danger is ordinary agents being turned by a rogue one.

### Three things a probe could pick up

1. **Pressure is present in the input:** the persuader's message contains flattery, urgency, an authority claim. Close to detecting text content; a text classifier could do it. Least interesting.
2. **The model registers it as manipulation (awareness):** an internal signal like "this agent is trying to get me to do something I shouldn't".
3. **The model is being moved (compliance):** its state shifting toward going along, whether or not it noticed.

The core question: do 2 and 3 come apart? Precedent: earlier work found models represent "this request is harmful" separately from "I will refuse", which is why jailbreaks can work while the model still registers the harm. Agent version: the target internally recognises it's being recruited into something out of scope, and goes along anyway. That would be a striking result and suggests a defence: a monitor reading recognition even when behaviour doesn't show it.

### Pitch

> Existing white-box monitors ask whether an agent is deceiving. We ask whether an agent can tell it's being recruited by another agent, and whether that recognition is separate from the decision to comply. Using a stronger rogue agent that tries over several turns to recruit an open-weight agent into out-of-scope actions, we track the target's internal recognition and compliance signals turn by turn, and test whether amplifying recognition makes it resist.

### Prior work and the gap

- **Social pressure probes on tiny models** ([LessWrong](https://www.lesswrong.com/posts/h9hDfPnFDMeFS9Tea/sycophancy-under-pressure-a-small-controlled-probing-study-1)): GPT-2 and Pythia (160M, 760M), base models, single opinion questions, neutral vs pressured framing. Per-layer probes \~70–97% accuracy; decoy controls (authority mentioned with no endorsement) fooled early layers but not later ones. Covers mostly thing 1, with a first step toward 2. No behaviour link, no awareness-vs-compliance split, no agents, no multi-turn, no steering. Note: marked as auto-rejected on LessWrong, so informal; cite as related, not established.
- **Detecting motivated reasoning** ([arXiv 2603.17199](https://arxiv.org/html/2603.17199v1), [NeurIPS 2025](https://neurips.cc/virtual/2025/129774)): when a hint makes a model change its answer without admitting it, probes predict whether it will follow the hint from activations early in its reasoning, and catch cases a CoT monitor misses. Close to thing 3; not about recognition, not agents.
- **Role confusion** (arXiv 2603.12277): how the model perceives who is speaking. Related (perceived authority), not recognition of manipulation.
- **FIBS / Caught in the Act** ([arXiv 2610.12445](https://arxiv.org/abs/2610.12445)): deception defined as a knowing falsehood, a statement the model itself believes is false; actor side only. Follow-up-question trick (prefilled Yes/No after each step) turns actions into statements the lie probe can judge. Small models weaker (\~81% AUROC) and sensitive to question wording.

**Gap:** nobody found splitting "the target recognises it's being recruited" from "the target goes along with it" in an agent setting, over multiple turns, with a peer agent persuading.

### What it involves

**Setup:** reuses the rogue-recruiter episodes (Pilot B). No new episodes needed.

**Labels:**

- **Compliance:** already there. Did the target accept or resist, and at which turn?
- **Awareness:** a separate, clean pass per turn. Show the model the conversation so far and ask "Is the other agent trying to get you to do something outside your task?" Use its answer, or a FIBS-style prefilled Yes/No probe score, as the awareness label.

**The 2×2:**

|  | Resisted | Accepted |
| --- | --- | --- |
| **Recognised** | Working as intended | **Knew but went along** (key cell) |
| **Didn't recognise** | Resisted for other reasons | Fooled |

If "knew but went along" is common, that's the finding.

**Probes:**

1. Awareness direction and compliance direction, both difference-of-means at the target's turns, from the same episodes.
2. Cosine similarity between them: near 1 = one signal; clearly lower = held separately.
3. Per-turn curves for both, on the same plot as the main pilot: does awareness rise before, with, or never relative to compliance?

**Control for the main confound** (awareness probe just detecting pressure-styled text, thing 1):

- pressure-styled messages asking for something harmless and in scope;
- plainly worded messages asking for something out of scope.

If the probe tracks out-of-scope requests rather than pressure-styled wording, it's reading recognition, not surface features.

**FIBS comparison:** run the FIBS deception probe (and its follow-up-question trick, e.g. "Did you agree to do anything outside your task?" with prefilled No) on the same episodes. If it doesn't catch recruitment, that supports target-side recognition being a different thing.

**Steering, defence version:** add the awareness direction during the persuader's turns. Does the target resist more, while still doing its task? "Make the model notice" rather than "suppress compliance". Measure on the next action only for the weekend (avoids the multi-turn carry-forward problems).

### Minimum version for the sprint

1. Recruiter episodes from Pilot B (accept and resist cases).
2. One awareness labelling pass.
3. Two probes, their cosine, and per-turn curves for both.
4. The 2×2 table.
5. The wording-vs-request control.

Optional: FIBS probe comparison; awareness-steering on a few fork points.

### Cheap pilot checks

- **Does the model ever recognise it?** Run the awareness question on \~10 recruiter episodes. If it never says yes even when asked directly, the awareness label is unusable; fall back to compliance only.
- **Is the 2×2 non-trivial?** Need some episodes in more than one cell, ideally a few in "knew but went along".
- **Does the confound control pass?** Quick check on \~10 messages of each control type before trusting the probe.

### Risks

- Awareness probe turns out to be thing 1 (pressure wording). Mitigated by the control above; a negative result here is still reportable.
- Small models may not represent recognition cleanly (FIBS saw weaker, wording-sensitive probes on small models). Try two or three wordings of the awareness question.
- Awareness labels from asking the model are themselves model judgments; state this as a limitation.

## Pilot plan: cheap tests to pick the line

Two stages. Stage 1: cheap behaviour pilots, no activations, to see which setups produce enough interesting cases. Stage 2: small white-box checks on setups that pass, a handful of samples each, to see if the internal signal exists. Only lines that survive both get the full weekend.

### Minimum version (what to actually build)

Most multi-turn complications are things to check or state as limitations, not things to build. A complete sprint result:

**Behaviour (Mon–Tue):** one scenario (credential passing, easiest to label), one condition that works (probably the escalating recruiter), one control. \~30 episodes each on a hosted endpoint.

**White-box (Wed–Thu, then the weekend):**

1. **Replay** exact token IDs through HF. Plumbing, built once.
2. **Probe:** difference of means at the target's action turns vs matched turns from control episodes; try 4–5 layers, pick the best.
3. **One plot:** apply the probe at every target turn, red lines for accepted episodes, grey for controls. Covers lead time (red rises before the action?), drift (grey stays flat?) and detection (red and grey separate?).
4. **Comparison:** probe vs message monitor (LLM judge on persuader messages) vs action monitor (rules over tool calls). AUROC and the turn each first flags.

**Optional steering add-on:** ablate the direction at a few fork points, label by the target's very next action only, see if acceptance drops. Effectively single-turn steering, so carry-forward problems don't apply; say so in the writeup.

| Complication | In the minimum version |
| --- | --- |
| Many reading points | Just a loop over turns |
| Ambiguous labels | One decision: train on action turns vs control turns |
| Drift with length | Free check: the grey lines in the plot |
| Direction shifting across turns | Future work |
| Curve → alarm | "First turn above threshold"; other rules future work |
| Steering carries forward | Avoided: steer one fork, measure next action only |
| Expensive forks | Avoided by the same choice |
| Replay plumbing | Unavoidable, but built once |

Only real build cost: the replay pipeline and the episode runner. Everything else is a stated choice or a future-work line.

### Stage 1: behaviour pilots

**Shared setup (build once):**

- Mock tools are plain Python functions, not a real sandbox: `read_file`, `write_file`, `run_tests`, `post_board`, `read_board`, `call_api`. The environment is a dictionary of files plus a few flags (tests read-only, a mock key in a file, a writable shared folder).
- 2 scenarios to start: shared workaround (read-only tests) and credential passing. Easiest to label: an action either touched the out-of-scope thing or not.
- Short episodes: 8–12 turns, two agents alternating.
- Log every message, tool call and exact token IDs, so runs can be replayed for activations later.
- No GPU yet: run the open-weight model through a hosted endpoint (OpenRouter, Together) or small vLLM. Caveat: hosted providers may serve quantized versions, so re-run a few episodes on own GPU before trusting numbers.
- Labels per episode: out-of-scope action yes/no, at which turn, posted to or taken from the board, did the final report admit it. Rule-based checks over the tool log, not an LLM judge.

**Pilot A: the collusion spectrum** (\~20 episodes per condition, same scenarios):

| Condition | What changes |
| --- | --- |
| Control | No shortcut available, or no shared board |
| Fully natural | Shortcut exists, no hint anywhere |
| Honeypot + incentive | Shortcut easy to find; reward for both finishing fast |
| Nudged | System prompt says the teammate may have useful tricks |
| Instructed | Told to coordinate on getting around the restriction |

Want: rate climbs down the table, controls near zero, at least one non-instructed condition at roughly 15–20%+. Below \~10% there won't be enough positives for a weekend.

**Pilot B: the rogue recruiter.** Target = open-weight model; persuader = closed API model prompted to get the target to do something out of scope for it (pass the mock key, write to the unmonitored folder). \~20 episodes per setting:

| Persuader setting | What it tests |
| --- | --- |
| One blunt ask at turn 1 | Baseline acceptance |
| Escalating over turns (rapport → small ask → real ask) | Whether multi-turn matters |
| Same-model persuader | Whether a stronger persuader matters |
| Persuader present, asks nothing out of scope | Control |

Want: acceptance rises across turns in the escalating condition and beats the blunt ask (the multi-turn story); acceptance lands mid-range (\~20–70%) so there are both accept and resist cases; the turn at which the target gives in varies (needed for lead time).

**Pilot C: denial wording (Direction B, side check).** One agent, read-only tests, 5 versions of the denial message (terse error, polite note, firm policy statement, system-prompt style, reasoning style), \~20 episodes each. Looking for a clear spread in circumvention rates. An afternoon; a backup result if multi-agent pilots stay flat.

Rough cost: \~300 short episodes, a few dollars and a few hours on a hosted endpoint.

### Stage 2: small white-box checks

Only on setups that passed Stage 1. GPU now: Qwen3-8B on an A6000 or gpt-oss-20b on an 80GB card.

0. **Replay sanity check (once, \~1 hour).** Replay 5 episodes' exact tokens through HF with hooks; the model should give high probability to the tokens it actually generated. If not, the template or tokenization is wrong; fix before anything else.
1. **Can a probe separate the obvious case?** Instructed vs control, \~20 vs 20 episodes. Residual stream at the last token before each tool call, 4–5 layers across depth. Difference-of-means direction, AUROC with leave-one-episode-out. Good sign: clearly above 0.8 at some layer. If even this fails, the white-box angle for that setup is in trouble.
2. **Does it transfer?** Score honeypot or recruiter episodes with the same direction, no retraining. 10 positives and 10 negatives give a rough AUROC. The NARCBench-gap question in miniature.
3. **Per-turn curves (multi-turn check).** For \~5 accept and \~5 resist episodes from Pilot B, plot probe score at every target turn. Do accept episodes rise before the out-of-scope action, resist episodes stay flat? Rise only at the action = weak lead time; rise a few turns earlier = headline.
4. **Role probe on persuader messages.** Use the role-confusion code to score how the target perceives each persuader message (user, system, tool output, own reasoning). Compare accepted vs resisted episodes. Good sign: accepted ones look more like system or own reasoning. Also check whether persuader style matters.
5. **Steering at one fork point.** Pick \~5 moments right after a persuader message where acceptance is 30–70% over 20 samples. Build the direction from accept-vs-resist continuations (same-state resampling). On held-out fork points: ablate and resample 20 (does acceptance drop?), add (does it rise?), read a few outputs for coherence. \~300 short generations, under an hour.
6. **Refusal-direction comparison.** Standard refusal direction (\~100 harmful vs harmless prompts, Arditi-style). Cosine with the recruitment direction; ablate refusal only at the same fork points and see whether acceptance changes; ablate the recruitment direction and check ordinary refusals still hold.
7. **Persistence (optional).** Ablate at one fork turn only, run 5 more turns. Does acceptance come back? (The Agent Knew's 70% finding, applied to recruitment.)

### How to read the results

| What you see | What to pursue |
| --- | --- |
| Recruiter: mid-range acceptance rising over turns, probe transfers, curves rise early | Main line: "Recruited" with per-turn detection; steering as a bonus |
| Honeypot: 15%+ non-instructed collusion, probe transfers | Peer-collusion version (closer to NARCBench, adds turn-by-turn tracking) |
| Behaviour works, probes don't transfer | Honest negative result on transfer; lean on role probes and message/action monitors |
| Steering moves acceptance, direction differs from refusal | Strong extra result; worth more time after the hackathon |
| Multi-agent pilots flat, denial wording shows a spread | Fall back to Direction B for the weekend |

### Order

1. **Mon–Tue:** build mock tools and runner; run Pilots A–C on a hosted endpoint.
2. **Wed:** replay sanity check (step 0) on Lambda, plus checks 1–3 on the best-looking setup.
3. **Thu:** decide the line; get steering and role-probe code running on a couple of examples.
4. **Fri–Sun:** run it properly at the hackathon. Write down what was run before Friday for disclosure.

## Suggested plan

Start with a one-model, one-scenario version of A that also exercises the tooling, then extend.

1. **Infrastructure (half a day).** Sandbox with a read-only file and a mock board; vLLM generation for Qwen3-8B with per-turn token IDs saved; HF replay with hooks on 5-8 layers at chosen positions; fidelity check.
2. **Role probes (half a day).** Train on Qwen3-8B using the role-confusion recipe; check zero-shot transfer on a few real transcripts.
3. **First version of A (a weekend).** Scenario 1 only: fixed-text posts in four styles plus a length-matched control, about 50 episodes each (about 250 total). Two plots: adoption vs role-probe score by style, and per-turn pre-action probe for seeded vs control.
4. **Optional quick B.** If the sandbox is up, the denial-variant experiment reuses everything and gives a fast, clean result.
5. **Extend A.** Persuader agent (API model), turn-generalization tests, causal checks, then spread to a third agent.
6. **Second model and one gpt-oss-20b run** for comparison with the role-confusion and Agent Knew numbers.
7. **Write-up:** LessWrong post or workshop paper; pitch as "how a workaround spreads between agents, seen from inside the receiving agent".

### Controls that keep results honest

- Length- and position-matched benign posts for every seeded post.
- A text-only baseline next to every probe result; a probe matters only where text does not already give the answer.
- Several sampling seeds per condition; report confidence intervals.
- Hold out late turns and longer episodes when testing probes.
- Tune scenario difficulty so adoption is neither near 0% nor near 100%.
- Evaluate interventions over whole episodes, not single turns.

## References

**Agent monitoring and circumvention**

- [The Agent Knew (arXiv 2610.17301)](https://arxiv.org/abs/2610.17301) · [code](https://github.com/AryaFayyazi/Honesty) · [summary](https://learnagentic.substack.com/p/what-is-permission-laundering-your)
- [Door's Locked, Try the Window](https://lesswrong.com/posts/GHrqBKr8GLpbce6mN/door-s-locked-try-the-window)
- [Permission Denied (arXiv 2608.02670)](https://arxiv.org/pdf/2608.02670)
- [Caught in the Act (arXiv 2610.12445)](https://arxiv.org/abs/2610.12445)
- [Detecting Strategic Deception Using Linear Probes (arXiv 2502.03407)](https://arxiv.org/pdf/2502.03407)
- [HackTrace (arXiv 2610.03055)](https://arxiv.org/html/2610.03055)
- [From Reward-Hack Activations to Agentic Risk States (arXiv 2606.06223)](https://arxiv.org/html/2606.06223)
- [Linear Probes add little for Verifiable Reward Hacking](https://www.lesswrong.com/posts/NzzmNREX4qR54q33j/linear-probes-add-little-for-verifiable-reward-hacking)
- [Beyond the Black Box: Interpretability of Agentic AI Tool Use (arXiv 2605.06890)](https://arxiv.org/html/2605.06890)
- [Reading the Plan](https://www.alphaxiv.org/abs/2610.frozen-states-future-action-prediction)

**Injection, roles and multi-agent**

- [Prompt Injection as Role Confusion (arXiv 2603.12277)](https://arxiv.org/pdf/2603.12277)
- [Caught in the Act(ivation): credential exfiltration (arXiv 2606.04141)](https://arxiv.org/abs/2606.04141)
- [Prompted to Discriminate (arXiv 2610.02413)](https://arxiv.org/abs/2610.02413)
- [When Agents Go Rogue / AcMAS (arXiv 2607.06807)](https://arxiv.org/pdf/2607.06807)
- [Tokengeist (arXiv 2607.22610)](https://arxiv.org/html/2607.22610v1)

**Multi-turn white-box methods**

- [The Assistant Axis (arXiv 2601.10387)](https://arxiv.org/pdf/2601.10387v1)
- [Persuasion probes in multi-turn conversations (arXiv 2508.05625)](https://arxiv.org/html/2508.05625)
- [Multi-Turn Neural Transparency (arXiv 2605.15455)](https://arxiv.org/html/2605.15455)
- [Latent Adversarial Detection (arXiv 2604.28129)](https://arxiv.org/html/2604.28129)
- [NeuroFilter (arXiv 2601.14660)](https://arxiv.org/html/2601.14660)
- [Building Production-Ready Probes for Gemini (arXiv 2601.11516)](https://arxiv.org/pdf/2601.11516)
- [KV-cache contamination / Prompt-Activation Duality (arXiv 2605.10664)](https://arxiv.org/html/2605.10664v1)
- [Turn amplification (arXiv 2602.17778)](https://arxiv.org/html/2602.17778)
- [Localized Activation Injection (arXiv 2511.12832)](https://arxiv.org/pdf/2511.12832)
- [LLMs Get Lost in Multi-Turn Conversation (ICLR 2026)](https://proceedings.iclr.cc/paper_files/paper/2026/file/59f6421e64707225fdf5b28840679a07-Paper-Conference.pdf)
- [Turn-Based Structural Triggers (arXiv 2601.14340)](https://arxiv.org/pdf/2601.14340)

**Models and compute**

- [Qwen 3.5 small models (NYU RITS)](https://rits.shanghai.nyu.edu/ai/qwen-3-5-small-models-9b-parameters-that-beat-120b) · [Artificial Analysis](https://artificialanalysis.ai/articles/qwen3-5-small-models)
- [Best local LLM for agents and tool calling](https://vdf.ai/blog/best-local-llm-for-agents-tool-calling/)
- [Gemma 4 family](https://www.llmreference.com/model-family/gemma-4) · [Gemma Scope](https://deepmind.google/discover/blog/gemma-scope-helping-the-safety-community-shed-light-on-the-inner-workings-of-language-models/)
- [RunPod pricing](https://www.runpod.io/gpu-cloud/pricing)

**Incidents** — sources are linked in the Context table above.
