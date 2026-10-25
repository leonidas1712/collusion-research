# Recruited: prior-work sanity check

Oct 24, 2026

Reading activations to predict bad behaviour before it happens has been done many times, so that framing alone isn't new; the specific combination in Recruited still looks open.

## Short answer

Several individual pieces of the design have close precedents that should be cited. What a search did not turn up is this combination:

- a **peer agent** persuading a target **over several turns**;
- a target breaking an **operator rule** rather than safety training;
- the main comparison being **gave in vs held under the same pressure**;
- scored **turn by turn within the same round**;
- against a **ladder of text monitors** at the same point in the conversation.

About five papers below were not yet in the related-work notes. Two of them change how the claims should be worded, and one changes a metric.

## Closest neighbours, and how Recruited differs

### 1. Before the Model Caves: pre-capitulation states under multi-turn sycophancy

[GitHub](https://github.com/soham-padia/pre-sycophancy-study). Closest in shape: five open-weight models under steadily escalating social pressure, hidden states extracted every turn, probes trained to catch giving in before it shows.

- Linear probes failed at every layer; non-linear classifiers did about 6.6 points better on average.
- The zero-shot signal peaked around AUC 0.60–0.64.
- The signal was model-specific; probes didn't transfer between models.

**Difference:** a user disputing factual answers, with no peer agent, no operator rule and no tool action. Cite as closest prior work; add an MLP probe as a check given their linear-probe failure.

### 2. Readable Before Actionable: hijacked vs resisted on prompt injection

[arXiv 2610.05295](https://arxiv.org/pdf/2610.05295). Directions estimated from hijacked and resisted AgentDojo trajectories, and editing along them at pre-action positions reduces attack success. So comparing gave-in with held trajectories, plus steering, is already done for injected tool text.

**Difference:** persuasion over several turns by a peer agent, against an operator rule, rather than one injected tool result.

### 3. From Probe Scores to Alarm Policies: high AUROC, useless alarm

[arXiv 2610.04575](https://arxiv.org/html/2610.04575v1). Most important for the metrics.

- On AgentDojo, an activation monitor reached AUROC 0.92 but caught none of 38 positive cases at a 5% false-alarm threshold.
- When one task contains many alarm opportunities, step-level AUROC and false-positive rate don't give the per-task false-alarm rate.
- At 5% per step and 10 steps, the per-task false-alarm rate is about 40% if steps are independent.

**Implication:** the current threshold (5% of control steps) understates false alarms per episode. Report and set the threshold on "any alarm in the episode".

### 4. Internal-State Probes Read the Situation, Not the Action

[arXiv 2606.30449](https://arxiv.org/pdf/2606.30449). Three negative results; the paper a reviewer will cite against this work.

- Their best future-behaviour probe reached AUC 0.80, only 5.1 points above always guessing the majority class.
- A shared-prefix minimal pair had indistinguishable internal states before the first differing input, the same position problem already noted for the backup route.
- Core critique: probes tend to read the situation rather than the upcoming action.

**Defence:** the same-pressure comparison holds the situation fixed and varies only the outcome. Say this explicitly.

### 5. Doomed from the Start: precedent for per-round evaluation

[arXiv 2607.06503](https://arxiv.org/pdf/2607.06503). Plots probe AUC for predicting eventual failure among the episodes still running at each round: essentially within-round AUROC, applied to task failure. Cite as method precedent.

### 6. Apart project: detecting an agent's intent to escape

[Apart sprint project](https://apartresearch.com/sprints/projects/can-we-detect-an-agents-intent-to-escape-before-it-actually-does-so-hg7h). Linear probes caught most escapes ahead of time, but benign runs raised frequent false alarms. Reviewers noted every positive came from an impossible task and every negative from an easy one, so a probe that only detected "this is going badly" would score the same.

**Contrast:** gave-in and held episodes share the same task and pressure. Make this explicit; judges may have seen this project.

## Wider background to cite briefly

- **Predicting future behaviour from internals:**
  - Defection probes predicted when a sleeper-agent model would act on its hidden goal, reading only the prompt ([Anthropic](https://www.anthropic.com/research/probes-catch-sleeper-agents)).
  - An early-warning system built on probes reduced jailbreaking by 91% ([Ashok & May](https://arxiv.org/pdf/2502.13329)).
  - Probes predicted jailbreak success from the prompt's final token with over 80% accuracy on several 3–8B models ([Kirch et al.](https://arxiv.org/pdf/2411.03343)).
  - Future tool calls are decodable from a single frozen hidden state at a decision point ([Reading the Plan](https://www.alphaxiv.org/abs/2610.frozen-states-future-action-prediction)).
- **Early detection of multi-turn attacks with a lead-time metric:** SafeDream measures how many turns before compliance a jailbreak is detected; external rather than activation-based, but a precedent for lead time ([SafeDream](https://arxiv.org/html/2604.16824)).
- **Agent-to-agent persuasion, behaviour only:** [Persuade Me If You Can](https://arxiv.org/pdf/2503.01829) tracks a persuaded model's self-reported agreement to measure persuasiveness and susceptibility; a [multimodal agent-to-agent persuasion](https://arxiv.org/html/2510.22768) study does the same for vision-language agents.
- **Already in the project notes:** Dong et al. on injection exposure ([arXiv 2608.02657](https://arxiv.org/pdf/2608.02657)), NeuroFilter, LAD, CIFT credential probes, NARCBench.

## How to word the claim

Avoid:

- "First to detect misbehaviour before the action": many papers do this.
- "First to detect the effect rather than the attempt": Readable Before Actionable does this for injection.

Safe wording:

> We test whether a target's activations predict giving in to a **peer agent's multi-turn persuasion against an operator rule**, comparing episodes under the **same pressure** that end differently, scored **turn by turn within round**, against text monitors given the same context.

## Changes this suggests

1. **Report false alarms per episode**, not just per step, and set the threshold on that ([Alarm Policies](https://arxiv.org/html/2610.04575v1)).
2. **Add an MLP probe** alongside logistic regression, since [Before the Model Caves](https://github.com/soham-padia/pre-sycophancy-study) found linear probes failed.
3. **Make the same-situation argument explicit in the intro**: it answers [Situation, Not the Action](https://arxiv.org/pdf/2606.30449) and the escape-intent critique directly.
4. **Cite [Doomed from the Start](https://arxiv.org/pdf/2607.06503)** for the per-round AUROC method.

## Sources

- [Before the Model Caves (GitHub, pre-sycophancy study)](https://github.com/soham-padia/pre-sycophancy-study)
- [Readable Before Actionable (arXiv 2610.05295)](https://arxiv.org/pdf/2610.05295)
- [From Probe Scores to Alarm Policies (arXiv 2610.04575)](https://arxiv.org/html/2610.04575v1)
- [Internal-State Probes Read the Situation, Not the Action (arXiv 2606.30449)](https://arxiv.org/pdf/2606.30449)
- [Doomed from the Start (arXiv 2607.06503)](https://arxiv.org/pdf/2607.06503)
- [Can we detect an agent's intent to escape before it actually does so? (Apart)](https://apartresearch.com/sprints/projects/can-we-detect-an-agents-intent-to-escape-before-it-actually-does-so-hg7h)
- [Simple probes can catch sleeper agents (Anthropic)](https://www.anthropic.com/research/probes-catch-sleeper-agents)
- [Language Models Can Predict Their Own Behavior (arXiv 2502.13329)](https://arxiv.org/pdf/2502.13329)
- [What Features in Prompts Jailbreak LLMs? (arXiv 2411.03343)](https://arxiv.org/pdf/2411.03343)
- [Reading the Plan: Multi-Horizon Future-Action Prediction](https://www.alphaxiv.org/abs/2610.frozen-states-future-action-prediction)
- [SafeDream (arXiv 2604.16824)](https://arxiv.org/html/2604.16824)
- [Persuade Me if You Can (arXiv 2503.01829)](https://arxiv.org/pdf/2503.01829)
- [Agent-to-Agent Multimodal Persuasion (arXiv 2510.22768)](https://arxiv.org/html/2510.22768)
- [Your Agentic LLMs Secretly Encode IPI Exposure (arXiv 2608.02657)](https://arxiv.org/pdf/2608.02657)

## Source check (2026-10-24)

All 14 links resolve. Corrections, where the text above goes further than the source:

- **SafeDream is not external to the activations.** It encodes the LLM's hidden states; "external" only means it doesn't change the weights. So it is an activation-based lead-time precedent.
- **Alarm Policies:** AUROC 0.922 is their *secondary* mean-activation monitor. The 40% (exactly 40.1%) is their general Proposition 1 (5% per step, 10 independent steps); their AgentDojo unit is a set of 10 attempts, not 10 steps.
- **Before the Model Caves:** peak AUC is 0.596–0.636, over the 4 probed models (the 5th, Gemma-2-9B, is behaviour only). Transfer is reported to fail "for all within-family pairs", narrower than "between models". No authors or paper; the README says submitted to EMNLP 2026.
- **Kirch et al.:** over 80% for 3 of 5 models (Llama-3.1-8B, Llama-3.2-3B, Ministral-8B); the other two are ≥70%.
- **Reading the Plan:** the alphaXiv link is a slug, not an arXiv id, but it resolves (Advani, Maharjan, Chaturvedi, 8 Oct 2026). No arXiv id found.

Not confirmed:

- **Persuade Me if You Can** scoring by "self-reported agreement": not in the abstract; check the paper.
- **Multimodal persuasion** being behaviour only: inferred from the abstract (function-call outcomes, no activations mentioned).
- **Dong et al.** on Qwen3-8B: the abstract names other models; already on the to-check list in `PROVENANCE.md` §8.

Everything else checked out as written. Rows are in `PROVENANCE.md` §6 and `docs/related_work.md` ("From the prior-work check").
