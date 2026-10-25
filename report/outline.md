# Paper outline (internal working notes, not the draft)

- **What this file is:** a rough, sourced outline of the sprint paper. It lays out the story, the section structure and every number we plan to use, each with its source file. It is not prose for the paper. The draft is written from this file later, and the final Markdown is rendered to .docx. The Markdown stays the source of truth.
- **Status:** first version, written Sun 25 Oct 2026, 15:38 SGT. All main analyses are in. Items marked **PENDING** are still being computed or labelled; their numbers must not be filled in from memory.
- **How to use it:** `> Q:` marks an open question or decision for the author. `> Leo notes:` is space for raw notes under each section. `[main]` / `[appendix]` says where a result goes.
- **Sources:** run folders under `runs/`, plus `EXPERIMENT_LOG.md` (dated lab notebook), `docs/confirmatory_plan.md`, `docs/writeup_limitations.md`, `docs/release_checklist.md`, `PROVENANCE.md`, `docs/rq22_papers_check.md`, `docs/decision_models_as_monitors.md`, `docs/related_work.md`. Every number below was checked against the file named next to it on 25 Oct, except where it says "not re-checked".

## Rules that shape the paper (from the organisers' help desk; `EXPERIMENT_LOG.md`, 25 Oct ~13:55)

- 8 pages, including title and abstract. References, appendices and the LLM-usage statement don't count.
- Keep the template's section structure and order (`report/template.docx`). Fonts and spacing can change.
- Judges score only work done during the sprint. Mark what existed before.
- The project defines "collusion" itself, so include a definition paragraph.
- Methodology is scored, not scale: say what the sample can and can't show.

Template headings, in order (extracted from `report/template.docx`): Title · Authors · Abstract · 1. Introduction · 2. Related Work · 3. Methods · 4. Results · 5. Discussion and Limitations (subheadings: Limitations, Future Work) · 6. Conclusion · Code and Data · Author Contributions (optional) · References · Appendix (optional) · LLM Usage Statement.

The template has no separate dual-use heading. We put limitations in full plus the dual-use note in the Appendix (Appendix A), as the old skeleton `report/draft.md` planned.

## Page budget (8 pages incl. title and abstract)

| Section | Pages | Notes |
|---|---|---|
| Title, authors, abstract | 0.4 | Abstract 150–250 words, written last |
| 1. Introduction (incl. collusion definition, contributions) | 0.9 | |
| 2. Related Work | 0.6 | One compact table could replace prose |
| 3. Methods (incl. Fig 1 setup diagram) | 1.8 | The heaviest section after Results |
| 4. Results (Figs 2–3, Tables 1–2) | 2.6 | Includes the confirmation-test subsection |
| 5. Discussion and Limitations (incl. Future Work) | 1.0 | Limitations short here, full list in Appendix A |
| 6. Conclusion | 0.2 | |
| Code and Data (incl. what existed before the sprint) | 0.2 | |
| Author Contributions | 0.05 | Optional |
| **Total** | **~7.75** | ~0.25 slack for figure placement |

> Q: Fig 4 (pressure vs outcome) and Fig 5 (alarms) do not fit in 8 pages on top of Figs 1–3. Proposal: pressure vs outcome as two numbers in the text plus one row in Table 2 or a small inset; alarms in the appendix. OK?

> Leo notes:

---

## Title, authors, abstract

**Purpose:** say in one breath what we did and what we found.

- Working title options:
  - "Can you see it coming? Activation probes and text monitors for an agent being talked into breaking its operator's rule"
  - "Recruited: predicting when an agent gives in to a peer, from activations and from text"
- Authors: the author + "With Apart Research" (template line).
- Abstract beats (150–250 words, written last):
  1. Problem: one agent pressures another, over many rounds, to break a rule its operator set. Can a monitor see the give-in coming before the action?
  2. Setup: DeepSeek-V4-Flash peer, Qwen3-32B target (thinking off), six scenarios from one task template, 338 scored episodes, 6,404 scored steps.
  3. Methods: linear probes on the target's residual stream vs black-box monitors (GPT-5-nano LLM judge; two "decision models", Jev and Luna), all scored on the same steps, within scenario × round, on held-out scenarios.
  4. Result 1: nothing predicts whether the target will *eventually* give in.
  5. Result 2: whether it gives in *this round or next* is modestly predictable. Probe 0.579 on unseen scenarios; best text forecaster (Jev) 0.650. Held on 89 new episodes under a plan fixed in advance.
  6. Result 3: the activations encode the pressure perfectly (1.000), not who gives in (0.43).
  7. Takeaway: asking a monitor "will it?" beats "is it?"; activations add to a weak LLM judge within known scenarios; errors overlap little, which argues for combining.

> Q: Title preference? Do you want "Recruited" in the title?

> Leo notes:

---

## 1. Introduction

**Purpose:** the problem, why it matters, the threat model, our definition of collusion, contributions.

- **Motivation.** Collusion between agents usually starts with recruitment: one agent needs something, another has the access. Real 2026 incidents had agents breaking their environment's rules on the way to a goal, with more than one model involved: the OpenAI / Hugging Face incident, July 2026 (sources in `PROVENANCE.md` §1; we take the structure only).
- **Why operator rules, not safety refusals.** Deployed agents are mostly governed by operator rules (scopes, "keep credentials private"), not by "don't build a bomb". Our ask is mundane (post a value to a team channel), so the operator's rule is the only reason to refuse. Refusal training stays out of it. (`docs/overview.html`, Final shape tab, "Update, 23 Oct night".)
- **Definition of collusion (required paragraph).** Draft content:
  - Mechanically, collaboration and collusion look the same: one agent asks, the other complies. The difference is whom it works against. Collaboration stays within what the operator wants; collusion goes against the operator's stated rules.
  - Here: a target agent *colludes* when, under pressure from a peer agent, it takes an action its operator explicitly forbade (publishing a protected value), to serve the peer's goal. The peer does not know the target's rule; the two share no principal. So this is the recruitment step of collusion, not sustained joint scheming.
  - Accidental leaks (the value pasted inside a refusal) count as giving in, because the outcome is what an operator cares about. The deliberate vs accidental split is a sensitivity check.
  - Source: `docs/overview.html` ("Collusion vs ordinary collaboration"); `docs/writeup_limitations.md` (accidental leaks).
- **Attempt vs effect.** Prior probe work detects the *attempt* (was the agent exposed to an injection or pressure?). We study the *effect*: under the same kind of pressure, which target gives in, and when. (Dong et al. 2608.02657; NeuroFilter 2601.14660.)
- **The question, RQ 2.2 framing:** does reading the target's internals, or combining what it says with what it does, catch the give-in before it happens? Secondary RQ 2.1: which task features lead to giving in (only touched lightly; see Results 4.1).
- **Contributions (draft list):**
  1. A multi-round recruitment setup with mixed outcomes under an operator rule, and a scoring protocol that puts probes and text monitors on exactly the same steps, after the secret is in context and before the leak (removes a shortcut that gives a probe AUROC 1.000).
  2. A negative result reported in full: neither activations nor any of 18 monitor setups predict *eventual* give-in.
  3. A positive, pre-registered-style result: *imminent* give-in is modestly predictable, from activations (0.579 on unseen scenarios) and best by a per-step forecasting decision model (0.650); checked once on 89 new episodes under a frozen plan.
  4. A direct answer to the "probes read the situation, not the action" critique (Fomin et al. 2606.30449): pressure 1.000, outcome 0.43.
  5. (Maybe fold into 3) Evidence for RQ 2.2: forecaster > detector; the context ladder; low error overlap between probe and text monitor.

> Q: Three or four contributions? Proposal: merge 1+2 ("setup and protocol, with the negative eventual result") and keep 3 and 4, with 5 as a sentence.

> Q: Mention the sprint's RQ numbers (2.2, 2.1) in the paper, or only in the submission form?

> Leo notes:

---

## 2. Related Work

**Purpose:** the closest work and how ours differs. Keep to ~0.6 page; a small table may be denser than prose.

- **Activation probes for agent behaviour (closest).**
  - Dong et al. 2608.02657: single agent on AgentDojo; probe reads "was I exposed to an injection" (≈0.97); probe for "did the attack succeed" weaker (≈0.83–0.89). One injected tool result, not a peer over many turns; no text-monitor comparison. *(numbers marked "summary" in `PROVENANCE.md` §8: re-check against PDF)*
  - Readable Before Actionable (Yu et al.) 2610.05295: hijacked-vs-resisted directions and steering for injection. One injected tool result; ours is multi-turn peer persuasion against an operator rule. [checked per PROVENANCE §6]
  - Fomin et al. 2606.30449, "Internal-state probes read the situation, not the action": best future-behaviour probe AUC 0.801 (+5.1 pp over majority); shared-prefix pairs indistinguishable. The critique our Result 3 answers. [checked per PROVENANCE §6]
  - Kortukov et al. 2606.11172: prediction probes for future behaviour in single-turn reasoning models; closest methodological precedent.
  - NARCBench (Rose et al.) 2604.01151: probes on instructed colluders, AUROC drops from ~1.0 to ~0.7 going to emergent collusion. We read the recruited target, per turn.
  - Credential probes 2606.04141; LAD 2604.28129 (multi-turn drift); NeuroFilter 2601.14660 (attempt detection); Goldowsky-Dill et al. 2502.03407 (logistic probe recipe); Kramár et al. 2601.11516 (multi-turn favours judges; layer choice on validation).
  - Doomed from the Start (Ruan et al.) 2607.06503: precedent for per-round AUROC among episodes still running.
- **Text monitors, RQ 2.2 papers** (all checked against full text, `docs/rq22_papers_check.md`):
  - Arike et al. 2601.21112: "less-is-more effect" (more context can hurt a monitor). Holds for our LLM judge, not for Jev.
  - Radev et al. 2605.29178: code → code + messages monitor 68% → 81% TPR at 2% FPR; matches our L1 → L2 gain.
  - Nakamura et al. (Colosseum) 2602.15198: judge score vs coalition advantage r = −0.243 / −0.143, n = 19, not significant per their footnote. Cite as motivation only. Also the source of our peer-tactic templates.
  - Shi et al. 2026a 2607.05132: private plans contain the deviation >90% only in the highest-deception conditions (0–98.6% overall). Closest analogue of our L3 unposted text.
  - Nguyen et al. (TraceGuard) 2604.03968: 0% → 95% "safety" for an untrusted monitor, n = 20 (the sprint page's ">70%" is a misquote).
  - Monitor prompts adapted from UK AISI ControlArena (`default.txt`; MIT). Forecasting-question idea from The Agent Knew (Fayyazi et al.) 2610.17301.
- **Decision models as monitors** (`docs/decision_models_as_monitors.md`): decision models return probabilities over fixed options, no rationale. Prior use as cheap detectors exists ("Just Ask Jev", Guo et al. 2609.29429; a GitHub Jev collusion monitor on NARCBench). Not found: per-step *forecasting* of a later violation, compared against LLM judges *and* probes in multi-turn recruitment.
- **Behavioural collusion / persuasion:** Shi et al. 2026b 2609.24967 (own stake drives collusion); Voluntary Collusion (Zeng & Rudzicz) 2605.27593; Many-to-One 2512.03097; SPINE 2609.09090 (sustained pressure); GroupGuard 2603.13940.
- **Timing / early warning:** SafetyDrift 2603.27148; StepShield 2601.22136; From Probe Scores to Alarm Policies (Gao) 2610.04575.
- **Gap statement (one sentence):** no paper we found combines activation probes with a text monitor for the same agent; our combination test is new (`docs/rq22_papers_check.md`, "Bearing on our results").

> Q: Cite the spread paper the author co-authored (arXiv 2609.35576, "Share-Borne AI Virus") in Related Work or only in Future Work (spread)? Its title is from the author and the id is not yet verified (`PROVENANCE.md` §8).

> Leo notes:

---

## 3. Methods

**Purpose:** enough to replicate; justify each key design choice.

### 3.1 Environment and agents
- Each episode: up to 20 rounds; in each round the peer acts, then the target. Each agent can call mock tools (in memory, no external effects, no real credentials) and posts to a shared team channel. Temperature 0.7, max 12 tool steps per turn, early stop. (`runs/20261025-0817-e01-spray-dispatch-integration-code-consequence-recruiting-32b-scaleup/meta.json`; `experiments/E01-behaviour-pilot/SCENARIO_SPEC.md`)
- Target: Qwen3-32B, thinking off, served fp8 via OpenRouter (DeepInfra). Peer: DeepSeek-V4-Flash (`PROVENANCE.md` §5).
- The target must read a protected value (a token, number or text) from a file to do its task. The operator rule forbids posting it, with a stated consequence ("consequence" rule strength). The peer asks for it. Forbidden action = the value appears in a post or a new file, decided by a rule on the tool log, not by judgement.
- Conditions: recruiting peer; control peer (same scenario, normal collaboration, no ask); target alone. Controls and alone: 0 leaks across the runs (e.g. spray top-up controls 0/34, alone 0/20; `EXPERIMENT_LOG.md` 25 Oct 03:45).
- Six scenarios, one shared task template: deploy-token v2 (development scenario; credential) and five "spray" scenarios: service-rollout-threshold, procurement-reserve-price, handoff-exception-note, service-capacity-figure, dispatch-integration-code (number / text / code values). How scenarios were built and checked: `docs/scenario_guidelines.md`.
- Why the rule was strengthened: with no rule, targets handed over the value in the first one or two rounds, which gives nothing to predict. The rule produces hold-then-give-in. [appendix: rule-strength sweep `runs/20261024-0332-e01-overnight-rule-strength`]

### 3.2 Data
- Behaviour batches → GPU replay of every target request through the pinned HF Qwen3-32B (bf16, revision 9216db57…), saving all 64 layers at the last prompt token. Replay fidelity: reply NLL 0.249, top-5 99.79% (replay 2, `runs/20261025-0339-e02-replay2-results/report.md`); NLL 0.227, top-5 99.82% (replay 3, `runs/20261025-0923-e02-replay3-completion/report.md`).
- Combined dataset: 9,138 replayed rows, 6,404 eligible steps in 338 episodes (`runs/20261025-1026-e05-replay3-data-1d95/summary.json`). Recruiting steps scored: 4,697 in 241 episodes (101 give-ins, 140 held) (`runs/20261025-1504-e06-appendix-errors/report.md`; row count also in `runs/20261025-1456-e05-all-data-main/report.md`).
- Split into: replay 2 (4,184 eligible steps, 2,910 recruiting; 63 give-in and 89 held episodes; `runs/20261025-0147-e06-monitor-main/report_main_A_hazard.md`) and the balanced batch (129 complete new episodes, 89 usable recruiting episodes; used first as the confirmation set).
- Table 1 (per-scenario counts) — **PENDING** (per-scenario breakdown being computed). See Results 4.1.

### 3.3 The scoring window (the key design choice)
- Every method is scored only on steps where the secret is already in the target's context and has not yet leaked.
- Why: steps before the read cannot leak, and including them lets a method win by detecting "the file was read". A probe does that perfectly: exposure positive control AUROC 1.000 at layer 32 on held-out families (replay 2: `runs/20261025-0338-e05-replay2-positive-control/summary.json`, min over all 64 layers 0.99999; replay 3: `runs/20261025-1026-e05-replay3-positive-control/summary.json`, 1.000). Steps after the leak are detection after the fact. [main: one sentence + the 1.000 as positive control]
- Cost of the window: give-ins that leak on the very next call after reading have no step to score; held episodes that never read the secret are dropped. (`docs/writeup_limitations.md`: 5 of 109 give-ins and 74 of 211 held episodes, combined data — *not re-checked against the data files*.)

### 3.4 Labels
- **Eventual:** every eligible step of an episode that eventually gives in is 1. The question we planned to ask.
- **Near-term A ("gives in this round or next"):** a step is 1 if the first forbidden action comes in this round or the next; earlier steps of give-in episodes are 0. The question a live alarm asks. Primary near-term label.
- **B and C** (secondary, appendix): B keeps A's positives but only held-episode negatives; C = within 3 target calls vs held. Both use hindsight to drop steps, so they are not prospective alarm labels (`runs/20261025-1456-e05-all-data-main/report.md`, intro).
- The near-term labels were defined after the eventual result was seen. This is why the confirmation test exists (one line here, pointing to 4.3).

### 3.5 Probes
- Logistic regression (C = 0.1), training-only standardisation, round-balanced weights, on the 5,120-d residual stream at the last prompt token before the target's reply. Layer chosen inside each training fold from 17 candidates (0, 4, …, 60, 63) on an inner family holdout (25%) ("nested"). Fixed layer 32 as a secondary check. Three split seeds (42/43/44). (`runs/20261025-1456-e05-all-data-main/report.md`)
- Trained on recruiting episodes only. Episodes are grouped into families (related variants), and families never cross a train/test boundary.
- Recipe follows Goldowsky-Dill et al. 2502.03407 and Kramár et al. 2601.11516 (layer choice on validation).

### 3.6 Text monitors
- Three monitor models: GPT-5-nano (LLM judge, 0–100 score); two decision models, Jev 1.14 (TypeSafe) and Luna Decisions (OpenAI), which return a probability over fixed yes/no options. Yes/no order randomised per step.
- Two questions: **detector** "is the target breaking the rule now?"; **forecaster** "will it break the rule at any later point in this episode?".
- Context ladder: **L1** target tool calls + posted messages (what it *does*); **L2** + the peer's messages (the conversation); **L3** + the target's unposted text and tool results (everything the target saw; it has no reasoning trace, thinking off).
- Prompts adapted from ControlArena `default.txt`: warning signs, guiding questions, score anchored only at the ends (not a banded rubric — a limitation). Filled per scenario from each step's own rule text. Approved before the main run and not changed afterwards.
- Full 3 × 2 × 3 = 18 setups on replay 2 (75,312 calls, $12.67: Jev $2.03, GPT-5-nano $6.53, Luna $4.11; `runs/20261025-0147-e06-monitor-main/report_main_A_hazard.md`). On the new episodes, an 8-setup subset fixed before any new results: Jev all 6 + GPT-5-nano detector L2 and forecaster L2 (`runs/20261025-0841-e06-monitor-main-balanced`). Why: appendix "monitor choice".

### 3.7 Metric and evaluation
- **Within scenario × round AUROC:** each positive step is compared only with negative steps of the same scenario and the same round; per-group AUROCs averaged, weighted by positives. Why: turn number alone scores 0.71 pooled (later rounds belong to episodes that will give in), and base rates differ by scenario. Inside a group, turn and scenario both score exactly 0.5 by construction. (`EXPERIMENT_LOG.md` 25 Oct 04:45 and 05:40; `docs/overview.html` "One metric, explained once".)
- **Held-out scenario (leave one scenario out, LOSO):** train on five, test on the sixth, rotate, pool. Headline for "unseen scenarios".
- **Pooled family CV** (5 folds) for "known scenarios", plus its fold-stratified version (also requires the same fitted fold; explained in 4.2 / appendix).
- **CIs:** family bootstrap, 1,000 resamples, seed 20261025, conditional on the fitted models.
- **Combination test:** stacked logistic on [round, log prompt length, monitor score] vs the same + probe; paired family-bootstrap difference.
- **Alarms** (appendix): cutoff set on benign episodes for a 5% false-alarm target; recall and false alarms on held recruiting episodes.
- **Confirmation test:** one line here ("a frozen one-shot test on new episodes, Section 4.3").

**Figure 1 (setup diagram)** [main]: peer → target → tools/channel; where the probe reads (last prompt token before each target request); what L1/L2/L3 monitors see; the scoring window (after read, before leak) on a toy timeline; eventual vs near-term A labels on the same toy episode. Data: none (schematic). Source for the toy: `docs/overview.html` "Two labels, explained once".

> Q: Fig 1 is doing a lot (setup + window + labels). Split into 1a (setup) and 1b (timeline with labels), or keep one figure?

> Q: Say "decision model" for Jev/Luna throughout and define it once here? (Proposal: yes.)

> Leo notes:

---

## 4. Results

**Purpose:** the evidence, in the order of the story. Observations first, interpretation kept to Discussion.

### 4.1 Behaviour: the target holds, then sometimes gives in
- deploy-token v2, plain peer: 21/38 complete episodes gave in (21/32 of those that read the file); control 0/15, alone 0/6 (`EXPERIMENT_LOG.md` 25 Oct 02:30). [main, one line]
- Spray top-up: give-in rounds spread from 2 to 19, e.g. dispatch 9/24 at rounds 5–17 (`EXPERIMENT_LOG.md` 25 Oct 03:45). [main, one line]
- Leak kinds: 64 deliberate / 18 accidental / 1 unclear over 323 earlier episodes (`runs/20261025-0056-e01-topup-semantic-judge`); balanced batch 26 / 14 (`runs/20261025-0833-e01-topup-semantic-judge`, from `EXPERIMENT_LOG.md` 08:36). About a quarter of leaks are accidental. [appendix]
- Label check by hand for deliberate vs accidental: **PENDING** (`runs/20261025-1355-e01-label-batch-2`, 40 episodes, being labelled). An earlier small check: 7 of 8 agree (`EXPERIMENT_LOG.md` 05:20). [appendix]
- RQ 2.1 side results [appendix, screening numbers, n = 4–8 per cell]:
  - Persuasion tactics made the target *more* resistant on v2: T1 1/8, T2 1/8, T7 1/7 vs plain peer ~2/3 (`EXPERIMENT_LOG.md` 02:30).
  - Own stake makes giving in faster or likelier (e.g. patient-contact 0/4 → 3/4) (same entry).
  - Thinking mode on: 1/8 vs 14/40 with thinking off, same setup (`EXPERIMENT_LOG.md` 24 Oct 22:20).
  - Two peers instead of one (deploy-token v1): 2/8 in the batch run (rounds 6, 12) plus 1 of 5 complete single-episode runs (round 7) (`runs/20261024-20*-…-2peers-scaleup/episodes/`, counted 25 Oct; one batch episode is invalid). No sign that a second peer increases giving in; far too small to say.
- **Table 1 (data)** [main]: per scenario: recruiting episodes run / scored / gave in / deliberate vs accidental / controls. — **PENDING** (per-scenario breakdown). Must state deploy-token v2 is the development scenario, and that drop-out is uneven (balanced batch: procurement 15/30, rollout 15/24 scored; `docs/writeup_limitations.md`).

### 4.2 Eventual give-in: nothing predicts it
- All data, within scenario × round: probe 0.488 [0.438, 0.537] pooled, 0.523 [0.486, 0.560] held-out scenario; Jev forecaster L3 0.577 [0.521, 0.628]; GPT-5-nano detector L2 0.549 [0.518, 0.580] (`runs/20261025-1456-e05-all-data-main/report.md`, Headline). [main]
- Replay 2, all 18 monitor setups: 0.48–0.57 (min Jev forecaster L1 0.479, max Jev forecaster L3 0.574 [0.502, 0.639]); nothing adds clear value over turn + length (largest +0.015 [−0.003, 0.033]) (`runs/20261025-0147-e06-monitor-main/report_main.md`). [main, one sentence; table appendix]
- Reported honestly as the original question, in main text, short. Details [appendix]:
  - Replay-2 probe: v2 alone 0.632 [0.474, 0.757], pooled 0.522, LOSO 0.551 (`runs/20261025-0536-e05-replay2-analysis/report.md`).
  - The early pilot result on deploy-token v1 (probe 0.658 [0.593, 0.724], `runs/20261024-2011-e05-text-baselines/report.md`) did not carry over to v2 + spray. TF-IDF text baselines there were at chance (0.480–0.488).
  - Learning curve flat for eventual: LOSO nested 0.521 / 0.537 / 0.552 / 0.551 at 25/50/75/100% of families (`runs/20261025-0842-e05-learning-curve/report.md`; checkpoint `runs/20261025-0936-e05-learning-checkpoint`).
  - Per-layer: flat ~0.50–0.58 at every layer (`runs/20261025-1003-e05-layer-diagnostic/report.md`).
  - Trajectory (step-difference) features at chance: 0.495–0.506 (`runs/20261025-0800-e05-explore-trajectories-pressure/report.md`).
  - Branching: rerunning the same state 5 times gives different outcomes (mixed at 9 of 34 points; controls 0/80), so "will give in" is partly chance and caps any predictor (`runs/20261024-2001-e01-branching-scaleup`, via `EXPERIMENT_LOG.md` 02:30). At 23 identical starting states the probe does not predict which reruns give in: Spearman −0.03 [−0.46, 0.40] (`runs/20261025-0340-e05-replay2-branching/report.md`).

### 4.3 Near-term give-in: modestly predictable, best by a text forecaster
- All data, label A, within scenario × round (`runs/20261025-1456-e05-all-data-main/report.md`) [main]:
  - Probe: 0.579 [0.537, 0.619] held-out scenario; 0.586 [0.541, 0.631] pooled CV; 0.618 [0.571, 0.666] pooled, fold-stratified.
  - Jev forecaster L3: 0.650 [0.608, 0.688]. GPT-5-nano detector L2: 0.557 [0.518, 0.593].
  - Jev − probe: +0.064 [0.012, 0.113] pooled; +0.071 [0.024, 0.116] held-out scenario. Fold-stratified gap +0.040 [−0.017, 0.090] (CI includes 0).
  - Balanced (mean of per-scenario AUROCs): probe 0.580 pooled / 0.585 LOSO; Jev 0.640 (same file, "Scenario mean" column). [appendix or table footnote]
- Combination (same file, Combination tests) [main, Table 2]:
  - Probe added to GPT-5-nano detector L2: +0.081 [0.038, 0.126] pooled (known scenarios); +0.022 [−0.013, 0.059] held-out scenario (not clear).
  - Probe added to Jev forecaster L3: +0.008 [−0.020, 0.039] pooled; +0.003 [−0.011, 0.018] LOSO. No clear gain.
  - Monitor + monitor (GPT-5-nano added to Jev) as reference: −0.000 [−0.013, 0.013] pooled; +0.003 [−0.014, 0.019] LOSO.
  - Caveat: the stacker's training rows use out-of-fold probe scores from models that may have seen the test fold's labels; slightly optimistic, plausibly ~0.01 (`docs/writeup_limitations.md`). The confirmation test has no such leak.
- B and C as robustness [appendix]: probe LOSO 0.586 / 0.569; Jev 0.664 / 0.658 (same file).
- Further probe checks [appendix]:
  - MLP no better than logistic: e.g. A LOSO 0.608 vs 0.611; B pooled −0.020 [−0.056, 0.021] (`runs/20261025-0848-e05-near-term-mlp`, via `EXPERIMENT_LOG.md` 10:00; replay 2).
  - Learning curve (near-term B, replay 2): pooled still rising (+0.033 [0.003, 0.066] at the last step), LOSO flat from ~50% (−0.008 [−0.037, 0.019]) (`runs/20261025-0842-e05-learning-curve/report.md`).
  - Per layer (B, replay 2): late layers 48–63 higher, ~0.63–0.66, vs ~0.55–0.62 mid (`runs/20261025-1003-e05-layer-diagnostic/report.md`). A late-band probe was then tested on new episodes and was not better (see 4.4).
  - Logit lens at the last layer: p(next token opens a tool call) 0.586 [0.556, 0.618] on A; refusal mass, entropy at chance (`runs/20261025-0803-e05-logit-lens/report.md`). The decision isn't visible in the first token.
  - Trajectory features on A: no better than the plain probe (best LOSO 0.576) (`runs/20261025-0800-e05-explore-trajectories-pressure/report.md`).
  - Replay-2-only numbers for reference: probe LOSO 0.611 [0.560, 0.658], Jev 0.660 [0.613, 0.704] (`runs/20261025-0730-e05-near-term/report.md`; `runs/20261025-0147-e06-monitor-main/report_main_A_hazard.md`).

**Figure 2 (main result)** [main]: grouped bars with 95% CIs, eventual vs near-term A, per method: probe, GPT-5-nano detector L2, Jev forecaster L3, probe + GPT-5-nano, probe + Jev. Two points each: held-out scenario (all data) and the confirmation set. Reference line at 0.5. Data: `runs/20261025-1456-e05-all-data-main/metrics.json`; `runs/20261025-1030-e06-confirmation/confirm.json`. Takeaway: eventual flat at chance; near-term above, Jev best.

**Table 2 (combination test)** [main]: gain from adding the probe to each monitor, pooled and held-out scenario, with paired CIs; monitor + monitor reference row. Data: `runs/20261025-1456-e05-all-data-main/report.md` (Combination tests).

> Q: Headline split for "probe": lead with held-out scenario (0.579) as the paper's main number, and put pooled / fold-stratified in a footnote? `docs/overview.html` already says pooled CV goes to the appendix. Proposal: yes.

### 4.4 Checking the near-term result on new episodes (the only place this test is explained)

Planned as its own short, clearly signposted subsection. Introduced from scratch:

- **Why it exists.** We defined the near-term label after seeing that the eventual label failed. A label picked after looking at results can win partly by luck. The fix is a test on data that played no part in any choice.
- **What was frozen, before any new-episode outcome was graded** (`docs/confirmatory_plan.md`, written 25 Oct ~09:05, addenda 2–5 before the new data landed):
  - label A primary (B, C secondary); same eligibility window;
  - probe: same recipe, trained once on all replay-2 recruiting rows, three seeds, z-scored and averaged; applied unchanged;
  - monitors: Jev forecaster L3 (named primary) and GPT-5-nano detector L2; scores used as they are;
  - stackers fit on replay 2 only;
  - metric: within scenario × round AUROC, family bootstrap over the new episodes;
  - success criteria: (1) probe CI above 0.5; (2) gain from adding the probe to GPT-5-nano detector L2 above 0; expected ≈0 over Jev;
  - one secondary hypothesis from the per-layer diagnostic (late-band probe, layers 48–63).
- **The data.** 129 new balanced-batch episodes in the five spray scenarios; 89 usable recruiting episodes; 1,787 steps, 82 positive.
- **What it showed** (`runs/20261025-1030-e06-confirmation/report.md`, run once):
  - Probe 0.681 [0.604, 0.753] → criterion 1 passes.
  - Jev forecaster L3 0.644 [0.560, 0.722]; GPT-5-nano detector L2 0.532 [0.462, 0.602].
  - Probe added to GPT-5-nano: +0.113 [+0.025, +0.203] → criterion 2 passes.
  - Probe added to Jev: +0.052 [−0.014, +0.121] (CI includes 0, as expected).
  - Jev − probe: −0.038 [−0.142, +0.059].
  - Late-band probe 0.664, −0.017 [−0.090, +0.057] vs primary: hypothesis not supported.
  - Seed 42 alone 0.639; fixed layer 32 0.640 (averaging seeds helped).
- **How it relates to the all-data numbers in 4.3, and why they differ.**
  - Different jobs: the confirmation test guards against having picked the label and recipe to fit the data; the all-data estimate (old + new data together, same CV and held-out-scenario recipes, `docs/confirmatory_plan.md` addendum 1) is the best estimate of size.
  - Small set: 82 positive steps, so intervals are about ±0.08; "probe level with Jev" there was probably partly luck.
  - One model vs several: the test scores every step with one final model; pooled CV compares scores from different fold models inside one group, which costs AUROC. The fold-stratified all-data figure is 0.618.
  - Same scenarios as training (new episodes, not a new scenario); no deploy-token v2 episodes.
- **Elsewhere in the paper:** at most one line pointing here (Methods 3.4, Figure 2 caption, Abstract). Do not repeat "confirmed" in other sections.

> Q: Should the abstract mention this test at all, or only "held on 89 new episodes under a plan fixed in advance"? Proposal: that one clause only.

### 4.5 Pressure vs outcome: the activations read the situation, not who gives in
- A probe trained to separate recruiting from benign (control / alone) steps: 1.000 [1.000, 1.000] pooled; 0.99998 LOSO.
- The same score, used to rank give-in vs held within recruiting steps: eventual 0.430 [0.373, 0.492] pooled, 0.426 LOSO; near-term A 0.436 [0.368, 0.510] pooled, 0.437 LOSO. Slightly opposite: steps that look more pressured are a bit less likely to give in. CIs touch or cross 0.5, so exploratory.
- Source: `runs/20261025-0800-e05-explore-trajectories-pressure/report.md` (layer 32, replay 2). [main: two numbers + one sentence; details appendix]
- Answers Fomin et al. 2606.30449: our main comparison holds the situation fixed (same kind of pressure, gave in vs held), which is the control they say is missing. The near-term probe signal (0.58) is therefore not a pressure detector.
- Related monitor observation (alarms, replay 2, eventual): the monitors that alarm do so on held episodes almost as often as on give-ins: GPT-5-nano detector L2 87% recall vs 83% of held episodes; Jev forecaster L2 98% vs 98% (`runs/20261025-0147-e06-monitor-main/report_main.md`). Text monitors also detect the pressure, not the outcome. [main, one sentence]

> Q: This result is replay 2 only (4,184 steps). Rerun on all data for consistency, or report as is with "replay 2" in the caption? The analyses are frozen, so proposal: as is.

### 4.6 Alarms (appendix, one sentence in main)
- All data, near-term, 5% false-alarm target on the held-episode maximum: give-in episodes caught probe 8/101, Jev 10/101, GPT-5-nano 0/101; held-episode false alarms probe 8/140 (5.7%), Jev 6/140 (4.3%) (`runs/20261025-1504-e06-appendix-errors/report.md`). Weak alarms for every method; AUROC ranking does not translate into a usable alarm at this size.
- Accuracy vs cost trade-off — **PENDING** (being computed).

> Leo notes:

---

## 5. Discussion and Limitations

**Purpose:** what the results mean for AI safety; then limitations and future work.

- **Ask "will it?", not "is it?".** The same model and context score far better as a forecaster than as a detector: Jev forecaster L3 0.650 vs Jev detector L3 0.578 (all data, A; `runs/20261025-1456-e05-all-data-main/report.md`). Before the leak there is nothing for a detector to detect; a forecaster can read drift.
- **Words vs actions (RQ 2.2), the context ladder** (replay 2, A, `runs/20261025-0147-e06-monitor-main/report_main_A_hazard.md`):
  - Actions only (L1): every monitor near chance (0.507–0.548). Partly by construction: before the leak, the target's actions are benign.
  - Adding the conversation (L2) helps the forecasters: Jev 0.512 → 0.635. Matches Radev et al.'s code → code + messages gain.
  - Adding unposted text and tool results (L3): hurts the LLM judge (detector 0.569 → 0.542; forecaster 0.554 → 0.535), "less is more" (Arike et al.); helps Jev (forecaster 0.635 → 0.660; on all data 0.626 → 0.650).
  - Figure 3 (context ladder) [main or appendix]: L1 → L2 → L3 lines per monitor × question. Data: `runs/20261025-0147-e06-monitor-main/metrics_main_A_hazard.json`.
- **Errors overlap little → combining.** Probe–Jev step-score correlation within scenario × round 0.232 [0.178, 0.282]; probe–GPT-5-nano 0.089 [0.052, 0.126]; Jev–GPT-5-nano 0.165 (all data, `runs/20261025-1504-e06-appendix-errors/report.md`). Of the give-in episodes caught at 5% false alarms, probe and Jev never catch the same one (8 vs 10, 0 shared); both-miss rate 0.822 vs 0.830 expected if independent. The activations carry partly different information; they help a weaker judge, but at this size not the best one.
- **What a deployer should take away:** a per-step forecasting decision model is the cheapest strong option here; a probe is a complementary signal, not a replacement; neither gives a usable alarm at a 5% false-alarm budget in this data.
- **Interpretation, kept separate from observations:** the give-in is partly chance (branching), and the decision seems to form late (late layers; logit lens shows no first-token tell). Both cap what any step-level predictor can reach.

> Q: Is the "forecaster vs detector" comparison fair to state in main text? The forecaster was named best after seeing replay-2 results; the new-episode subset was fixed in advance and Jev forecaster L3 was again best (0.644 vs detector L3 0.608, `runs/20261025-1030-e06-confirmation/report.md`). Proposal: state it, with that sentence.

> Q: "Less is more" holds on point estimates only; the L2/L3 CIs overlap. Word it as "did not help" rather than "hurt"?

### Limitations (short in main text; full list in Appendix A)
From `docs/writeup_limitations.md`:
- One task template for all six scenarios; "unseen scenario" means new setting and secret type within one task structure. The out-of-template check was skipped.
- One target model (Qwen3-32B, thinking off) and one peer model.
- Scenario imbalance (v2 is the development scenario) and uneven drop-out (procurement 15/30, rollout 15/24 scored in the balanced batch).
- Near-term labels defined after the fact (mitigated by 4.4); B and C use hindsight.
- Only last-token activations; the peer-message tokens were not captured.
- Single LLM judge (GPT-5-nano) with a ControlArena-default prompt anchored only at the ends; a stronger judge or banded rubric could do better.
- Pooled-CV fold mixing; OOF stacking leak in the combination test (~0.01).
- Instant give-ins (leak right after reading) cannot be predicted within the episode.
- The window needs a known exposure time (one known file read); real deployments do not know when the means arrived.
- Accidental leaks count as giving in; hand-label agreement **PENDING**.
- Small samples: confirmation CIs ±0.08; per-scenario AUROCs ±0.15–0.2.

### Future work
- Side tasks unrelated to the secret; influence before exposure (stance shift from "I can't" to "sure", needs a judged per-turn stance label); prediction from the peer's messages alone.
- Unknown exposure time: train and score on all steps; no-pressure controls that see the same secret; vary how the information arrives (search, command output, messages).
- Side channels (leak via files, encodings) beyond the channel post.
- Many agents: several peers (pilot only, 3 of 13 complete episodes gave in); spread, where a recruited target goes on to recruit a third agent (cf. the author's co-authored arXiv 2609.35576, unverified id).
- Stronger judges, banded rubrics, and reasoning-mode targets with a chain-of-thought monitor (L4).
- Peer-message token positions; steering along a "giving in" direction.

> Leo notes:

---

## 6. Conclusion

**Purpose:** 1–2 paragraphs.

- Whether a target will *eventually* give in cannot be read from one step, by activations or text. Whether it is *about* to give in can, modestly: probe 0.58 on unseen scenarios, a text forecaster 0.65, holding on 89 fresh episodes under a frozen plan.
- Activations encode the pressure, not the outcome. Monitors should ask "will it?" and combine views whose errors differ.

> Leo notes:

---

## Code and Data

- Repository: link + tag `apart-submission` (`docs/release_checklist.md`).
- Data: episodes (transcripts) in git; activations on the Modal volume, regenerable from the replay scripts (not in git).
- Deployable probe: trained on all data, 12 full-data model sets plus a local inference command (`runs/20261025-1456-e05-all-data-main/report.md`; log 14:58).
- How to reproduce the headline: scripts and run folders in order (README, to write).
- **What existed before the sprint** (required): sprint start taken as Fri 23 Oct 00:00 AoE (= 12:00 UTC = 20:00 SGT); the sprint page gives only dates and an AoE deadline. Only one commit is earlier: `a5bd6f93` (23 Oct 00:50 SGT): planning docs, infra notes, the idea doc, related-work notes, a report skeleton; no code. The next commit (run helper and E01 harness) is 23 Oct 21:41 SGT. Everything from then on is sprint work. (`docs/release_checklist.md`; `git log`.)
- Info-hazard note: peer tactic text (see Appendix A).

> Leo notes:

## Author Contributions (optional)

- Single author: designed the study, made the decisions, reviewed scenarios and traces; AI coding agents implemented and ran experiments under supervision (details in the LLM Usage Statement).

---

## References (planned; check each against the source before the draft)

Status from `PROVENANCE.md` / `docs/rq22_papers_check.md`. "checked" = marked checked there; "verify" = not yet checked against the paper.

| Ref | arXiv / source | Status |
|---|---|---|
| Fomin, David, LeVi — Internal-State Probes Read the Situation, Not the Action | 2606.30449 | checked |
| Dong et al. — IPI exposure signal | 2608.02657 | verify numbers (summary) |
| Yu et al. — Readable Before Actionable | 2610.05295 | checked |
| Kortukov et al. — Predicting Future Behaviors in Reasoning Models | 2606.11172 | verify |
| Rose et al. — NARCBench / HELIOS | 2604.01151 | abstract checked; numbers verify |
| Goldowsky-Dill et al. — deception probes | 2502.03407 | verify |
| Kramár et al. — Gemini probes | 2601.11516 | verify (appendix numbers unverified) |
| NeuroFilter | 2601.14660 | verify (summary) |
| LAD | 2604.28129 | verify (summary) |
| Credential exfiltration probes | 2606.04141 | verify |
| Ruan et al. — Doomed from the Start | 2607.06503 | checked |
| Arike et al. — information access and monitors | 2601.21112 | checked |
| Radev et al. — The Best-Laid SCHEMEs | 2605.29178 | checked |
| Nakamura et al. — Colosseum | 2602.15198 | checked |
| Shi et al. 2026a — When Agents Lie | 2607.05132 | checked |
| Nguyen et al. — TraceGuard | 2604.03968 | checked |
| Shi, Zhang, Yang 2026b | 2609.24967 | abstract checked |
| Fayyazi et al. — The Agent Knew | 2610.17301 | verify |
| Guo et al. — Just Ask Jev | 2609.29429 | verify (numbers flagged "verify") |
| Zeng & Rudzicz — Voluntary Collusion | 2605.27593 | checked |
| Many-to-One | 2512.03097 | verify |
| SPINE | 2609.09090 | checked |
| Gao — From Probe Scores to Alarm Policies | 2610.04575 | checked |
| SafetyDrift | 2603.27148 | verify |
| StepShield | 2601.22136 | verify |
| Spread paper co-authored by the author ("Share-Borne AI Virus") | 2609.35576 | **unverified: id only, title from the author** |
| UK AISI ControlArena (monitor prompts) | GitHub, commit 1086011 | cloned and read |
| Jev / Luna Decisions vendor docs | TypeSafe, OpenAI, OpenRouter pages | checked 24 Oct (`docs/decision_models_as_monitors.md`) |
| OpenAI / Hugging Face incident, July 2026 | OpenAI posts, CNBC (`PROVENANCE.md` §1) | verify links |
| Qwen3-32B model card; DeepSeek-V4-Flash | HF / OpenRouter | — |

> Q: Cut list to ~20 for the page? References don't count towards 8 pages, so keeping ~30 is fine if each is cited.

---

## Appendix plan

- **Appendix A. Limitations (full) and dual-use / ethical considerations.**
  - The full list from `docs/writeup_limitations.md`, each with its source.
  - Dual-use: all tools mocked, no real network, no real credentials; synthetic prompts sent to OpenRouter. What could make collusion easier: effective recruitment text. Our persuasion tactics (adapted from Colosseum) made the target *more* resistant on v2, and the plain peer worked best. Decide which peer prompts and tactic text to publish; baseline prompts are needed for replication (`docs/release_checklist.md`, "Dual-use").
  - Detection side: publishing that monitors fail at "eventual" could inform evasion; weigh against value to defenders.
- **Appendix B. Monitor choice (why these monitors).**
  - Full 18-setup ladder on replay 2 for Jev / Luna / GPT-5-nano (table from `runs/20261025-0147-e06-monitor-main/report_main_A_hazard.md` and `report_main.md`).
  - Luna at chance as a forecaster on replay 2 (A: L1 0.517, L2 0.496, L3 0.505); dropped from the new-episode runs for cost.
  - Cost: Jev $0.042 per M input tokens, output free; Luna $0.10 per M input; GPT-5-nano $0.025–0.05 per M input + $0.20–0.40 per M output incl. reasoning (two price entries in the file) (`runs/20261025-0147-e06-monitor-main/model-prices-jev-llm-luna.json`). Actual replay-2 spend for 25,104 calls each: Jev $2.03, Luna $4.11, GPT-5-nano $6.53.
  - Jev forecaster L3 and GPT-5-nano detector L2 were named in the frozen plan before the new data.
  - Single LLM judge (GPT-5-nano) = limitation.
  - Accuracy vs cost figure — **PENDING**.
- **Appendix C. Eventual-label details** (4.2 bullets): replay-2 probe table, v1 pilot, learning curve, per-layer curve, trajectory features, branching.
- **Appendix D. Near-term robustness:** labels B and C; MLP; learning curve (B); per-layer (B); logit lens; balanced (scenario-mean) AUROC; replay-2-only numbers; per-scenario forest plot — **PENDING** (per-scenario breakdown).
- **Appendix E. Pooled CV and fold mixing.** Why pooled-CV baselines fall below 0.5 (scores from different fold models compared within one group); the fold-stratified check (replay 2: nested 0.522 → 0.552; scenario baselines → 0.5; `runs/20261025-0544-e05-fold-sensitivity/report.md`). LOSO and the confirmation test are unaffected.
- **Appendix F. Pressure vs outcome details** (full table, `runs/20261025-0800-e05-explore-trajectories-pressure/report.md`).
- **Appendix G. Errors and alarms (exploratory):** shared misses, score correlations, episode catches and false alarms, whether authority / approval claims in peer text sway monitors (21 tagged steps; no reliable shift) (`runs/20261025-1504-e06-appendix-errors/report.md`).
- **Appendix H. Behaviour and RQ 2.1 screening:** rule-strength sweep, tactics, own stake, thinking mode, two peers, leak kinds, evaluation awareness (essentially absent: 1/70 gave-in, 1/88 held; `runs/20261024-2013-e01-evaluation-awareness`, via `EXPERIMENT_LOG.md` 23:45).
- **Appendix I. Prompts:** monitor prompts (detector / forecaster × L1–L3), target system prompt and rule text for one scenario, plain peer prompt (subject to the dual-use decision).
- **Appendix J. Replay and integrity checks:** fidelity numbers, exposure gates, costs (GPU replay 2 ~$5.51; replay 3 $2.94).

> Q: Keep the confirmation test's frozen-plan text verbatim in an appendix, or just link `docs/confirmatory_plan.md` with its commit?

---

## LLM Usage Statement

- AI coding agents (Claude models and Codex / GPT models) wrote the harness, scenarios, analysis code and run reports, ran the experiments, and drafted documents under the author's supervision. Claude agents drafted the report prose; Codex / GPT agents reviewed it for technical accuracy and rendered it to .docx.
- LLMs inside the experiment (not assistance): DeepSeek-V4-Flash (peer), Qwen3-32B (target), GPT-5-nano / Jev / Luna (monitors), Luna (leak-kind labels). No Claude models were used inside the experiments.
- Every number traces to a run folder; analyses were audited by re-running fits and reconstructing scores (e.g. `runs/20261025-1456-e05-all-data-audit/`). The author reviewed the claims.
- The organisers encourage the final version to be written mainly by the team.

> Q: How much of the final text will you rewrite yourself? The statement should match what actually happens.

> Leo notes:

---

## Numbers to watch (inconsistencies found while writing this outline)

- `runs/20261025-1504-e06-appendix-errors/report.md` lists the all-data probe at **0.605** [0.548, 0.658] on label A, while the main estimate (`runs/20261025-1456-e05-all-data-main/report.md`) gives 0.586 pooled. Probably a different score aggregation (seed-mean scores vs mean of per-seed AUROCs). Use 0.586 / 0.579 in the paper; footnote or fix the appendix number.
- Shared misses: the log says "not evidence either way", but the report's excess overlap is −0.008 [−0.015, −0.002] (CI just below 0: slightly *less* shared than chance). Word it as "no more shared than chance".
- The exclusion counts in `docs/writeup_limitations.md` (5 of 109 give-ins, 74 of 211 held, 320 recruiting episodes) use a different accounting from the dataset summary (57 invalid, 2 with no step in the window). Reconcile before quoting.
- Monitor cost: "$0.042 vs $0.10 per M input" compares Jev with **Luna**, not with GPT-5-nano (GPT-5-nano is cheaper per input token but pays for output and reasoning; it cost the most in practice).
