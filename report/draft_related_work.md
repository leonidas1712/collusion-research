# 2. Related Work (draft)

*Draft prose for Section 2, from `docs/report_plan_outline.md` (Section 2 plan and novelty points). No results in this section. Every citation was checked against its arXiv page on 25 Oct 2026; items still needing a full-text check are listed at the end. Target length about 0.6 page.*

## 2. Related Work

**Probes on a model under attack.** Probes detect prompt-injection exposure in tool-using agents (Dong et al., 2608.02657). Directions from hijacked versus resisted trajectories can cut attack success (Yu et al., 2610.05295). Probes also predict a reasoning model's next behaviour in single-turn settings (Kortukov et al., 2606.11172). Fomin et al. (2606.30449) warn that such probes often read the situation, not the coming action. NARCBench (Rose et al., 2604.01151) reads agents told to collude. *We differ:* we read the agent being recruited by a peer over many turns against its operator's rule. We compare episodes under the same pressure that end differently, the control Fomin et al. find missing.

**Monitoring what agents say and do.** A monitor that sees agents' messages as well as their code catches more coordinated sabotage (Radev et al., 2605.29178). Yet more of the trace often makes a monitor worse (Arike et al., 2601.21112). Conversation-judge scores track actual collusion only weakly (Nakamura et al., 2602.15198). Private plans reveal later deviations at rates that vary widely by game (Shi et al., 2607.05132). *We differ:* these monitors detect an attempt under way. We ask which target will give in, scoring probes and monitors on the same steps, at three levels of access, asked both "is it breaking the rule?" and "will it?"

**Persuasion between agents.** Agents accept secret, unfair arrangements (Zeng & Rudzicz, 2605.27593). Colluding peers sway other agents (Tao et al., 2603.13940) and mislead a decision-maker agent (Bashir et al., 2512.03097). Models yield under sustained multi-turn pressure (Tang et al., 2609.09090). *We differ:* these are measured from text and outcomes only. None reads the persuaded agent's activations or predicts an individual give-in.

**Early warning and combined detectors.** Per-round probe AUROC among episodes still running predicts task failure (Ruan et al., 2607.06503). Per-step false-alarm rates understate per-episode ones (Gao, 2610.04575). Probes paired with prompted classifiers already filter misuse (Kramár et al., 2601.11516; Cunningham et al., 2601.04603). *We differ:* we adopt the per-round metric and per-episode alarm counts. We then test whether a probe adds to a text monitor when predicting a rule violation induced by a peer, including on unseen scenarios.

**What is new.** We separate *eventual* from *imminent* give-in and find only the imminent case predictable. We hold the situation fixed and test directly whether the probe merely detects pressure. Probes and monitors are scored on the same steps, varying what the monitor sees and is asked. We test whether a probe adds to a monitor for this task. Where a second model allows it, we run the same pipeline on a different model family, which gives in by a different route.

> **For the authors (remove before submission):**
> - **Changed from the previous draft:**
>   - "No prior work combines a probe with a text monitor" was false: Kramár et al. pair probes with prompted classifiers for misuse detection, and Constitutional Classifiers++ ensembles linear probes with external classifiers. The claim is now limited to predicting an agent's give-in.
>   - The Shi et al. clause now says rates vary widely by game (0–98.6%), not "only in the most deceptive settings".
>   - Yu et al. now compares hijacked vs resisted runs (an outcome contrast), not "flag that it is under attack".
>   - Many-to-One is added (abstract checked). NARCBench is folded into the probes group, giving four groups as the outline plans.
>   - TraceGuard is dropped to save space; it is a hackathon preprint about monitors that may themselves collude, and our monitors don't.
> - **Still to check against full text:**
>   - NARCBench: "told to collude" holds per our full notes (`docs/related_work.md`). The draft no longer claims "no tools" or "one verdict per game".
>   - SPINE: "yields under sustained pressure" is in the abstract. Our earlier claim that refusal strength doesn't predict collapse is not in the abstract, so it was dropped.
>   - Kramár et al.: "pairing probes with prompted classifiers" is in the abstract. Our notes say the cascade defers about 8% of traffic to Gemini 2.5 Flash (Figure 1 caption), not quoted here.
> - **Quoted numbers:** none, on purpose. The sprint page's TraceGuard "0%→>70%" and the "more than 90% of deviations" reading of Shi et al. are misquotes (`docs/rq22_papers_check.md`).
