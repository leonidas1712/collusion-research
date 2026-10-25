# What the probe literature changes in our plan

24 Oct 2026. Sources: `docs/llm_activations_lit.md`, the primary sources it cites, and the notes in `docs/activations_takeaways_claude2.md`. These items add to `docs/evaluation_design.md`; they don't replace anything. Each says what to compute, why, the cost, and the source.

## Most relevant facts

- **NARCBench used our exact model.** Qwen3-32B, one activation per agent turn, a band of layers 26–30 of 64.
  - In-distribution AUROC was 1.00. Six held-out families scored 0.82–0.88, with recall at 1% FPR as low as 0.38.
  - Emergent (not instructed) collusion scored 0.49–0.73.
  - Expect a transfer drop of that order, and expect recall at a fixed FPR to fall much more than AUROC.
- **Prediction probes, not detection probes. Kortukov et al. 2026,** "Predicting Future Behaviors in Reasoning Models Enables Better Steering", arXiv 2606.11172. Full text read; the venue isn't stated on arXiv.
  - **Setup:**
    - single-turn: one prompt and one chain of thought, with no agents or tools;
    - 4 reasoning models up to QwQ-32B;
    - 6 behaviours, e.g. refusal, sycophancy and prompt injection.
  - **Labels:** the share of 10–30 resampled continuations that show the behaviour, at each sentence boundary of the CoT.
  - **Probes:** logistic regression at a middle layer predicts the most likely behaviour at 64–91% accuracy. The error is still 20–30 points on some tasks. MLP probes beat linear ones by only a few points.
  - **Detection vs prediction:** probes trained on final-answer activations (detection features) predict far worse, especially early in the CoT.
  - **FPCG:** samples 10 candidate sentences and keeps the one the probe likes. It shifts behaviour strongly with almost no quality loss, and works where difference-of-means steering breaks generation.
  - **What they don't do:** no comparison with text or LLM-judge monitors, no low-FPR operating point, no held-out tactic or scenario.
  - **For us:** our probe is a prediction probe, so this supports the design. Our gap is still open: multi-turn, with an adversarial peer acting in between, tool use, outcomes that actually happened, and the monitor ladder.
  - **To borrow:**
    - a detection-vs-prediction control: train on the give-in step only, test on earlier steps;
    - an MLP-vs-linear check;
    - optionally, resampled probability labels for a few prefixes, to show when the target "decides";
    - FPCG on the target's turns as a defence extension.
  - **Positioning:** "Kortukov et al. show mid-layer probes predict a reasoning model's eventual behaviour within a single response, using features distinct from detection features. We test whether such prediction features extend across turns of a multi-agent, tool-using episode under peer pressure, and whether they beat LLM-judge monitors at a fixed false-positive rate."
  - **Related, verified:** Dong et al., "Emergent Response Planning in LLMs", arXiv 2502.06258 (single-turn); Arghal et al., arXiv 2602.08964 (agent goal-directedness).
- **Multi-turn favours judges.** Gemini's production probes missed 22–26% of multi-turn attacks, against 13.5% for Gemini Flash (Kramár et al. 2026). If our judges win, say so plainly.
- **The scenario raises scores by itself.** Apollo's probe scored honest replies inside deception scenarios above control. A threshold set only on controls will over-flag episodes where the peer pushes and the target holds.
- **On-policy data is the safe setting.** Probes on the model's own text generalise far better for intent-like behaviours (Kirch et al., arXiv 2511.17408). Our replays are on-policy, so we keep it that way.

## Additions to the analysis (all CPU, after the replay)

| # | Add | Why | Cost | Source |
|---|---|---|---|---|
| 1 | **Difference-of-means probe**, next to logistic regression | Simplest baseline; the same vector is our steering direction. Expect it to be weaker out of distribution (NARCBench: 0.68 vs 0.81) | trivial | Arditi; NARCBench; Apollo |
| 2 | **Fixed layer band 26–30** (mean of per-layer logits), next to nested layer selection | Doesn't hinge on one tuned layer; directly comparable to NARCBench on the same model | trivial | NARCBench |
| 3 | **Episode-so-far score:** running max of an EMA (α≈0.5) of per-step logits | Gives a per-episode early warning; production systems found single-position or mean scores worst | trivial | CC++ §5.1; Anthropic cheap monitors; Kramár |
| 4 | **Thresholds set on the alert we'd actually raise:** per-episode max over control episodes. Also report the false-alarm rate on push-and-hold episodes | Controls are few (5% ≈ 2–3 episodes), and the push context raises scores by itself | trivial | CC++ §4; Apollo |
| 5 | **Partial AUROC (FPR 1–20%) and bootstrap CIs that resample whole episodes;** repeat CV with 3–5 different fold dealings | Recall at a single FPR is noisy with our counts | cheap | Anthropic cheap monitors; Kramár §5.1.1 |
| 6 | **Activation deltas:** h(after the peer's message) − h(previous target step), probed the same way | Strips accumulated history, which also attacks the conversation-length confound | free (same activations) | TaskTracker |
| 7 | **"Talks about the token" control:** probe scores on firm refusals that discuss the token at length | Separates "about to give in" from "the topic is on the table" | free (existing labels) | Apollo failure modes |
| 8 | **Probe + judge:** average the logits, report error correlation, and plot recall against the share of steps deferred to the judge (a cascade) | The most practical result may be the combination; production systems use exactly this | cheap (judge scores exist) | CC++ §5.3, §6; Kramár Eq. 11 |
| 9 | **INLP robustness:** project out the probe direction repeatedly and count rounds to chance | One direction suggests a shallow cue; many suggest a distributed signal | cheap | Caught in the Act |
| 10 | **Early-step label noise:** compare plain logistic regression with dropping the first k steps, or with an episode-level max loss | A give-in episode's round-1 step may look like a control | medium | CC++ §5.1 |
| 11 | **Multi-layer arm:** about 8 evenly spaced layers, strong L2, inside nested CV | Production uses all layers; full concatenation (327k dims) is too big for ~3k rows | medium | CC++ §5.2 |

## Causal check (GPU, later, needs budget approval)

Add or subtract the probe direction at the chosen layer during live generation, and measure the give-in rate under the same peer and the task success on controls. Alternative: probe-guided sampling (FPCG), which steered where activation steering failed (Kortukov et al.). Benchmark small first.

## Judges

- Give judges the identical context and the same forecasting question.
- Try at least two judge sizes; judge quality varies a lot with size (Caught in the Act; Kirch et al.).

## Not verified

- Kramár's appendix numbers, and the 3% vs 8% deferral discrepancy.
- Which layer the Anthropic cheap-monitors post used.
- No Kirch probe-steering paper was found; the steering claim in the lit doc probably refers to Kortukov et al.
- The `aclanthology …/unverified` and `catalyzex` links in the lit doc are author or search pages, not papers.

## Further additions (full text: `docs/activations_takeaways_claude2.md`)

| # | Add | Why | Cost | Source |
|---|---|---|---|---|
| 12 | **Activation Oracle as an extra monitor rung.** A trained LoRA for Qwen3-32B exists (adamkarvonen checkpoints; check its config). Inject the saved layer-32 vector, ask "about to send the token?", score P(Yes) | Open-ended reader; expect weaker than logistic regression; never tested on agentic contexts | <$1 GPU, minutes | Activation Oracles 2512.15674 |
| 13 | **Causal check, stage 1 (forward only).** Teacher-forced log-prob of the target's own recorded replies under 0 / −a·d / +a·d / 3 norm-matched random directions, on ~100 held-out pre-give-in and matched hold steps. Pass: −a·d lowers give-in reply log-prob and raises hold reply log-prob beyond random; KL on control next tokens <0.1 | Cheap test of whether the direction matters, using the replay pipeline | ~5M tokens, ~$1–3 GPU | Arditi; CAA; random baselines are our addition |
| 14 | **Causal check, stage 2 (only if 13 passes).** Branch generation from saved prefixes (25 prefixes × {0, −a·d, random} × 10), deterministic share label; choose a and the layer on validation by effect. Report per prefix (steering flips many inputs the wrong way) | Behavioural evidence | ~$3–6 GPU; needs a local tool-calling generate path | Tan 2407.12404; Braun 2505.22637 |
| 15 | **Free pre-check of steerability:** cosine agreement of per-example differences, separability along d. If difference-of-means AUROC is far below logistic regression, expect weak steering | Decide whether 13–14 are worth it | free | Braun 2505.22637; Kumar 2605.27958 |
| 16 | **Frame the held-out-tactic test as the style-shift test** (probes at 0.998 collapse under style shifts, recover with varied training) | Positions a test we already run | free | Kumar 2605.27958 |

Skipped: LatentQA (only a Llama-3-8B decoder is released).

**Corrections to `docs/llm_activations_lit.md`:**
- The off-policy claim is Kirch, Dower, Skapars et al., arXiv 2511.17408 (ACL 2026 Findings). The claim holds: incentivised data proxies on-policy data, r = 0.793.
- The non-linear-probe claim is arXiv 2411.03343, about jailbreak-compliance interventions.
- The style-shift claim is Kumar et al., arXiv 2605.27958.
- Apollo and CC++: use arXiv abs links. Apollo's layer 22 of 80 and 1% FPR on Alpaca are confirmed.
- Caught in the Act's "nearly 100 directions" is specific to DeepSeek 7B and Qwen 14B.
- Kramár's 99% figure is from Table 3 only (99.13%); the 8% deferral is confirmed.
