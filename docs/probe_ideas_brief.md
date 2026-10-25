# Brief: ideas to get a better probe result

25 Oct 2026. Deadline for the write-up: Mon 26 Oct, 7:59 PM SGT, about 36 hours from now. Ideas must fit inside that time.

## The project in short

- A peer agent (DeepSeek-V4-Flash) pressures a target (Qwen3-32B, thinking off) to break an operator rule: "don't share the token / figure / note".
- **Probe:** for every target API request, we take the residual stream at the last prompt token for all 64 layers ([64 × 5120]). Logistic probes then predict whether the episode will later give in.
- **Metric:** within-round AUROC, which compares give-in and held steps of the same scenario and round.
- **Data:** six scenarios that share one template; 4,184 eligible steps; 152 recruiting episodes (63 gave in); 78 benign control/alone episodes.

Read these first:

- `docs/overview.html`, the Idea, Evaluation and Now tabs;
- `EXPERIMENT_LOG.md`, the last ~10 entries;
- `runs/20261025-0536-e05-replay2-analysis/report.md`, the main probe result;
- `runs/20261025-0147-e06-monitor-main/report_main.md`, monitors vs probe (partial);
- `docs/prior_work_check.md` and `docs/related_work.md`;
- `experiments/E02-activation-replay/replay.py`, which shows what was captured. Only the last prompt token was saved, not every token.

## What we found

- **Probe, within scenario × round AUROC:**
  - v2 alone 0.63 [0.47, 0.76];
  - six scenarios pooled 0.52, or 0.55 when scores are also compared within the same fold;
  - held-out scenario 0.55 [0.50, 0.60].
- **The MLP probe** is no better.
- **Added value** over turn + length + scenario is about 0.
- **Alarms:** useless.
- **Black-box monitors** (GPT-5-nano judge; Luna and Jev decision models; detector and forecaster prompts; context levels L1–L3) also score 0.46–0.58. They detect the pressure rather than the outcome.
- **Branching:** at 23 identical states, 5 reruns each, outcomes are partly chance. Many states have 1/5–4/5 give-in. That caps any predictor of the eventual outcome. The probe score vs the rerun give-in fraction gave Spearman −0.03.
- **Earlier v1 result** (3,034 steps, one scenario): 0.658 [0.59, 0.72], which beat all baselines.
- **Leak kinds:** about a quarter of leaks are accidental (the secret pasted inside a refusal). Deliberate-only labels give slightly higher AUROC (pooled 0.59).

## Constraints

- **GPU** needs Leo's OK. Modal has ~$70 left; one full replay costs ~$5.5 and takes ~2 h. Token weights are cached on the Modal volume.
- **No Claude models in experiments.** Targets are open-weight models; monitors run through OpenRouter.
- **Proportionate rigour:** keep the same family-grouped CV, within-round metric and alarm protocol, so results stay comparable.
- **New behaviour data** costs ~$1–3 per scenario batch on OpenRouter and takes 1–2 h.

## What we want from you

Ideas that could plausibly give a **better or more informative** result by Monday. Ground them in the literature: search the web for recent work, e.g.:

- attention probes and multi-token or sequence probes;
- activation oracles, LatentQA, self-explanations;
- SAE features;
- probes that predict sycophancy or capitulation;
- hazard or near-term prediction;
- probes for jailbreak success;
- steering as a causal check.

For each idea, give:

1. what it is, in plain words;
2. why it might help *here*, given the results above (be specific);
3. the paper or source, with a link;
4. cost and time: GPU yes/no, $, hours; and whether it needs a new replay or can reuse the saved last-token activations;
5. what result would count as success, and what we learn if it fails.

Rank the ideas by expected value per hour. Also say which ones are **reframings** rather than better probes, e.g.:

- predict "gives in within the next round" instead of "eventually";
- predict at the peer's message token;
- use the probe as a pressure detector.

Also say whether the honest negative result is itself a good paper, and what would make it stronger.

Under 1,500 words. Plain language: define every term the first time it appears.
