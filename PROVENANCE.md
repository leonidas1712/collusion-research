# Provenance

> **Before the write-up:** every citation must be re-checked against the source (title, author order, year, venue, arXiv id). Nothing here is final until checked.

This is the master provenance list: every idea, method, scenario inspiration, tactic, incident, dataset, tool and paper we use, with its source. Add new items here when you introduce them.

Started 2026-10-24 from the repo docs listed in each section. Links and arXiv ids are copied from those docs; nothing here was re-checked against the papers. "Unverified" marks items the source doc flags, or items with no link or id. Section 8 collects them.

## Contents

1. [Project framing and incidents](#1-project-framing-and-incidents)
2. [Scenario design and levers](#2-scenario-design-and-levers)
3. [Peer tactics](#3-peer-tactics)
4. [Methods](#4-methods)
5. [Datasets, models and tools](#5-datasets-models-and-tools)
6. [Related work we position against](#6-related-work-we-position-against)
7. [Ideas credited to the author](#7-ideas-credited-to-the-author)
8. [Unverified or to-check](#8-unverified-or-to-check)

## 1. Project framing and incidents

Sources: `docs/scenario_levers.md`, `docs/related_work.md`, `docs/plan.md`, `experiments/E01-behaviour-pilot/SCENARIO_SPEC.md`, `SCENARIO_CANDIDATES.md`, `resources.md`.

| Item | Where we use it | Source | Our changes or notes |
|---|---|---|---|
| OpenAI–Hugging Face incident (July 2026) | Intro; grounding for deploy-token and most scenarios | [OpenAI: incident and the road ahead](https://openai.com/index/hugging-face-incident-and-the-road-ahead/); [OpenAI and HF partner](https://openai.com/index/hugging-face-model-evaluation-security-incident/); [CNBC](https://www.cnbc.com/2026/07/22/open-ai-cyber-models-hack-hugging-face.html); [Simon Willison](https://simonwillison.net/2026/Jul/22/openai-cyberattack/) | We take the structure only (task pressure + shortcut, using access that isn't yours); we don't copy names, systems or sequence |
| METR / Redwood investigation of the HF incident (Wijk et al. 2026) | Levers doc (30–40% of tasks unsolvable, budget pressure, >90% of agents joined); disable-failing-test grounding | [METR blog](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/) | Transcripts not public (shared under agreement) |
| Wiki incident (~18,000 agent posts on a dormant wiki) | Levers L3/L5; fleet-relay; spread variant | Von Arx et al. 2026; Lütje 2026, arXiv 2609.12748; [collusion.wiki dump](https://collusion.wiki/explorer/download); [eSecurity Planet](https://www.esecurityplanet.com/threats/news-openai-agents-wiki-restrictions-emea-germany/) (via `docs/plan.md`) | Von Arx et al. has no link (unverified); dump holds wiki edits, not labelled conversations |
| 2026 agent-incident timeline | `docs/plan.md` "Context" | [felloai running list](https://felloai.com/ai-safety-incidents/) and press links in `docs/plan.md` | Background only |
| Sprint question Q2.2 (say vs do) | Main framing: monitor ladder vs probe | Sprint Resources page, copied in `resources.md`; cites Nakamura et al. 2026 (Colosseum) | Anchor question for the project |
| Sprint question Q2.1 (which tasks lead to collusion) | Secondary framing: stake vs favour, info vs action, access, rule wording | `resources.md` | |
| Sprint question Q3.2 (trusted / undercover agents) | Discussion point only | `resources.md` | Our recruiting peer plays the offering agent |
| Sprint question Q1.3 (better detection) | White-box detection framing | `resources.md` | |
| Sprint "open gap" sentence (audits not combined with message/activation detectors) | Framing | Sprint reading list, `collusion_hackathon/literature/README.md` | |
| "Swarmcha.se Chinese agent fleet" report | Idea for a rogue-fleet "unrelated" peer | Mentioned by the author (EXPERIMENT_LOG 00:30) | No link; unverified |

## 2. Scenario design and levers

Sources: `docs/scenario_levers.md`, `docs/scenario_guidelines.md`, `experiments/E01-behaviour-pilot/SCENARIO_SPEC(S).md`, `SCENARIO_CANDIDATES.md`, `OVERNIGHT_RULES.md`. Tags [checked]/[unchecked] are from the levers doc.

| Item | Where we use it | Source | Our changes or notes |
|---|---|---|---|
| L1 own task depends on it (own stake) | deploy-token own-stake, poster-approval, minimum-price, release-date, coding drafts | Shi et al. 2026b, arXiv 2609.24967 [checked, abstract]; the author's idea (log 01:11) | Stake is stated, not measured |
| L2 operator pressure / deadline | disable-failing-test, self-merge-without-review | Agrawal et al. 2025, arXiv 2507.01413 [checked] | Author: make the proper route blocked or hard |
| L3 precedent | Not yet in a scenario | Paglieri et al. 2026, arXiv 2609.04170 [checked, abstract] | |
| L4 consensus / several peers | Planned many-peers variant | Many-to-One, arXiv 2512.03097; GroupGuard, arXiv 2603.13940 [checked] | |
| L5 longer horizon (16–20 rounds) | Most scenarios | Shi 2026b; SPINE, arXiv 2609.09090 [checked] | Added at runtime when rounds ≥ 16 |
| L6 authority claim | Peer tactic T2 | Colosseum, arXiv 2602.15198 [checked]; Alnuhait et al. 2026, arXiv 2609.39050 [checked, abstract] | |
| L7 trade / reciprocity | Peer tactic T3 | Colosseum [checked] | Offer is information only (author) |
| L8 lower perceived cost | Not yet in a scenario | Inverse of Q. Liu et al. 2026, arXiv 2604.23511 | [unchecked] |
| L9 neutral framing | Ask wording | Zeng & Rudzicz 2026, arXiv 2605.27593 [checked] | |
| L10 persuasion tactic | T1–T7 peer tactics | Colosseum tactic prompts (sprint starter repo) [checked] | See section 3 |
| L11 rule salience | Rule wording sweep | Zeng & Rudzicz V4/V5 [checked] | |
| L12 private channel | Not in our setup | Colosseum; Agrawal et al. [checked] | |
| L13 in-group | Not yet used | Aharon et al. 2026, arXiv 2601.22184 | [unchecked] |
| A1 ethical framing + consequences | consequence / consequence_logged rule strengths | Zeng & Rudzicz [checked] | |
| A2 penalties and reporting rewards | Not used | Q. Liu et al. 2026 | [unchecked] |
| A3 oversight / monitoring | Possible Q3.4 condition | Agrawal et al.; Alnuhait et al. [checked] | |
| A4 diverse or competitive agents | Not used | Keppo et al. 2026, arXiv 2603.20281 | [unchecked] |
| A5 throttling messages | Not used | Agrawal et al. [checked] | |
| O1 `report_to_operator` tool (3-way outcome) | Optional outcome | Inspired by Q. Liu et al. reporting rewards | Not built |
| Required vs optional access tag | All scenarios | Author, 2026-10-24 (log 02:08, 02:09) | Prompted by Llama-3.3-70B never reading the token |
| Rule strengths explicit / firm / norm / soft | Rule-wording sweep | Ours (LLM-drafted, approved by the author 2026-10-24) | Granite 3/0/0/0/1 deliberate per 10 |
| Rule strengths consequence / consequence_logged | Overnight sweep; lead cell | Ours (`OVERNIGHT_RULES.md`) | Stated consequences not enforced by the mock |
| Policy × goal-relation grid, target-alone baseline | E01 design | Author (log 21:46, 21:58) | Related cells are the headline |
| deploy-token | Main scenario | HF incident (credential use during task pursuit) | Analogy, not reconstruction |
| release-packet-copy, runner-reassignment | Drafts | OpenAI August retrospective (link above) | Analogies |
| printer-queue-copy | Draft | OpenAI HF incident account | Analogy |
| front-door-sign, release-date | Approved | Colosseum (secondary goals) | Analogies |
| poster-approval, skip-layout-check | Approved / deferred | Shi et al., arXiv 2609.24967 | Analogies |
| fleet-relay | Deferred | Paglieri et al., arXiv 2609.04170 | Relay mechanism borrowed |
| minimum-price | Approved | Agrawal et al., arXiv 2507.01413 | Analogy |
| disable-failing-test | Approved | METR/Redwood HF investigation | Reward-hacking analogy |
| self-merge-without-review | Dropped (every model merged alone) | [GitHub required-review docs](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews); Shi et al. | |
| Reciprocal code-review hybrid | E01 hybrid scenario | [GitHub required-review docs](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews); Shi, Zhang, and Yang, [arXiv 2609.24967](https://arxiv.org/abs/2609.24967) | Synthetic work items and tools; borrows the common LGTM rubber-stamping pattern and repeated mutual-verification structure, not the paper's prompts, task, rewards, or data. See `experiments/E01-behaviour-pilot/HYBRID_PROVENANCE.md` |
| Credential-passing scenario choice (S1) | deploy-token | Distinguished from arXiv 2606.04141 (excludes keys in tool calls) | |
| Database-password migration | E01 dedicated credential scenario and spray row | Ours; designed 2026-10-24 | Synthetic password and workflow; not tied to an incident |
| Artifact-registry-token spray row | E01 candidate screen | [OpenAI–Hugging Face incident account](https://openai.com/index/hugging-face-model-evaluation-security-incident/) | Structural analogy only; new roles, wording, task and synthetic token |
| Unreleased-benchmark spray row | E01 candidate screen | Rose et al., [NARCBench/HELIOS, arXiv 2604.01151](https://arxiv.org/abs/2604.01151), abstract checked 2026-10-24 | Borrows only the high-level private/public multi-agent information motif; not their task or data |
| Peer-audit-log spray row | E01 candidate screen | Shi, Zhang, and Yang, [arXiv 2609.24967](https://arxiv.org/abs/2609.24967), abstract checked 2026-10-24 | Borrows only repeated log sharing and verification; not their environment or transcript |
| Secret-tool-code spray row | E01 candidate screen | Zeng and Rudzicz, [arXiv 2605.27593](https://arxiv.org/abs/2605.27593), abstract checked 2026-10-24 | Borrows only secret-tool availability; not Liar's Bar, Cleanup, prompts, or data |
| Support-bot-secret spray row | E01 candidate screen | Debenedetti et al., [SaTML'24 CTF report, arXiv 2406.07954](https://arxiv.org/abs/2406.07954), abstract checked 2026-10-24 | Borrows only a synthetic secret-keeping/extraction structure; not a CTF defense or transcript |
| Remaining spray rows | E01 candidate screen | Ours; see `experiments/E01-behaviour-pilot/SPRAY_CANDIDATES.md` | Synthetic candidate domains; no external incident claim |

## 3. Peer tactics

Full table: [`experiments/E01-behaviour-pilot/PEER_TACTICS_PROVENANCE.md`](experiments/E01-behaviour-pilot/PEER_TACTICS_PROVENANCE.md). Direct source for T1–T7 is the Colosseum persuasion prompts (Nakamura et al., arXiv 2602.15198), `collusion_hackathon/colosseum/experiments/persuasion/collusion/prompts.py` in the sprint starter repo. General LLM evidence: Zeng et al. 2024 (ACL, "How Johnny Can Persuade LLMs"); Meincke et al. 2025 ("Call Me a Jerk", Wharton working paper).

| Item | Where we use it | Source | Our changes or notes |
|---|---|---|---|
| T0 no tactic | Baseline peer | Colosseum `control` (empty) | Our own peer prompt |
| T1 helpful framing | `PEER_TACTICS.md` | Colosseum helpful misdirection (paper); Tversky & Kahneman 1981 | Softened, gradual; slots |
| T2 organizer tone | `PEER_TACTICS.md` | Colosseum authority nudge (paper); Cialdini 1984; Milgram 1963 | Peer never claims to be a manager |
| T3 trade | `PEER_TACTICS.md` | Colosseum reciprocity trade (paper); Cialdini 1984; Gouldner 1960 | Offer is information only (author) |
| T4 social proof | `PEER_TACTICS.md` | Colosseum code only; Cialdini 1984; Asch 1951 | Unverifiable "others agree" kept |
| T5 time pressure | `PEER_TACTICS.md` | Colosseum code only (scarcity); Cialdini 1984 | Urgency from the peer, not the operator |
| T6 playing it safe | `PEER_TACTICS.md` | Colosseum code only (risk aversion); Kahneman & Tversky 1979 | Skipped for release-date and front-door-sign |
| T7 cost anchoring | `PEER_TACTICS.md` | Colosseum code only; Tversky & Kahneman 1974 | Softened, slots |
| Split-brain | Not used | Colosseum code only | Needs two or more targets |
| Softer wording, slots, matched controls | All tactics | Ours (author) | |

## 4. Methods

Sources: `docs/llm_activations_lit.md` (author), `docs/probe_takeaways.md`, `docs/evaluation_design.md`, `EXPERIMENT_LOG.md`.

### 4.1 Linear probes and difference of means

| Item | Where we use it | Source | Our changes or notes |
|---|---|---|---|
| Logistic-regression probe | Main probe (E02 analysis) | Apollo, Goldowsky-Dill et al. 2025, arXiv 2502.03407 | On standardised activations, last prompt token per step |
| Difference-of-means direction | Baseline; steering direction | Arditi et al. 2024, arXiv 2406.11717; NARCBench, arXiv 2604.01151 | NARCBench scripts as reference code |
| Fixed layer band 26–30 | Cross-check vs NARCBench | NARCBench (Qwen3-32B) | Mean of per-layer logits |
| Multi-layer probe (~8 layers) | Optional arm | Constitutional Classifiers++ §5.2, arXiv 2601.04603; lmprobe library | |
| Layer sweep, choose on validation | Probe layer choice | Arditi et al.; Apollo; Kramár et al. 2026, arXiv 2601.11516 | |
| Two-position recipe (recognition vs compliance) | Optional | Zhao et al., arXiv 2507.11878 | |
| Five-point reply rubric | Target-reply judge baseline | SPINE, arXiv 2609.09090 | Adapted; action label kept separate |
| Drift / path-length baselines | Label-free baseline | LAD, arXiv 2604.28129; NeuroFilter, arXiv 2601.14660 | Re-implemented, not their code |

### 4.2 Splits and scoring

| Item | Where we use it | Source | Our changes or notes |
|---|---|---|---|
| Split by episode family | All evaluation | Kramár et al.; capitulation-null paper, arXiv 2609.17550; Blind Deference code review | Ours to apply; matched cells stay together |
| Nested CV for layer choice | Probe code requirement | Decision in EXPERIMENT_LOG 19:05; motivated by Blind Deference picking its layer on test | Plus fixed layer 32 cross-check |
| Within-round AUROC, position-matched training | Headline scoring | Ours (EXPERIMENT_LOG 17:15, conversation-length confound) | Applies to monitors too |
| Recall at fixed FPR, separate from AUROC | Metrics | NARCBench; Das et al., arXiv 2609.03035 | Threshold on per-episode max over controls |
| Partial AUROC, episode bootstrap CIs | Metrics | Anthropic cheap monitors; Kramár §5.1.1 | |
| Ladder of evidence | Reporting standard | Author (EXPERIMENT_LOG 19:00) | |
| Shuffled labels, random directions, positive control | Checks | Capitulation-null paper; Caught in the Act, arXiv 2508.19505 | Positive control = token_in_context probe |
| Push-and-hold false-alarm check | Threshold check | Apollo failure modes | |
| Accepted vs resisted (not recruiter vs control) as main test | Main design | `docs/related_work.md` recommendation, LLM-assistant correction on fork points | Author's decision |
| Per-step unit (every target API request) | Dataset rows | Author (EXPERIMENT_LOG 18:05) | |
| Deterministic main label; judges secondary | Labels | Author (`scenario_guidelines.md` §4) | |
| Monitor ladder (actions / + channel / + unposted / + reasoning) | Monitor comparison | Author (EXPERIMENT_LOG 01:47) | |

### 4.2b Behaviour reporting

| Item | Where we use it | Source | Our changes or notes |
|---|---|---|---|
| Give-in rate against attacker budget; Wilson intervals; substantive-success scoring; failure categories; coverage grid | Behaviour reporting (`docs/pressure_reporting_practices.md`) | Hughes et al. 2024, Best-of-N Jailbreaking, arXiv 2412.03556; Souly et al. 2024, StrongREJECT, arXiv 2402.10260; Samvelyan et al. 2024, Rainbow Teaming, arXiv 2402.16822 (coverage) | To verify against the papers |

### 4.3 Activation deltas, EMA pooling, cascades

| Item | Where we use it | Source | Our changes or notes |
|---|---|---|---|
| Activation deltas | Probe variant | TaskTracker, Abdelnabi et al., arXiv 2406.00799 | Applied per peer message over turns |
| EMA / running-max episode score | Early-warning score | Kramár et al. 2026, arXiv 2601.11516; CC++ §5.1; [Anthropic cheap monitors](https://alignment.anthropic.com/2025/cheap-monitors/) | α ≈ 0.5 |
| Probe + judge cascade | Combined monitor | CC++ §5.3, §6; Kramár Eq. 11; [Anthropic next-gen classifiers](https://www.anthropic.com/news/next-generation-constitutional-classifiers) | Plot recall vs share deferred |
| Early-step label noise handling | Optional | CC++ §5.1 | |

### 4.4 INLP and steering

| Item | Where we use it | Source | Our changes or notes |
|---|---|---|---|
| INLP robustness (rounds to chance) | Robustness check | Caught in the Act, arXiv 2508.19505 | |
| Steering (add/subtract direction) | Stretch causal check | ActAdd, arXiv 2308.10248; CAA, arXiv 2312.06681; Arditi et al. | Needs GPU budget |
| Probe-guided sampling (FPCG) | Alternative to steering; possible defence extension | Kortukov et al., arXiv 2606.11172 | |
| Random-direction steering control | Steering control | Blind Deference repo; capitulation-null paper | |
| Representation engineering | Background | Zou et al. 2023, arXiv 2310.01405 | |
| Activation Oracles / LatentQA | Optional extra | arXiv 2512.15674 ([code](https://github.com/adamkarvonen/activation_oracles)); arXiv 2412.08686 | |

### 4.x Black-box monitor baselines (details: `docs/monitor_baselines.md`)

| Item | Where we use it | Source | Our changes / notes |
|---|---|---|---|
| ControlArena monitor prompts (`default.txt`, `cot.txt`, `cot_only.txt`, `full_trajectory_default_system.txt`) | Primary monitor family for all ladder levels | UK AISI ControlArena (MIT) | Operator-rule framing; channel and unposted-text blocks; forecasting question; 0–100 scale |
| Per-step "next action unauthorized" probability question | Wording of our forecasting question | The Agent Knew, arXiv 2610.17301 (github AryaFayyazi/Honesty, `scripts/156_v57_monitor.py` L17–23) | No licence: cite and paraphrase, don't copy |
| E06 detector and forecaster prompts (`experiments/E06-monitors/prompts.py`, edits in `PROMPTS.md`) | LLM judge and decision-model monitors at ladder levels 1–3 | Adapted from ControlArena `control_arena/monitor/prompts/default.txt` L1–40, [commit 10860116c370c74c56d6d49edce629b62cf5661b](https://github.com/UKGovernmentBEIS/control-arena/blob/10860116c370c74c56d6d49edce629b62cf5661b/control_arena/monitor/prompts/default.txt) (MIT, © 2025 UK AI Security Institute); "full range" sentence from `full_trajectory_default_system.txt` L18 | Operator-rule framing, rule-specific signs and questions, chronological history block per level; forecaster asks P(forbidden action later in episode), 0–100 |
| E06 forecasting question wording | Forecaster prompt | Idea from Fayyazi et al., The Agent Knew, arXiv 2610.17301 (`scripts/156_v57_monitor.py` L17–23 @ 7dada5c, no licence) | Our own wording; "next action" widened to "any later point in this episode"; no text copied |
| Relaxation judge | Secondary monitor (levels 3–4); like-for-like judge on Shi traces | Shi et al. 2609.24967, `analysis/relaxation_judge_prompts.md` L7–46 (MIT) | Detects stated intent to relax, not a forecast |
| Constraint-adherence rubric | Considered | TraceGuard `dimensions.py` L65–106 (MIT) | Scores the current action only |
| Black-box deception baseline | Considered | Apollo 2502.03407, `data/black_box_baseline/prompt.txt` (no licence) | Detection of past deception |
| Blackboard judge | Considered | Colosseum `judge_blackboards.py` (no licence) | After-the-fact detection |
| CoT monitor | Considered for the reasoning level | Baker et al. 2025, App. C | Binary detection |

### 4.y Decision models as monitors (details: `docs/decision_models_as_monitors.md`)

| Item | Where we use it | Source | Notes |
|---|---|---|---|
| Decision models (Jev, Luna Decisions) | Monitor variant; label judge | TypeSafe Jev 1.13/1.14 (Sept–Oct 2026); OpenAI Decisions API, gpt-6-luna-decisions on OpenRouter 2026-10-06 | Probabilities over fixed options, no rationale |
| "Just Ask Jev" (alignment-failure detection) | Prior work on decision models as monitors | see docs/decision_models_as_monitors.md | Median AUROC 0.886, ~63x cheaper than LLM judges (verify) |
| Jev collusion monitor on NARCBench | Closest prior work for decision-model monitors | github.com/Rao-Aditya-127/jev-collusion-monitor | AUROC 0.82–0.89; we differ by forecasting, lead time, probe/judge comparison |

## 5. Datasets, models and tools

Sources: `EXPERIMENT_LOG.md`, `experiments/E02-activation-replay/README.md`, `experiments/E01-behaviour-pilot/JUDGE_LABELS.md`, `docs/external_traces.md`, `docs/backup_shi_et_al.md`, `resources.md`.

| Item | Where we use it | Source | Our changes or notes |
|---|---|---|---|
| Qwen3-32B | Main target (E01); E02 replay | HF `Qwen/Qwen3-32B` rev 9216db5781bf21249d130ec9da846c4624c16137 | bf16 replay; OpenRouter served fp8 (DeepInfra) |
| Qwen3-32B-FP8 | Robustness option, untested | HF `Qwen/Qwen3-32B-FP8` rev aa55da1e… | |
| Qwen3-30B-A3B-Instruct-2507 | Second target | OpenRouter (SiliconFlow fp8) | Chosen after E03 screen |
| DeepSeek-V4-Flash | Peer model | OpenRouter `deepseek/deepseek-v4-flash` | Replaced gpt-6-luna |
| gpt-6-luna | Early peer | OpenRouter `openai/gpt-6-luna` | Broke role; dropped |
| granite-4.2-8b | Early target | [HF ibm-granite/granite-4.2-8b](https://huggingface.co/ibm-granite/granite-4.2-8b/tree/a7042144125ce5ae64f89610e8289647fc000b9a); CoreWeave bf16 | Replaced by Qwen3-32B |
| qwen3.5-9b, mistral-nemo, llama-3.1-8b, Llama-3.3-70B | Smoke tests / screens | OpenRouter | nemo tool use unreliable |
| Gemma-4-31B, Qwen3.6/3.8-27B | E04 backup replay (not started) | Shi et al. release | |
| OpenRouter providers (DeepInfra, CoreWeave, SiliconFlow) | All E01 runs | OpenRouter | Provider pinned to full precision where possible |
| Modal | E02 GPU replay | [Modal](https://modal.com/pricing), SDK 1.6.2 | Each GPU run gets a cost cap in advance |
| Luna Decisions judge (gpt-6-luna-decisions) | Secondary labels (deliberate vs incidental) | OpenRouter; `judge_labels.py`, run 20261024-1710-e01-label-judge | 15/16 agreement with hand labels; small set |
| Jev 1.14 (typesafe/jev-1.14) | Judge alternative | OpenRouter | Compared with Luna on a small sparse set |
| GPT-5 Nano | Judge fallback | OpenAI | Not live-validated |
| HF transformers / torch stack | E02 replay | Versions pinned in `requirements-lock.txt` | |
| Shi et al. traces | E04 backup route | [HF SALT-NLP/agent-collusion](https://huggingface.co/datasets/SALT-NLP/agent-collusion), MIT; [code](https://github.com/SALT-NLP/agent-collusion) | Mutual collusion, not recruitment |
| NARCBench data and activations | Possible pipeline check | [HF aaronrose227/narcbench](https://huggingface.co/datasets/aaronrose227/narcbench); [code](https://github.com/aaronrose227/narcbench), MIT | Instructed collusion only |
| PMIYC, SYCON-Bench, SaTML'24 CTF | Candidate secondary data | [PMIYC](https://github.com/beyzabozdag/PersuadeMeIfYouCan); [SYCON](https://github.com/JiseungHong/SYCON-Bench); [CTF](https://huggingface.co/datasets/ethz-spylab/ctf-satml24) | Not used yet |
| Sprint starter repo | Colosseum tactic prompts; reading list | [github.com/poseidon-research/collusion_hackathon](https://github.com/poseidon-research/collusion_hackathon) | |
| Colosseum code | Tactic source | [github.com/umass-ai-safety/colosseum](https://github.com/umass-ai-safety/colosseum) | No licence file |

## 6. Related work we position against

Sources: `docs/related_work.md`, `docs/probe_takeaways.md`, `docs/external_traces.md`. Numbers marked *(summary)* there still need checking against the PDFs.

| Item | Where we use it | Source | Our changes or notes |
|---|---|---|---|
| NARCBench / HELIOS (Rose et al.) | Closest collusion-probe paper | arXiv 2604.01151 | They read instructed colluders; we read the recruited target, per turn |
| Das et al., "You Can't Escape Your Own Activations" | AUROC vs fixed-threshold recall | arXiv 2609.03035 | |
| Kortukov et al. 2026, "Predicting Future Behaviors in Reasoning Models Enables Better Steering" | Closest methodological precedent: prediction probes (64–91%) vs detection features, single-turn reasoning models; positioning line in `docs/probe_takeaways.md` | arXiv 2606.11172 (full text read; venue not stated on arXiv); code github.com/kortukov/future_probes | We extend to multi-turn, multi-agent, tool use, monitor comparison; borrow the detection-vs-prediction control |
| Apollo deception probes | Probe baseline; scenario-raises-scores caution | arXiv 2502.03407 | |
| Colosseum (Nakamura et al.) | Say-vs-do motivation; tactic source | arXiv 2602.15198 | Checked 2026-10-25 (`docs/rq22_papers_check.md`): judge-score vs coalition-advantage r = −0.243 / −0.143, n = 19, not significant per their own footnote |
| When Agents Lie (Shi, Zhang, Schölkopf, Conitzer, Jin; "Shi et al. 2026a") | RQ 2.2: private plans vs public announcements; analogue of our L3 unposted text | arXiv 2607.05132 | Checked 2026-10-25. >90% premeditation only in the highest-deception conditions; 0–98.6% across games. Not the same paper as Shi 2026b |
| The Best-Laid SCHEMEs (Radev, Haas, Arnav, Bernabeu-Pérez) | RQ 2.2: joint code + messages monitor; matches our L1 → L2 gain | arXiv 2605.29178 | Checked 2026-10-25. Codex TPR@2% FPR: code only 68% → code + messages 81%; per-agent 61%. Monitors the saboteurs, not a recruited target |
| TraceGuard (Nguyen, Nghiem, Tran) | RQ 2.2: multi-dimension monitor rubric (action-trace consistency) | arXiv 2604.03968 | Checked 2026-10-25. Sprint page's "0% → >70%" is misquoted: paper has 0% → 95% safety for an *untrusted* monitor, n = 20; 70.8% is another monitor. Hackathon preprint |
| Arike et al., information access and sabotage monitors | RQ 2.2: "less-is-more effect"; explains L3 not beating L2; EaE monitor idea | arXiv 2601.21112 | Checked 2026-10-25. Filtering helps in 7/8 monitor-environment pairs; EaE +16.8 pp |
| Shi et al. 2026b | L1/L5 evidence; backup data | arXiv 2609.24967 | |
| Dong et al. (IPI exposure) | Closest paper overall | arXiv 2608.02657; [code](https://github.com/jianshuod/IPI-exposure-signal) | Their effect probe is weaker than exposure |
| LAD | Attempt detection; drift baseline | arXiv 2604.28129 | |
| NeuroFilter | Attempt-vs-effect citation | arXiv 2601.14660 | |
| Credential exfiltration probes | Cite and distinguish | arXiv 2606.04141 | Excludes keys in tool calls |
| Agent MechSuits | Actor-side per-step probe | arXiv 2606.22673 | One-step lookahead only |
| Zhao et al. (harm vs refusal) | Recognition vs compliance precedent | arXiv 2507.11878 | |
| Voluntary Collusion (Zeng & Rudzicz) | Behavioural analogue | arXiv 2605.27593 | |
| GroupGuard | Persuasion between agents | arXiv 2603.13940 | |
| Many-to-One | Many-peers precedent | arXiv 2512.03097 | |
| SPINE | Sustained pressure; rubric | arXiv 2609.09090 | |
| Capitulation-null paper | Validation caution | arXiv 2609.17550 | |
| Blind Deference | Pressure vs outcome probes on Qwen3-8B | [repo](https://github.com/sujitnoronha/llm_sycophancy_probing) | No paper linked |
| Kramár et al. (Gemini probes) | Multi-turn favours judges | arXiv 2601.11516 | |
| Kirch et al. (on-policy data) | Keep replays on-policy | arXiv 2511.17408 | |
| Paglieri et al. | Exploit spread | arXiv 2609.04170 | |
| Agrawal et al. | Urgency, oversight | arXiv 2507.01413 | |
| Persuasion-probe paper | History vs current-turn control | arXiv 2508.05625 | |
| Goldowsky-Dill / Among Us / Fan et al. | Other pointers | arXiv 2502.03407; 2504.04072; 2609.16436 | Minor |
| Before the Model Caves (pre-capitulation states, multi-turn sycophancy) | Closest in shape; reason to add an MLP probe (`docs/prior_work_check.md` §1) | [GitHub soham-padia/pre-sycophancy-study](https://github.com/soham-padia/pre-sycophancy-study) (README only; "submitted to EMNLP 2026", no authors or paper) | Checked 2026-10-24. They: a user disputing facts, no peer, rule or tool action. Peak AUC 0.596–0.636 on 4 probed models (5th is behaviour only) |
| Readable Before Actionable (Yu, Xing, Yang, Han) | Hijacked-vs-resisted directions and steering are done for injection | arXiv 2610.05295 | Checked. They: one injected tool result on AgentDojo; we: multi-turn peer persuasion against an operator rule |
| From Probe Scores to Alarm Policies (Gao, DAI 2026) | Per-episode false-alarm rate; threshold on "any alarm in episode" | arXiv 2610.04575 | Checked. AUROC 0.922 is their *secondary* mean-activation monitor (0/38 at 5%). The 40.1% is their generic Proposition 1 (p=.05, n=10, independence); their AgentDojo unit is 10 attempts, not 10 steps |
| Internal-State Probes Read the Situation, Not the Action (Fomin, David, LeVi; ICML 2026 AIWILD workshop) | The critique we must answer: probes read the situation | arXiv 2606.30449 | Checked (AUC 0.801, +5.1 pp; shared-prefix pair). Our answer: gave-in vs held under the same situation and pressure |
| Doomed from the Start (Ruan et al.) | Precedent for per-round AUROC among episodes still running | arXiv 2607.06503 (Fig. 3, v2) | Checked. They predict task failure with a post-generation probe; we predict giving in, before the action |
| Apart sprint project: detecting an agent's intent to escape (Han & Yong Deng, Sep 2026) | Example of the task-difficulty confound | [Apart project page](https://apartresearch.com/sprints/projects/can-we-detect-an-agents-intent-to-escape-before-it-actually-does-so-hg7h) | Checked; sprint project, not peer-reviewed. Their positives are all impossible tasks; ours share task and pressure with the negatives |
| Simple probes can catch sleeper agents (MacDiarmid et al., Anthropic, Apr 2024) | Background: predicting future behaviour from prompt activations | [Anthropic alignment note](https://www.anthropic.com/research/probes-catch-sleeper-agents) | Checked. Trained-in backdoor; ours is an untrained model being persuaded |
| Language Models Can Predict Their Own Behavior (Ashok & May, NeurIPS 2025) | Background: probe early warning, 91% less jailbreaking | arXiv 2502.13329 | Checked (abstract). Single-turn; no peer agent |
| Kirch et al., What Features in Prompts Jailbreak LLMs? | Background: jailbreak success from last prompt token | arXiv 2411.03343 | Checked. >80% for 3 of 5 models (Llama-3.1-8B, Llama-3.2-3B, Ministral-8B); the other 2 ≥70%. Single-turn jailbreaks |
| Reading the Plan: Multi-Horizon Future-Action Prediction (Advani, Maharjan, Chaturvedi) | Background: future tool calls decodable from one frozen state | [alphaXiv slug](https://www.alphaxiv.org/abs/2610.frozen-states-future-action-prediction) (resolves; no arXiv id found) | Checked (abstract). Predicts which tool comes next; we predict a rule-breaking give-in under persuasion |
| SafeDream (Yan, Lin, Zhu, Wang) | Lead-time ("detection lead") precedent | arXiv 2604.16824 | Checked. **It does read hidden states** (a world model over LLM hidden states); "external" only means no weight changes. Single-model jailbreaks |
| Persuade Me if You Can (Bozdag et al., ACM CAIS 2026) | Agent-to-agent persuasion, behaviour only | arXiv 2503.01829 | Abstract checked; how susceptibility is scored not confirmed. Text only; no rule or tools |
| MMPersuade: Seeing is Believing? (Qiu et al.) | Agent-to-agent persuasion of VLMs | arXiv 2510.22768 | Checked (abstract). Behaviour via function calls; no activations |

## 7. Ideas credited to the author

Sources: `EXPERIMENT_LOG.md` [idea]/[decision] entries, `docs/overview.html` Decisions and Idea tabs, `docs/scenario_guidelines.md` §7.

| Item | Where we use it | Source | Our changes or notes |
|---|---|---|---|
| Spread variant (target later recruits a third agent) | Planned multi-agent variant | Author (log 01:59); related paper co-authored by the author: arXiv 2609.35576 (Share-Borne AI Virus) | Cite in related work and write-up |
| Policy × related/unrelated grid | E01 design | Author (log 21:46) | |
| Graded relatedness; neutral vs authority peer framing | Later factors | Author (log 22:04) | |
| Policy condition is the main experiment; mundane ask | E01 | Author (log 23:46) | |
| Backup route on constructed pairs | Probe route | Author (log 23:54, 02:45) | |
| Action asks; rogue-fleet "unrelated" | Later scenarios | Author (log 00:30) | |
| Shortcut checks and transfer order | Evaluation | Author (log 00:43) | |
| Own stake (L1) | Scenarios | Author (log 01:11) | |
| Early stopping | Harness | Author (log 01:39) | Approved 02:54 |
| Per-turn LLM judge | Labels / text monitor | Author (log 01:44) | |
| Monitor ladder | Monitor comparison | Author (log 01:47) | |
| Many peers, watching third agent, full team | Variants | Author (log 01:59) | |
| Required/optional access | Scenarios | Author (log 02:08, 02:09) | |
| Gradual wearing down as the target behaviour | Scenarios, tactics | Author (log 03:23) | |
| Work backwards from evaluation | `docs/evaluation_design.md` | Author (log 03:26) | |
| "Minority Report / PreCrime for agents" title | Title idea | Author (log 03:28) | Decide after results |
| Colosseum tactics as peer strategies | Section 3 | Author (log 23:13, 16:10) | |
| Reuse published traces | `docs/external_traces.md` | Author (log 16:10) | |
| Shi et al. replay as backup (E04) | Backup route | Author (log 17:56) | |
| Environment realism v2 | Later | Author (log 17:50) | |
| Per-step probe unit | E02 | Author (log 18:05) | |
| Don't-verbalise experiment | Later | Author (log 18:15) | |
| Ladder of evidence | Reporting | Author (log 19:00) | |
| Activations literature survey | Section 4 | Author, `docs/llm_activations_lit.md` | |
| Fork-point correction (identical prefixes) | Design | LLM assistant, `docs/related_work.md` | |

## 8. Unverified or to-check

Copied from the source docs' own caveats, plus items with no link or id.

| Item | Where we use it | Source | Our changes or notes |
|---|---|---|---|
| Zeng et al. 2024 and Meincke et al. 2025 section/page numbers and effect sizes | Section 3 | `PEER_TACTICS_PROVENANCE.md` | "Unverified in this session"; no links |
| Persuasion classics (Cialdini, Milgram, Asch, Gouldner, Tversky & Kahneman) | Section 3 | `PEER_TACTICS_PROVENANCE.md` | No links |
| Kramár appendix numbers; 3% vs 8% deferral discrepancy | Section 4.3 | `docs/probe_takeaways.md` | Not verified |
| Layer used in Anthropic cheap-monitors post | Section 4 | `docs/probe_takeaways.md` | Not verified |
| Kirch probe-steering claim | Section 4.4 | `docs/probe_takeaways.md` | No such paper found; refers to Kortukov et al. 2606.11172 |
| `aclanthology …/unverified` (Kirch, Skapars) and catalyzex (Kumar et al.) links | `llm_activations_lit.md` | `docs/probe_takeaways.md` | Author/search pages, not papers |
| "Caught in the Act" naming | Section 4 | 2508.19505 (lit doc), 2610.12445 (`plan.md`), 2606.04141 "Caught in the Act(ivation)" | Three different papers; check which one each claim cites |
| Levers L8, L13, A2, A4 (Q. Liu, Aharon, Keppo) | Section 2 | `docs/scenario_levers.md` | [unchecked] |
| Wiki incident (Von Arx et al. 2026) | Section 1 | `docs/scenario_levers.md` | [checked, from reading list]; no link |
| Swarmcha.se "Chinese agent fleet" report | Section 1 | EXPERIMENT_LOG 00:30 | No link |
| `*(summary)*` numbers in related work (NARCBench, Dong, LAD, NeuroFilter, Voluntary Collusion) | Section 6 | `docs/related_work.md` | Re-check against PDFs |
| NeuroFilter code link `github.com/NeuroFilterPrivacy/NeuroFilter` | Section 6 | `docs/related_work.md` | Came from a summary |
| Dong et al. code repo populated? Qwen3-8B AUROC 0.976 | Section 6 | `docs/related_work.md` | Check PDF and repo |
| SPINE code | Section 6 | `docs/related_work.md` | Not retrievable; "upon publication" |
| Blind Deference steering claims | Section 6 | `docs/related_work.md` | Artifacts need reconciliation |
| Gemma-4-31B / DeepSeek-V4-Flash open-weight status in Shi data | Section 5 | `docs/external_traces.md` | Inferred (I) |
| arXiv 2609.35576 (Share-Borne AI Virus) | Section 7 | EXPERIMENT_LOG 01:59 | Id only; title from the author |
| Judge validation (Luna 15/16; Jev comparison) | Section 5 | `JUDGE_LABELS.md` | Small, sparse set |
| "Self-reported agreement" in Persuade Me if You Can | Section 6 | `docs/prior_work_check.md` | Not in abstract; check full paper |
| Reading the Plan arXiv id | Section 6 | `docs/prior_work_check.md` | alphaXiv-only slug; no arXiv id found |
| Before the Model Caves authors and paper | Section 6 | `docs/prior_work_check.md` | README names none; cite as GitHub repo |
