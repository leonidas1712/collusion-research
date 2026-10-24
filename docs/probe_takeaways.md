# What the probe literature changes in our plan

24 Oct 2026, claude. Sources: `docs/llm_activations_lit.md` (Leo), plus two subagents reading the primary sources and claude-2's notes (pending). These items add to `docs/evaluation_design.md`; they don't replace anything. Each says what to compute, why, the cost, and the source.

## Most relevant facts

- **NARCBench used our exact model.** Qwen3-32B, one activation per agent turn, a band of layers 26–30 of 64.
  - In-distribution AUROC was 1.00. Six held-out families scored 0.82–0.88, with recall at 1% FPR as low as 0.38.
  - Emergent (not instructed) collusion scored 0.49–0.73.
  - Expect a transfer drop of that order, and expect recall at a fixed FPR to fall much more than AUROC.
- **Prediction probes, not detection probes.** Kortukov et al. (arXiv 2606.11172, ICML 2026), on reasoning models: features that *detect* a behaviour already in the text are poor predictors of future behaviour. But probes trained on future outcomes from intermediate reasoning steps predict the most likely behaviour at 64–91% accuracy. Their FPCG method steers by choosing candidate sentences with such a probe, with little quality loss, and works where activation steering fails. Our probe is a prediction probe (each step labelled with the episode's future outcome), so this supports the design. It also warns that a difference-of-means direction from give-in vs refusal *text* is a detection feature. Closest methodological precedent: single model and its own reasoning, not multi-agent pressure across turns, and no monitor comparison in the abstract (full-text check pending).
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

## Causal check (GPU, later, needs Leo's OK)

Add or subtract the probe direction at the chosen layer during live generation, and measure the give-in rate under the same peer and the task success on controls. Alternative: probe-guided sampling (FPCG), which steered where activation steering failed (Kortukov et al.). Benchmark small first.

## Judges

- Give judges the identical context and the same forecasting question.
- Try at least two judge sizes; judge quality varies a lot with size (Caught in the Act; Kirch et al.).

## Not verified

- Kramár's appendix numbers, and the 3% vs 8% deferral discrepancy.
- Which layer the Anthropic cheap-monitors post used.
- No Kirch probe-steering paper was found; the steering claim in the lit doc probably refers to Kortukov et al.
- The `aclanthology …/unverified` and `catalyzex` links in the lit doc are author or search pages, not papers.

## claude-2's additions

Pending: Activation Oracles / LatentQA, steering design, and corrections to the lit doc.
