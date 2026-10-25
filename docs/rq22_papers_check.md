# RQ 2.2 papers: check against the sources

2026-10-25. The five papers the sprint page cites for RQ 2.2 ("does combining what agents say with what they do beat either alone?"), checked against the arXiv abstract and full HTML. Claims in quotes are the sprint page's wording (`resources.md` §2.2).

Our results this refers to: `EXPERIMENT_LOG.md`, 2026-10-25 entries 05:40–08:50 (E06 monitor-vs-probe table, context ladder, near-term labels, probe refit).

## Summary

| Paper | Sprint-page claim | Verdict | Already in our notes? |
|---|---|---|---|
| Nakamura et al., Colosseum, [arXiv 2602.15198](https://arxiv.org/abs/2602.15198) | Action-level coalition advantage weakly anti-correlates with LLM-judge conversation scores | **Holds, but weak and not significant**: r = −0.243 and −0.143, n = 19 | Yes (related_work, PROVENANCE); r values added |
| Shi et al. 2026a, When Agents Lie, [arXiv 2607.05132](https://arxiv.org/abs/2607.05132) | >90% of deviations from public announcements were already in private plans | **Overstated**: >90% only in the highest-deception conditions; 0–98.6% across games | No (we had Shi et al. 2026b, 2609.24967, a different paper); added |
| Radev et al., SCHEMEs, [arXiv 2605.29178](https://arxiv.org/abs/2605.29178) | Monitors that look for multiple agents coordinating on what they say and do | **Partly**: one monitor sees joint code + messages; the prompt doesn't ask about coordination | No; added |
| Nguyen et al., TraceGuard, [arXiv 2604.03968](https://arxiv.org/abs/2604.03968) | Multi-dimensional action analysis takes a single-dimension monitor from 0% to >70% | **Misquoted**: the paper reports 0% → 95% "safety" for an *untrusted* monitor; the 70.8% is a different monitor | No; added |
| Arike et al., [arXiv 2601.21112](https://arxiv.org/abs/2601.21112) | Less can be more: too much detail can degrade a monitor | **Holds**: the paper names it the "less-is-more effect" | No; added |

## 1. Nakamura et al. 2026, Colosseum

Nakamura, Kumar, Das, Abdelnabi, Mahmud, Fioretto, Zilberstein, Bagdasarian. arXiv 2602.15198, v2 27 May 2026.

**Claim check.** §5.4: "an inverse association between coalition advantage and judge score… r=−0.243 and r=−0.1429 for Emergent and Prompted groups" (Pearson, n = 19 models). Footnote 2: "this may not be a significantly strong relation." No p-values are given. At n = 19 these are about p ≈ 0.32 and 0.56 (my calculation). "Some collusion settings" means the two groups of one experiment. The judge is GPT-5.4 scoring the conversation 0–5.

**Bearing on our results.** Our text monitors show the same gap between what is said and what is done, more sharply. The alarming ones fire on held episodes almost as often as on give-in episodes: GPT-5-nano L2 87% vs 83%, Jev L2 98% vs 98%. So reading the conversation tells you a peer is pushing, not who gives in. Cite Colosseum as motivation only, with "weak, not significant", never as an established anti-correlation.

## 2. Shi et al. 2026a, When Agents Lie

Shi, Zhang, Schölkopf, Conitzer, Jin. arXiv 2607.05132, Jul 2026; Best Paper, ICML NExT-Game workshop. Not the same paper as Shi, Zhang & Yang 2026b (2609.24967, our E04 backup data).

**Claim check.**
- Abstract: the deviation "is predominantly already stated in their private plan (exceeding 90% in the highest-deception conditions)". §4.1 names those: Diners for GPT-5.2 and Llama-4-Maverick, El Farol for Llama.
- Conclusion: the rate varies "0% to 98.6% for the same model". There's no overall figure. A rough unweighted mean over the 18 homogeneous conditions is about 39%. This is my arithmetic on a summary of Table 8, so it is unverified.
- Setup: six repeated n-player games, groups of 5, three models (GPT-5.2, Llama-4-Maverick, Claude-Opus-4.6), 20 trials × 10 rounds.
- Their caveat: the private plan is itself model-generated text.
- So "more than 90% of deviations" holds only for the worst conditions.

**Bearing on our results.** Their "private plan" is the closest thing to our L3 unposted text. In their best cases it gives the deviation away almost every time, but our L3 didn't beat L2 on the eventual label. So our targets mostly don't write the leak down as a plan before doing it. Their own range (0–98.6%) suggests this depends on the setting.

The near-term result fits a weaker version: the Jev forecaster reads the target's recent text and gets 0.66–0.69. So the words may drift just before a leak rather than state a plan. For the write-up, "is the plan in the text?" is a per-setting question, not a given. It is also the question the probe + Jev combination test answers.

## 3. Radev et al. 2026, The Best-Laid SCHEMEs

Radev, Haas, Arnav, Bernabeu-Pérez. arXiv 2605.29178, May 2026.

**Claim check.**
- The setup: agents share a sandbox and a message channel, and pursue a sabotage side task that only works jointly. GPT 5.1 Codex and Gemini 3.1 Pro run 85 trajectories each.
- The monitor (GPT 5.1 Codex Mini) gives one suspicion score from four views:
  - code + messages;
  - code only;
  - messages only;
  - per-agent code slices, averaged.
- Detection at FPR ≤ 2%, Codex sabotage:
  - code + messages 81%;
  - code only 68%;
  - per-agent 61% ("20 pp of total Codex TPR" lost);
  - messages only 46%.
- For Gemini: 99% with code only, 100% with code + messages.
- So there is a joint view of words and actions. But I found no sentence saying the monitor is asked to check consistency *across* agents. The paper says "coordination cues distributed across agents are not fully revealed by any single slice."

**Bearing on our results.** Their code → code + messages gain matches our L1 → L2 gain: adding the peer's messages usually helps. But they monitor the saboteurs and detect an attempt that is under way, which our monitors do well too. We read the target and ask which one gives in, and that's where every monitor sits at 0.48–0.57. The per-agent loss also supports giving our monitor both sides of the conversation rather than the target alone.

## 4. Nguyen et al. 2026, TraceGuard

Nguyen, Nghiem, Tran. arXiv 2604.03968, Apr 2026; from the Apart × Redwood AI Control hackathon, March 2026.

**Claim check.**
- The phrase "0% to >70%" isn't in the paper.
- Abstract: "the untrusted structured monitor achieves 95% safety at moderate thresholds, compared to 0% for single-score untrusted monitoring." "Safety" means the fraction of attack runs detected; no FPR is given for this comparison.
- Both sides of that comparison are an *untrusted* monitor (Claude Sonnet 4, the same model as the agent). The 0% rows come from "earlier experiments", with n = 20 per configuration at threshold 0.3.
- The only "70%" in the paper is a different monitor, bash_heuristic: 70.8% at threshold 0.5.
- The five dimensions it scores:
  - goal alignment;
  - constraint adherence;
  - reasoning coherence;
  - safety awareness;
  - action-trace consistency.
- Hackathon-stage, one agent model, small n. The sprint page's wording should not be repeated.

**Bearing on our results.** Little directly. Its headline is about a monitor that might collude with the agent; ours are trusted models (GPT-5-nano, Luna, Jev), none of them the target. The usable idea is the rubric: score "does the target's stated position match its next action?" (action-trace consistency) as a separate dimension. That is a cheap structured monitor to try if we add a monitor variant. Low priority.

## 5. Arike et al. 2026, information access and sabotage monitors

Arike, Mehta Moreno, Subramani, Biswas, Ward. arXiv 2601.21112, v2 Feb 2026.

**Claim check.**
- Abstract: monitors "often perform better with less information, a phenomenon we call the *less-is-more effect*".
- Their conditions:
  - action-only;
  - CoT-only;
  - CoT + action;
  - extract-and-evaluate (EaE).
- The environments are SHADE-Arena, BigCodeBench-Sabotage and MLE-Sabotage, scored by log-AUROC and TPR at 1% FPR.
- Findings:
  - filtering what the monitor sees helps in 7 of 8 monitor-environment pairs;
  - action-only is worst in 5 of 8, never best;
  - EaE gains 16.8 pp over the next-best method on BigCodeBench-Sabotage, averaged over five attacker models.
- Their explanation: full-context monitors "often notice the side task, but proceed to give a low suspicion score anyway". The agent's own text talks them out of it with post-hoc justifications.
- EaE is two models: one extracts relevant excerpts, the other scores only those.
- Claim confirmed.

**Bearing on our results.** Our ladder has the same shape:
- L1 (actions only) is usually worst, as in their results;
- L2 (+ peer messages) helps;
- L3 (+ unposted text and tool results) hurts GPT-5-nano and Luna, and helps Jev slightly.

This fits less-is-more. Their mechanism is testable cheaply on our saved E06 rationales: at L3, do monitors mention the target's wavering and still score low? Two caveats. Their monitors detect a sabotage attempt, whereas ours forecast an outcome. And our L3 adds tool results and unposted text, not hidden reasoning. If we try one more monitor, EaE at L3 is the best-motivated one.

## What this means for the combination test

- Our setup answers RQ 2.2 in two halves: the context ladder (words vs actions) and probe + Jev combined (internals vs words). Radev and Arike show that what the monitor sees changes results by 10–20 pp. So fix the monitor's view (L2 or L3) on validation data before combining with the probe, not on the test rows.
- None of these five papers combines activations with a text monitor. Gao (2610.04575, outside this list) does: it fuses an activation monitor with Qwen-14B future-outcome forecasts on AgentDojo, and the joint monitor falls short of its frozen detection targets. So our probe + Jev result is a test in a new setting, not a new kind of method. Correction added 25 Oct, evening.
- Wording for the report: "conversation scores track pressure, not outcome", supported by our own held-episode alarm rates, with Colosseum as a weak precedent. Don't use the sprint page's "0% to >70%" or "more than 90% of deviations" as written.
