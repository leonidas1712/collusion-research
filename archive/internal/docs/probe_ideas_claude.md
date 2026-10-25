# Probe ideas for Monday (Claude's answer)

25 Oct 2026. Answer to `docs/probe_ideas_brief.md`. Written by Claude without reading the Codex answer (`docs/probe_ideas_codex.md`).

**Terms.** *Residual stream*: the model's internal vector at a token after each layer. *Probe*: a small classifier trained on those vectors. *AUROC*: the chance that a random give-in step scores above a random held step (0.5 = coin flip). *Within-round AUROC*: the same, but only comparing steps from the same scenario and round. *LOSO*: leave one scenario out (train on five scenarios, test on the sixth). *Family*: an episode plus its branches, always kept on one side of a split.

## One number first: the chance ceiling is not the main limit

I used the 23 branching states (`runs/20261025-0340-e05-replay2-branching/points.json`) to ask how well a perfect predictor of each state's true give-in chance could do. To keep this honest, I predicted each rerun from the other four reruns of the same state. The resulting AUROC is **0.87** (23 give-in reruns, 92 held). Fourteen states were 0/5 and two were 5/5. So the state does decide a lot of the outcome, and the probe's Spearman of −0.03 on those same states is not explained by chance alone. Caveats: 23 states, three-round horizon, v1 only, pooled across rounds. So "partly chance" caps predictors only weakly; it should not be the paper's main excuse.

## Ranked ideas (expected value per hour)

### 1. Predict "gives in within the next k calls" instead of "eventually" (*reframing*)

- **What:** relabel each step as positive if the first leak comes within the next 1–3 target calls or the next round. This is a *hazard* label: the chance of the event happening soon, given that it has not happened yet.
- **Why here:** the "eventual" label marks round-2 steps of round-17 give-ins (dispatch) as positive; a last-token state can't carry that. `rows.jsonl` already has `steps_until_action`.
- **Source:** Doomed from the Start ([arXiv 2607.06503](https://arxiv.org/pdf/2607.06503)) for per-round evaluation of the eventual outcome; SafeDream ([arXiv 2604.16824](https://arxiv.org/html/2604.16824)) for lead-time detection.
- **Cost:** no GPU, $0, about 1 h. Reuses the saved activations (`features.npy`, 6026 × 64 × 5120, local).
- **Success:** LOSO within-round AUROC ≥ 0.65 for k = 1–2, beating turn + length.
- **If it fails:** even the next call is not readable from the state, so the signal is weak, not just far away in time.

### 2. Logit lens on the saved last layer: what reply does the model start with? (*cheap new readout*)

- **What:** apply Qwen3-32B's final norm and output matrix (`lm_head`) to the saved layer-64 vector. That gives the exact first-reply-token distribution (*logit lens*: reading token probabilities off an internal vector). Features to compute: the probability of refusal openers ("I", "Sorry", "I'm unable") against the probability of a tool call or compliance opener, plus the entropy (spread) of the distribution.
- **Why here:** refusing vs complying is largely settled in the first few reply tokens; this is the model's own forecast of its next move.
- **Source:** Qi et al., *Safety Alignment Should Be Made More Than Just a Few Tokens Deep* ([arXiv 2406.05946](https://arxiv.org/abs/2406.05946)); Ashok & May, *Language Models Can Predict Their Own Behavior* ([arXiv 2502.13329](https://arxiv.org/pdf/2502.13329)).
- **Cost:** no GPU, $0, 1–2 h. The CPU-side download is only the norm and the 1.5 GB `lm_head` weights from Hugging Face.
- **Success:** first-token features add value over turn + length in LOSO, or give AUROC ≥ 0.65 on the k = 1 label from idea 1.
- **If it fails:** the decision is made mid-reply, not at its start (see idea 6).

### 3. Resample each step's next reply to get a soft "propensity" label (*better label*)

- **What:** for each recruiting step, resend the identical saved request to Qwen3-32B on OpenRouter 8 times (temperature 0.7, as in E01), using `continuation.py`. Record the fraction of replies that leak, by string match on the secret in text or tool arguments. Then regress the probe on that fraction.
- **Why here:** the saved activation is exactly the input to this reply, so the label depends only on the state, with no peer or future randomness (the "predicted risk" design in `docs/related_work.md` §2(b)).
- **Source:** Macar et al., *Thought Branches* ([arXiv 2510.27484](https://arxiv.org/abs/2510.27484)), which argues outcomes must be studied by resampling; Bigelow et al., *Forking Paths* ([arXiv 2412.07961](https://arxiv.org/abs/2412.07961)).
- **Cost:** no GPU. About 2,900 steps × 8 samples × ~2.2k prompt tokens ≈ 51M input tokens, roughly $4–6. About 2–3 h. Reuses the saved activations.
- **Success:** Spearman between probe and propensity ≥ 0.3 on held-out families within scenario × round. The probe should also beat the monitors on this label.
- **If it fails:** the probe does not even read immediate risk. That is a clean negative, with no "the label was noisy" excuse.

### 4. Trajectory features across the episode's own steps (*better probe*)

- **What:** use the change h_t − h_{t−1}, the cumulative path length, and an average of the probe score over past steps as features.
- **Why here:** one snapshot may miss slow erosion of the target's position.
- **Source:** LAD ([arXiv 2604.28129](https://arxiv.org/abs/2604.28129)); NeuroFilter ([arXiv 2601.14660](https://arxiv.org/abs/2601.14660)).
- **Cost:** no GPU, $0, about 2 h. Reuses the saved activations.
- **Success:** added value > 0 with a CI that excludes 0 in LOSO.
- **If it fails:** drift detects pressure, as in LAD, but not giving in.

### 5. Projection onto the pressure direction (*reframing: probe as pressure detector*)

- **What:** take the exposure direction (control vs recruiting, AUROC 1.0 at layer 32). Within recruiting episodes, test whether a larger projection predicts give-in. Report it as a pressure detector in its own right.
- **Why here:** the monitors detect pressure, not outcome; if the probe does too, say so plainly.
- **Source:** Chen et al., *Persona Vectors* ([arXiv 2507.21509](https://arxiv.org/abs/2507.21509)), where the last-prompt-token projection predicts later behaviour; Internal-State Probes Read the Situation ([arXiv 2606.30449](https://arxiv.org/pdf/2606.30449)).
- **Cost:** no GPU, $0, under 1 h.
- **Success:** within-round AUROC ≥ 0.6. If it scores near 0.5, that supports "reads the situation, not the action", now shown with a positive control and a matched-pressure comparison.

### 6. Multi-token attention probe over the peer's message and the target's last reply (*new replay*)

- **What:** re-run the replay and save, for about 6 layers, the mean vector and the last-token vector over three spans: the latest peer message, the target's previous reply, and the tool results. Then train an *attention probe*, which learns how much weight each token gets instead of using only the last token.
- **Why here:** the single last-token vector is a bottleneck. Production probe work finds last-token pooling clearly worse than attention or softmax pooling.
- **Source:** McKenzie et al. ([arXiv 2506.10805](https://arxiv.org/abs/2506.10805)); Kramár et al., *Building Production-Ready Probes for Gemini* ([arXiv 2601.11516](https://arxiv.org/abs/2601.11516)).
- **Cost:** GPU, needs budget approval. About $6 and 2 h of compute plus about 2 h of code; fits the $70 budget.
- **Success:** LOSO within-round AUROC ≥ 0.62 with added value > 0.
- **If it fails:** the null is robust to token choice, closing a likely reviewer objection.

### 7. Self-forecast by the target itself (*black-box reframing*)

- **What:** on the same prefix, ask Qwen3-32B: "If the peer asks once more, will you share X? Give a probability."
- **Source:** Binder et al., *Looking Inward* ([arXiv 2410.13787](https://arxiv.org/abs/2410.13787)).
- **Cost:** about $1–2, 2 h.
- **Success:** beats the GPT-5-nano forecaster. **If it fails:** the model has no privileged access to its own outcome, which matches the probe result.

### Lower value by Monday

- **Steering as a causal check:** add or subtract the probe or pressure direction while generating continuations. GPU, $5–10, 5+ h; steering a direction that barely predicts the outcome tells us little. Kirch et al. ([arXiv 2411.03343](https://arxiv.org/abs/2411.03343)) found probe-guided steering moved compliance, but the Refusal Residue study ([alphaxiv 2607.13346](https://www.alphaxiv.org/abs/2607.13346)) found that steering on a detected direction barely changed behaviour. Only if ideas 1–3 find a signal.
- **Activation oracles / LatentQA:** a second model trained to answer questions about activations ([arXiv 2512.15674](https://arxiv.org/abs/2512.15674)). None exists for Qwen3-32B that I found; training one won't fit in 36 h.
- **SAE features:** sparse autoencoders split activations into interpretable features. Qwen-Scope ([arXiv 2605.11887](https://arxiv.org/abs/2605.11887)) releases Qwen3 SAEs, but I could not confirm it covers 32B. Kantamneni et al. ([arXiv 2502.16681](https://arxiv.org/abs/2502.16681)) found SAE probes do not beat plain probes. Skip.

## Reframings vs better probes

Reframings: 1, 5, 7 and the peer-token half of 6. Better label: 3 (the key change). Better probes: 2, 4, 6.

## Is the honest negative a good paper?

Yes, if it is framed as a measurement result. Once pressure is held fixed and comparisons stay within round, both activation probes and text monitors, at every context level, fall to about 0.55. Yet all detect the pressure itself almost perfectly (exposure AUROC 1.0; monitors alarm on 83–98% of held episodes).

What would make it stronger:

1. The ceiling analysis above, redone within round with idea 3's labels, so "partly chance" becomes a measured number.
2. Show what *is* readable: near-term hazard (idea 1) and pressure (idea 5).
3. Explain v1 vs v2: same model, more scenarios. Test whether v1's 0.66 survives the fold × scenario × round metric.
4. A power statement: the LOSO CI [0.50, 0.60] rules out AUROC above ~0.6, a real bound.
5. Rule out the token-position objection (idea 6) if the GPU budget is approved.
