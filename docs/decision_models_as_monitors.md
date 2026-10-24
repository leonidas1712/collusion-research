# Decision models as safety monitors: what exists

2026-10-24, for Leo. Question: what are the OpenRouter "decision models" (`openai/gpt-6-luna-decisions`, `typesafe/jev-1.14`)? What literature uses classifier-style models as monitors or as replacements for LLM judges? Has anyone used decision models as agent monitors?

**How things were checked.** OpenRouter facts come from the live API on 2026-10-24. arXiv IDs, titles and dates were checked with the arXiv API. Everything else comes from the page linked next to it. **[unverified]** means the claim comes from a secondary source (a news article or the community awesome-list) and I did not read the primary source.

## Summary

- **Decision models are now a product category of their own.** They are not text generators. You send a `state` (text, JSON or images) plus typed questions. The model returns a probability distribution over your fixed options in one call, with no rationale. Input is billed and output is free. OpenRouter lists 30 of them from about 17 makers (Jev, Luna Decisions, Perplexity Decider, Liquid d1, Cloudflare Clef, Microsoft-Decision-1 and others).
- **Leo is right that Jev came first.** Jev opened in early access on 2026-09-15, and `typesafe/jev-1.13` was on OpenRouter on 2026-09-18. OpenAI previewed its Decisions API at DevDay on 2026-09-29, and `openai/gpt-6-luna-decisions` appeared on OpenRouter on 2026-10-06. Jev 1.14 followed on 2026-10-14.
- **There are no logprobs and no sampling parameters.** On OpenRouter, `supported_parameters` is empty for both models. The output is per-option probabilities plus a "confidence" value. That is enough for AUROC with no extra work.
- **Using decision models as monitors and judges is already an active area, so the general idea is not new.** Within six weeks there have been: a zero-shot alignment-failure detector (median AUROC 0.886, 63x cheaper than LLM judges), two judge-replacement papers with cascades, tool-call gating cookbooks, prompt-injection attacks on Jev, and a GitHub project that uses Jev as a black-box **collusion** monitor on NARCBench.
- **What I did not find:** anyone using a decision model to **forecast** a later rule violation at each step, scoring **lead time**, or comparing decision models with LLM judges **and** white-box probes in a multi-turn recruitment setting. That combination looks novel. "Cheap decision-model monitor" on its own does not.

## 1. The two models

### Jev (TypeSafe)

| | |
|---|---|
| Maker | TypeSafe AI. Founders Diogo Almeida (ex-OpenAI), Erik Gafni and Sasha Sheng ([OpenRouter: What is Jev](https://openrouter.ai/blog/insights/what-is-jev/)). |
| Dates | Early access 2026-09-15 ([TypeSafe launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev)). Waitlist dropped 2026-09-20 ([VentureBeat](https://venturebeat.com/security/companies-are-putting-jev-in-charge-of-ai-agent-decisions-and-prompt-injection-can-influence-the-verdict)). OpenRouter `created`: `~typesafe/jev-latest` and `jev-1.13` on 2026-09-18, `jev-1.14` on 2026-10-14 (API). |
| Price | $0.042/M input, $0 output (API). Context 262,144 tokens. Requests over about 32 KB of text, or with any image, run in a "long-context mode" that TypeSafe calls "slower and less accurate" ([OpenRouter Jev docs](https://openrouter.ai/docs/guides/community/jev)). |
| Training | Proprietary. No weights and no paper. The launch post names a "new model architecture, a parallel sampler" and "Reinforcement Learning for Calibrated Decisions (RLCD)", with no further detail. Almeida told TechCrunch that its edge is synthetic training data ([TechCrunch](https://techcrunch.com/2026/09/30/openais-jev-clone-could-help-the-frontier-lab-stop-its-swarming-agents/)). |
| Output | Four primitives. **Noul**: P(yes) for a proposition, with no confidence field. **Choice**: the chosen option, a probability per option and a confidence. **Score**: a probability-weighted position on ordered levels, a probability per level and a confidence. **Box**: an image bounding box (1.14 only). No rationale and no logprobs. |
| Calibration claims | TypeSafe: "when it says 0.8 … it means that", in aggregate. But VentureBeat quotes TypeSafe's limitations page as saying confidence is "a margin, not a probability that the answer is right". TypedBench finds the hosted model **systematically underconfident** (see below). Calibrate thresholds on our own labels. |
| First-party failure modes | [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13): literal reading, numbers and dates, multi-hop indirection, accuracy that falls as state fills with irrelevant content, **adversarial content in state can steer the answer**, contradictory criteria, and **a bias toward the first option**. Agent traces are not addressed. |
| Vendor benchmarks | Speed of 70–500 ms. "193.6x faster, 444.6x cheaper" on TypeSafe's workflow evals, where the reference is the average of GPT-6 Astra and Fable 5.1, which the post itself flags as a possible bias. No standard benchmarks are published. |

### GPT-6 Luna Decisions (OpenAI)

| | |
|---|---|
| What it is | OpenRouter: "GPT-6 Luna served through OpenAI's Decisions API". OpenAI's guide lists `gpt-6-luna` as the only supported model at `POST /v1/decisions` ([OpenAI Decisions guide](https://developers.openai.com/api/docs/guides/decisions)). Whether it is the same weights with constrained decoding or a separate head is **not stated**. |
| Dates | Previewed at DevDay on 2026-09-29 ([TechCrunch](https://techcrunch.com/2026/09/30/openais-jev-clone-could-help-the-frontier-lab-stop-its-swarming-agents/)). On OpenRouter from 2026-10-06 (API, endpoint `openai/gpt-6-luna-decisions-20261006`). Base GPT-6 Luna dates from 2026-09-22. OpenAI's guide now says "generally available". Secondary reports of the beta and GA dates conflict **[unverified]**. |
| Price | $0.10/M uncached input, $0 output, 1.05M context (API and OpenAI guide). |
| Output | Question types `predicate` (gives `probability`), `choice` (gives choice, `probabilities` and `confidence`) and `score` (gives a probability-weighted score, per-level probabilities and `confidence`). Refusals come back as their own answer type. Input can be an ordered array of messages, **tool calls and tool outputs**, which suits agent traces. Up to 400 questions per request. No logprobs, and no calibration claim: OpenAI says to set thresholds from labelled examples. |
| Evaluations | None published by OpenAI apart from "about 10x faster than the Responses API". Artificial Analysis includes both models in its Decision Index, but the scores are only in charts, so I could not read them ([AA Decision Index](https://artificialanalysis.ai/evaluations/artificial-analysis-decision-index)). |

### Practical notes for our harness

- **Listing.** Decision models are **hidden from the default** `GET /api/v1/models` (469 models, none of them decision models). Use `?output_modalities=decisions` (30 models) or `?output_modalities=all`.
- **Endpoints.** OpenRouter serves `POST https://openrouter.ai/api/alpha/decisions`. Note the "alpha". It also serves `POST /api/v1/systemone`, which is TypeSafe-SDK compatible. Each response carries `usage.cost`.
- **Cost per monitor call** with a 2k-token state: Luna Decisions about $0.0002, Jev about $0.00008. A GPT-6 Luna text judge costs $0.10/M in and $0.50/M out, plus reasoning tokens.
- **Other decision models on OpenRouter as of today** (API `created` dates): Perplexity Decider v1.2 27B and Flash 4B (10-16), Liquid d1 (10-01) and d1-ultra (10-15), Cloudflare Clef, Clef-flash and Clef-omni (open-weight Qwen fine-tunes, 10-01 and 10-09), Microsoft-Decision-1 (10-09), Nace Drex v1.5, v2.0 and Max, ScaleDown Classify-1, Upstage Solar Decide, Inception Mercury Decide (has a free tier), Together Tev1-4B, Jared Palmer Kev-4B (open, LoRA on Qwen3.5-4B), Respan Span-01 and Span-02, and Baseten mammoth-1 and elephant-1 (free).
- **Respan Span-01** is described as a "behavior scoring model": you define plain-language behaviours (for example "tool misuse"), and it returns P(present), P(absent) and P(not observable) for each one. It is the decision model closest to a monitor by design. Its vendor benchmarks are **[unverified]**: the model page returned 404 to my fetcher.
- **Open-weight options** (Clef, Kev, Decider v1.1, Span-02) would let us read the monitor's own activations if we wanted to, and they run on Modal.
- **Repo history.** We already used Luna Decisions as the E01 label judge, and compared it with Jev on 35 episodes (EXPERIMENT_LOG, 2026-10-24).

## 2. Classifier-style models as safety monitors or judge replacements (pre-decision-model literature)

**Guard and moderation models.** These are fine-tuned classifiers with a fixed taxonomy. They usually output a label token, so the score is P(unsafe) read from the token probability.
- Llama Guard (Inan et al., 2023, [2312.06674](https://arxiv.org/abs/2312.06674)): Llama fine-tuned for prompt and response safety classification against a taxonomy. Llama Guard 4 12B is on OpenRouter.
- ShieldGemma (Zeng et al., 2024, [2407.21772](https://arxiv.org/abs/2407.21772)), WildGuard (Han et al., 2024, [2406.18495](https://arxiv.org/abs/2406.18495)), Granite Guardian (Padhi et al., 2024, [2412.07724](https://arxiv.org/abs/2412.07724)).
- gpt-oss-safeguard-20b (OpenAI, on OpenRouter since 2025-10-29): a reasoning model that classifies against a policy you supply ("bring your own policy"). It is the closest older analogue to a decision model with a custom question.
- Constitutional Classifiers (Sharma et al., Anthropic, 2025, [2501.18837](https://arxiv.org/abs/2501.18837)): input and output classifiers trained on synthetic data generated from a natural-language constitution.
- Constitutional Classifiers++ (Cunningham et al., 2026, [2601.04603](https://arxiv.org/abs/2601.04603)): a **two-stage cascade**. Cheap classifiers, including linear probes, screen all traffic and escalate suspicious exchanges. About 40x less compute and a 0.05% refusal rate in production.

**Agent guardrails.** LlamaFirewall ([2505.03574](https://arxiv.org/abs/2505.03574)), GuardAgent ([2406.09187](https://arxiv.org/abs/2406.09187)) and ShieldAgent ([2503.22738](https://arxiv.org/abs/2503.22738)). These are policy checkers that run on the agent's actions.

**Small or fine-tuned judges as LLM-judge replacements.** JudgeLM ([2310.17631](https://arxiv.org/abs/2310.17631)), Prometheus 2 ([2405.01535](https://arxiv.org/abs/2405.01535)), the MT-Bench judge study ([2306.05685](https://arxiv.org/abs/2306.05685)) and a survey ([2411.15594](https://arxiv.org/abs/2411.15594)).

**Cascades and cost-aware monitoring.**
- FrugalGPT ([2305.05176](https://arxiv.org/abs/2305.05176)): LLM cascades for cost.
- Trust or Escalate ([2407.18370](https://arxiv.org/abs/2407.18370)): judge cascades with a guarantee on human agreement. This is the direct ancestor of JEV-as-a-Judge.
- Combining Cost-Constrained Runtime Monitors for AI Safety (Hua et al., 2025, [2507.15886](https://arxiv.org/abs/2507.15886)): how to allocate a monitoring budget across monitors of different cost.

**AI-control and agent-monitoring baselines.** All of these use prompted LLMs as monitors:
- AI Control ([2312.06942](https://arxiv.org/abs/2312.06942)) and Ctrl-Z ([2504.10374](https://arxiv.org/abs/2504.10374)): trusted, weaker monitors.
- SHADE-Arena ([2506.15740](https://arxiv.org/abs/2506.15740)).
- Reliable Weak-to-Strong Monitoring ([2508.19461](https://arxiv.org/abs/2508.19461)).
- CoT Red-Handed ([2505.23575](https://arxiv.org/abs/2505.23575)) and Baker et al. on CoT monitoring ([2503.11926](https://arxiv.org/abs/2503.11926)).
- Constitutional Black-Box Monitoring for Scheming (Storf et al., Apollo, ICML 2026, [2603.00829](https://arxiv.org/abs/2603.00829)): prompted monitors tuned on synthetic trajectories and tested on ControlArena. Performance saturates quickly, and simple prompt sweeps do as well as heavy optimisation.

**Timing of monitoring.** Both papers are directly relevant to our "will break the rule later" framing.
- **SafetyDrift** (Dhodapkar and Pishori, 2026, [2603.27148](https://arxiv.org/abs/2603.27148)) predicts violations before they happen with absorbing Markov chains. It reports 94.7% of violations detected with 3.7 steps of warning, against **per-step LLM judges at 52.6% detection with a 38.2% false-positive rate**.
- **StepShield** (Felicia et al., 2026, [2601.22136](https://arxiv.org/abs/2601.22136)) defines an Early Intervention Rate (alert within k steps of divergence). A regex guardrail reaches 86% recall but its timing is no better than random (EIR 0.23 vs 0.24).

## 3. Decision models specifically as judges and monitors

**Judge replacement (peer-reviewed status unknown, all arXiv preprints from Sep–Oct 2026):**
- **Rao and Callison-Burch, "Decision Models vs. LLMs as Rubric Judges: Cheaper, Faster, and Wrong in the Same Places"** ([2609.29769](https://arxiv.org/abs/2609.29769)). Setup: Jev and Perplexity Decider against three flash-tier LLM judges, on nine panels from seven benchmarks, scored against humans.
  - The decision models trail significantly in at most 6 of 27 comparisons.
  - The LLM judges cost 16–357x more and take 5–350x longer.
  - **Errors are shared:** over 85% of LLM verdicts on a decision model's most confident errors repeat the error, where about 50% would be independent. As a result, cascades gain at most 2.7 points, even with oracle thresholds.
  - Implication for us: a decision-model-then-LLM cascade may buy little, and the two kinds of monitor are not independent.
- **Li et al. (CMU), "JEV-as-a-Judge: Accept When Confident, Escalate When Unsure"** ([2609.26550](https://arxiv.org/abs/2609.26550)). Jev comes within 3 points of GPT-6 on verdicts that can be read from the text, but falls behind on math, code and logic. A cascade with a threshold frozen in advance is 0.9 points more accurate than GPT-6 at 41% of its cost. Jev alone costs 0.36% of GPT-6, with a median of 0.15 s. Confidence routing is weaker on style-adversarial pairs.
- **OpenRouter blog, Jev vs LLM-as-a-Judge** ([link](https://openrouter.ai/blog/tutorials/jev-vs-llm-as-a-judge/)). Vendor-adjacent and small (88 + 50 items). On HaluEval faithfulness, Jev and GPT-5.6 Luna are tied (84 vs 83 of 88), and Jev has the better Brier score (0.043 vs 0.054). On SummEval consistency the LLM is much better (Spearman 0.72 vs 0.47). Jev is about 5x cheaper and 10x faster.
- **TypedBench** (Sharma et al., [2610.11392](https://arxiv.org/abs/2610.11392)): the hosted model follows the stated policy but is **sensitive to wording and systematically underconfident**. Under asymmetric costs, acting on its probabilities can do worse than taking its top answer.
- **Red Hat guardrail benchmark** ([link](https://developers.redhat.com/articles/2026/10/02/benchmarking-ai-decision-models-against-traditional-guardrails)). On prompt injection: Jev 86.4%, DeBERTa 89.0%, Qwen3.6-35B judge 89.3%. On content safety: Jev 86.2%, Qwen judge 85.5%, Granite Guardian HAP 80.3%. Conclusion: decision models are useful where no trained classifier exists, but they were not found to be faster, cheaper or more accurate than the alternatives.

**Safety and alignment detection:**
- **"Just Ask Jev"** (Guo et al., [2609.29429](https://arxiv.org/abs/2609.29429)). RLCDAlignBench covers ten failure types (sycophancy, jailbreak, deception, prompt injection, reward hacking, power seeking and others) over 44 benchmarks and five target models. Results:
  - **Median zero-shot AUROC 0.886** with one generic question.
  - **63x cheaper** than LLM-judge scorers.
  - Matches the reference scorers' agreement with humans.
  - Question wording matters little, and input context matters more.
  - Scoring is per input, not per step and not forecasting. Scheming and sabotage datasets are not listed.
- **jev-collusion-monitor** (GitHub, Rao-Aditya-127, [repo](https://github.com/Rao-Aditya-127/jev-collusion-monitor)). This is **the closest prior work to our project.** Setup: Jev 1.13 is a black-box monitor over **NARCBench** public messages only, and its questions were frozen before the test split.
  - AUROC 0.89 on Core (vote counting scores 0.87; white-box probes 1.00) and 0.82 on Transfer (word overlap 0.60; probes 0.88).
  - It costs about $0.0013 per meeting.
  - A single "is this agent advocating an unsupported outcome" question does as well as the 16-call pair design.
  - It has **no LLM-judge baseline yet**. That comparison is listed as a next step. It scores past behaviour at message and round level, not forecasting. Samples are small (26 and 36 pairs).
- **Agent action gating.**
  - The OpenRouter cookbook [gate tool calls with Jev](https://openrouter.ai/docs/cookbook/building-agents/gate-tool-calls-with-jev) asks narrow Noul propositions per tool call. It approves at ≥0.9, blocks at ≤0.1, and sends anything in between to human review. Including the agent's own `reason` text in state shifted the probabilities, which matters for monitoring adversarial agents.
  - LangChain's `AutoModeMiddleware` gates tool calls by risk class, and its PR excludes tool output from the classifier input so fetched content can't authorise its own actions (per VentureBeat) **[unverified]**.
  - QueryStory hackathon demo: Jev checks every agent action against the task. TechCrunch estimates $2.94 with Jev against $372 with a frontier LLM.
  - Pentest-agent decision layers ([2609.28940](https://arxiv.org/abs/2609.28940)).
- **Attacks on decision-model monitors.** This is a real threat for us, because the rogue agent's text would sit in the monitor's state.
  - Octomind test: a fake "pre-approved" tool-output field cut Jev's block probability for `rm -rf ~/.ssh` from 0.76 to 0.48 ([VentureBeat](https://venturebeat.com/security/companies-are-putting-jev-in-charge-of-ai-agent-decisions-and-prompt-injection-can-influence-the-verdict)). This was a single test.
  - HiddenLayer: indirect injection and clickjacking, plus a TokenBreak bypass of prompt verification. Jev was fooled "less often" than a tuned Qwen, but no numbers were given ([The Register](https://www.theregister.com/ai-and-ml/2026/10/15/jev-and-other-decision-models-can-still-be-tricked-with-prompt-injection/5303184)).
  - **DecisionRobust** ([2610.19118](https://arxiv.org/abs/2610.19118)): "resistance to input perturbations does not necessarily imply resistance to prompt injection".
- **Community tools** from the [awesome-system-one list](https://github.com/andyrewlee/awesome-system-one), all **[unverified]**: Foreman (a supervisor over coding agents), Canny, kadi (a calibrated judge with escalation), jevmon (a process monitor), kettei (a Claude Code PreToolUse hook), Openlayer jevals (agent evals and guardrails as one decision per trace) and Vela (a prompt-attack and PII screen).

## 4. Novelty assessment

**Already done:**
- Decision models as cheap black-box detectors of misbehaviour (Just Ask Jev).
- Decision models as judge replacements, with cascade analysis (Rao and Callison-Burch; Li et al.).
- Tool-call gating (cookbooks and demos).
- A Jev collusion monitor on NARCBench, with a probe reference but no LLM-judge baseline.
- Injection attacks on Jev.

**Not found anywhere:**
1. A decision model asked a **forecasting** question at each step ("will this agent break its operator's rule later?"), scored on **lead time**, in the sense of SafetyDrift and StepShield. Only The Agent Knew asks a per-step forecasting question, and it uses an LLM (see `docs/monitor_baselines.md`).
2. An accuracy-against-cost curve with decision models, LLM judges **and** white-box probes on the same multi-turn recruitment traces.
3. A test of whether a **rogue agent's persuasion text injects the decision-model monitor**. In our setting the attacker's messages *are* the state the monitor reads.
4. The shared-error finding (Rao and Callison-Burch) applied to safety monitors, that is, whether decision-model and LLM-judge monitors miss the same recruited episodes.

So the sprint contribution should be framed as **"per-step forecasting monitors: decision models vs LLM judges vs probes, with lead time and the shared-error rate"**, not as "cheap decision models can monitor agents". Cite Just Ask Jev, jev-collusion-monitor, Rao and Callison-Burch, and SafetyDrift and StepShield as the nearest work.

**Caveats for the design:**
- Jev has a first-option bias, so randomise or swap the option order.
- Jev's accuracy drops on large states full of irrelevant content, and long-context mode starts above about 32 KB. Pass a windowed prefix or summary for each step.
- Calibrate thresholds on our labels. Do not trust vendor calibration claims.
- Report AUROC from the probabilities directly, since logprobs are not needed.

## Provenance

Live API (fetched 2026-10-24):
- https://openrouter.ai/api/v1/models (default list: 469 models, no decision models)
- https://openrouter.ai/api/v1/models?output_modalities=decisions (30 models)
- https://openrouter.ai/api/v1/models/openai/gpt-6-luna-decisions/endpoints
- https://openrouter.ai/api/v1/models/typesafe/jev-1.14/endpoints
- https://openrouter.ai/api/v1/models/~typesafe/jev-latest/endpoints
- arXiv API check of every arXiv ID cited: http://export.arxiv.org/api/query

Vendor and docs:
- https://openrouter.ai/docs/guides/community/jev
- https://openrouter.ai/blog/insights/what-is-jev/
- https://typesafe.ai/blog/introducing-system-one-models-and-jev
- https://docs.typesafe.ai/model-jaggedness/jev-1.13
- https://developers.openai.com/api/docs/guides/decisions
- https://openrouter.ai/docs/cookbook/building-agents/gate-tool-calls-with-jev
- https://openrouter.ai/blog/tutorials/jev-vs-llm-as-a-judge/
- https://artificialanalysis.ai/evaluations/artificial-analysis-decision-index
- https://github.com/andyrewlee/awesome-system-one (community list, used only as a pointer)

Papers (decision models): 2609.29769, 2609.26550, 2609.29429, 2610.11392, 2610.19118, 2609.30216, 2609.28940, 2610.29961 (all at https://arxiv.org/abs/ID).

Papers (background): 2312.06674, 2407.21772, 2406.18495, 2412.07724, 2501.18837, 2601.04603, 2505.03574, 2406.09187, 2503.22738, 2310.17631, 2405.01535, 2306.05685, 2411.15594, 2305.05176, 2407.18370, 2507.15886, 2312.06942, 2504.10374, 2506.15740, 2508.19461, 2505.23575, 2503.11926, 2603.00829, 2603.27148, 2601.22136, 2604.01151.

News and posts:
- https://techcrunch.com/2026/09/30/openais-jev-clone-could-help-the-frontier-lab-stop-its-swarming-agents/
- https://venturebeat.com/security/companies-are-putting-jev-in-charge-of-ai-agent-decisions-and-prompt-injection-can-influence-the-verdict
- https://www.theregister.com/ai-and-ml/2026/10/15/jev-and-other-decision-models-can-still-be-tricked-with-prompt-injection/5303184
- https://developers.redhat.com/articles/2026/10/02/benchmarking-ai-decision-models-against-traditional-guardrails
- https://github.com/Rao-Aditya-127/jev-collusion-monitor

Not read or failed: the OpenRouter model HTML pages (404 to the fetcher; the API was used instead), the Respan Span-01 page (404), and the Artificial Analysis numbers (charts only).
