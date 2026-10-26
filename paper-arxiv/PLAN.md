# Plan for the arXiv rewrite

Status: Phase 1 draft by claude-2 (lead writer). The claims list is in `docs/claims.md` and is **proposed**. The dataset plan (§3) is waiting on codex-2's input and will be updated when it lands. claude-4 reviews this file against `WRITING.md` before drafting starts.

## 1. Working title

**Recruited: An Agent's Activations Show Which Call Will Leak a Secret to a Recruiting Peer.** Alternatives go in HANDOVER.md:
- "Recruited: Predicting When an Agent Gives In to a Peer, from Its Activations"
- "Recruited: The Call That Leaks Is Readable Before It Acts"

## 2. What changes from the sprint version, in one list

- **Label.** Every per-call and ladder result uses one leak label on both models: any public emission. The Qwen per-call results are recomputed under it. The round-level Qwen confirmation keeps its pre-registered label, which is defined once in Setup.
- **Datasets.** Two names per model, used everywhere: development episodes and fresh test episodes (§3). The sprint's "first data batch", "new-episode set", "round-level cohort", "per-call cohort", "matched cohort" and "channel window" all disappear from the main text.
- **One evaluation per question.** Held-out scenarios on development episodes, plus the frozen fresh-test score where one exists. Pooled CV, fold-stratified scoring, hindsight labels B and C, fixed-layer checks and scenario-mean weighting move to one appendix robustness section.
- **Evidence status by structure** (author feedback, 26 Oct): Results headings state findings, with no status words. 4.1 "Confirmed on fresh episodes" holds the two pre-registered results. One sentence then opens the rest of Results. Figures: filled = fresh test episodes, hollow = development episodes, explained once in Method. "Exploratory" and "post hoc" never appear in a Results sentence. Held-out-scenario evaluation is presented as the main evidence standard. The Qwen per-call probe scored on its fresh test episodes is reported as out-of-sample evidence.
- **Numbers.** At most three in the abstract, at most one per claim in prose. Every number goes through `numbers.tex`. No counts in prose: one dataset table holds them.
- **Cut from the main text:** the incident narrative beyond two sentences, the contributions list's per-model numbers, the round-level monitor-design result (sprint §4.5) and the combination test (both move to the appendix), Gemma, the channel-window check, alarm-rate detail, leak-route counts and the scoring-window breakdown.
- **Cut from the appendix:** the sprint's §J follow-up design (reduced to two sentences in Discussion plus the slots in §8), the long related-work appendix (folded into a one-page main section), duplicated caveats in L.1–L.5, Table G.1's 21-row screen, which becomes a six-row summary with the CSV pointer, and every inline run path, which moves to the reproducibility index.

## 3. Dataset plan (decision: proposal A, agreed with codex-2; counts pending)

### 3.1 Named datasets (main text uses only these)

| Name | gpt-oss-20b | Qwen3-32B |
|---|---|---|
| **development episodes** | all 300 recruiting + 60 control episodes of the main collection (238 recruiting episodes have a scorable call) | proposal A: the episodes collected before the confirmation plan was frozen (the sprint's first batch). Fallback B: all 241 scored episodes |
| **fresh test episodes** | 84 episodes collected after the reasoning-probe plan was frozen | 89 episodes collected after the near-term plan was frozen |

**Decision: proposal A** (codex-2 agrees): Qwen development episodes are the replay-2 episodes and the fresh test episodes are the replay-3 episodes; gpt-oss development episodes are the 360-episode main collection and the fresh test episodes are the 84 new ones. Any new per-call test on a fresh set that was already inspected is labelled exploratory and out of sample, never a new confirmation. Proposal A makes every Qwen number belong to exactly one dataset, with no overlap. Its cost is fewer development positives. It also allows a frozen development-only per-call probe to be scored once on the fresh test episodes. That check is out of sample but not pre-registered, so it gets a hollow marker. Fallback B keeps the sprint's power, but then the fresh test episodes are also inside the development set, and that overlap has to be stated once in Setup. codex-2 is checking feasibility, and the decision is recorded here when their numbers land.

### 3.2 One evaluation per question

| Question | Reported evaluation | Goes to the appendix robustness section |
|---|---|---|
| Which call will leak? | Held-out scenarios on development episodes, plus the frozen gpt-oss reasoning probe on fresh test episodes | pooled CV, mean vs max aggregate, censored-at-mention variant, any-public vs channel-only label |
| How does predictability change with distance from the act? | Held-out scenarios on development episodes, all three labels on the same calls | per-layer curves, MLP, fixed layer |
| Confirmed round-level result | Frozen probe and Jev forecaster on Qwen fresh test episodes, as pre-registered | none (reported as it was) |
| Probe vs text monitor | Same calls as the per-call question; probe minus monitor, paired bootstrap | monitor reading reasoning, reversed-score diagnostic, other monitors |
| Shortcuts (pressure, string, read step) | Same calls as the per-call question | onset audit, incoming-only probe, action-time stream |

### 3.3 Mismatches to remove by recomputing (new run folders; nothing overwritten)

1. Qwen per-call last-prompt probe refit on any public emission (author decision 2). Replaces sprint 0.95 (give-in rule).
2. Qwen matched ladder (ever / this or next round / this call) on any public emission, on the same calls as item 1. Replaces sprint 0.54 / 0.67 / 0.95.
3. Qwen Jev per-call monitor and read-step flag, rescored on item 1's calls and label, from saved monitor scores. No new API calls unless a call is missing.
4. If proposal A: Qwen round-level eventual and near-term dev numbers recomputed on development episodes only, and the frozen dev-only per-call probe scored once on the Qwen fresh test episodes.
5. gpt-oss: the dev-trained per-call last-prompt probe scored once on the fresh test episodes, if their last-prompt activations were saved. Otherwise drop the item.

Every recomputed number, and what it replaced, goes in the analysis-history appendix. GPU spend only if activations must be re-extracted (cap USD 10, held by codex-2).

### 3.4 Dataset table (Setup, Table 1)

One small table: per model and dataset, the episodes, the scored calls, the calls that leak, and the share of recruiting episodes that leak. This is the only place counts appear.

## 4. Notation (Setup §2.3, in `math_commands.tex`)

Formally defined:
- episode, target calls $c_1,\dots,c_T$, round $r(t)$ of call $t$;
- $\tau$, the index of the first call that leaks, with $\tau=\infty$ if none does;
- three labels on calls $t \le \tau$ made after the target has read the secret: $y^{\text{call}}_t=\mathbb{1}[t=\tau]$, $y^{\text{near}}_t=\mathbb{1}[r(\tau)\in\{r(t),r(t)+1\}]$, $y^{\text{ever}}_t=\mathbb{1}[\tau<\infty]$;
- probe score $s_t = w^\top h_\ell(c_t)+b$, with $h_\ell(c_t)$ the residual stream at layer $\ell$ at the last prompt token. The reasoning probe is $\max_k$ over reasoning tokens;
- the metric: within-stratum AUROC, averaged over scenario × round strata, weighted by positives (one displayed equation).

Kept in words: the scenarios, the operator rule, families of related episodes, bootstrap details, the text-monitor prompt.

Defined terms in the main text (six; listed in `docs/glossary.md`): **target**, **peer**, **leak**, **probe**, **text monitor**, and the dataset pair **development / fresh test episodes**. "Call" and "round" are defined by notation. "Give-in", "recruiter", "principal", "cohort", "rung" and "eligible" are not used.

## 5. Outline as paragraph-opening sentences

Numbers are written as macro names. They are placeholders until the registry lands. Revised after blind outline review 1 (`reviews/outline_blind_review_1.md`).

### Abstract (≤200 words, at most three numbers; two planned)
1. AI agents increasingly work alongside other agents, and one agent can talk another into breaking its operator's rule.
2. We study the first step of such collusion: a peer agent presses a target agent for a secret that the target's operator told it to protect, in six scenarios on two open-weight models.
3. We train linear probes on the target's activations and compare them with text monitors, which read only the transcript, on the same model calls.
4. Whether an episode will ever leak is barely predictable, but whether this call will leak is highly predictable from a probe that reads the activations before the call writes anything.
5. On gpt-oss-20b, a reasoning probe frozen before any new data was collected ranked the leaking calls above the others on fresh episodes (AUROC `\gptossFreshReasoning`). On development episodes a simpler probe does the same on both models (AUROC `\qwenCallProbe` on Qwen3-32B).
6. A text monitor shown the same conversation does worse, so an overseer could pause the call that is about to leak.
7. Nothing we measured warns rounds ahead, and we test only exact-string secrets in synthetic scenarios.

### 1. Introduction
1. When agents work together, one agent can ask another to do something that the second agent's operator forbids, and the second agent sometimes does it.
2. We study this first step, one agent recruiting another, in its simplest checkable form: a peer asks a target for a secret, and the target's operator has told it never to share it.
3. The question is whether an overseer can tell, before the target acts, which episode will leak and when.
4. We ask at three distances from the act: will this episode ever leak, will it leak this round or the next, and will this call leak?
5. The answer depends on the distance (Figure 1): the eventual outcome is barely predictable, this round or the next modestly, and this call highly, on both models.
6. The strongest result is confirmed: on gpt-oss-20b, a probe on the call's reasoning, frozen with its alarm threshold before new episodes were collected, ranked the leaking calls above the others on those fresh episodes.
7. On development episodes, a simpler probe that reads one position before the call starts does the same on both models, and it is not simply detecting the request, the secret string or the file read.
8. A text monitor shown the same conversation scores well below the probe, and on gpt-oss-20b it flags almost every call made under pressure.
9. Contributions: (i) a recruitment benchmark with mixed outcomes and matched controls, (ii) probes and text monitors scored on the same calls at three distances from the act, (iii) a per-call warning confirmed on fresh episodes, with controls for the obvious shortcuts.

*Figure 1 (headline, page 1–2): "The nearer the act, the more predictable the leak." One grid gives every main-text number a home: one panel per model; x = distance from the act (ever / this or next round / this call); probe and text monitor in fixed colours; hollow markers for development episodes, filled for fresh test episodes.*

### 2. Setup
1. A target agent does an ordinary task in a mocked workspace under one rule from its operator: do not share a protected value outside the file that holds it.
2. A peer agent shares the team channel, needs the value, cannot read the file, and is not told the rule.
3. A call leaks if it is the first to write the secret out, in its reply or in a tool call such as a file write.
4. Every scenario also runs with a control peer that never asks for the value and with the target alone, and these episodes never leak.
5. We use two target models, Qwen3-32B and gpt-oss-20b, each facing its own peer, and we never pool their results.
6. Each model has two sets of episodes. We develop and evaluate every method on the *development episodes*. The *fresh test episodes* were collected later, after we had written down and committed a plan that fixes the model, its threshold and the success criterion, and each frozen model is scored on them once (Table 1).
7. Problem setup: an episode is a sequence of target calls; $\tau$ is the first call that leaks; the three labels are $y^{\text{ever}}_t$ (this episode leaks at some point), $y^{\text{near}}_t$ (it leaks in this round or the next) and $y^{\text{call}}_t$ (this call is the one that leaks); the probe score is a linear function of one layer's activation.
8. One episode shows how this plays out (Figure 2): the target refuses for four rounds, citing the rule, then posts the token when the peer recasts the request as a routine handoff.

### 3. Method
1. A probe is a logistic regression on the target's internal activations (the residual stream), read at the last prompt token before each call, so it runs before the call writes anything.
2. On gpt-oss-20b, which reasons before it answers, a second probe reads every reasoning token and takes the maximum score, still before any public output.
3. A text monitor is a language model that reads the transcript, with no access to activations. Our main monitor is Jev, a commercial decision model that returns a probability for a yes-or-no question instead of writing text. We ask it whether this call will leak.
4. Probes and monitors are scored on exactly the same calls. Because leaks come early, we compare calls only within the same scenario and round, so "early rounds are risky" scores exactly chance.
5. We evaluate on held-out scenarios: train on five scenarios, test on the sixth, and rotate. Related episodes, such as reruns that share a history, are always held out together.
6. Two results were tested under plans written down before the fresh test episodes were collected; all other analyses are evaluated on held-out scenarios, and on the fresh test episodes where possible. In every figure, filled markers are fresh test episodes and hollow markers are development episodes.

### 4. Results
**4.1 Confirmed on fresh episodes**
1. On gpt-oss-20b, the reasoning probe, frozen with its threshold before the fresh test episodes were collected, ranked the calls that leak above the others on those episodes (`\gptossFreshReasoning`), meeting its pre-stated criterion.
2. On Qwen3-32B, whether the target leaks this round or the next was modestly predictable on its fresh test episodes, for the probe (`\qwenFreshNearProbe`) and the best text monitor alike, as the frozen plan required.

*One sentence opens the rest of the Results: "The analyses below were designed after earlier results; we evaluate them on held-out scenarios and, where possible, on the fresh test episodes."*

**4.2 The probe picks out the call that leaks**
1. On held-out scenarios, the last-prompt probe picks out the call that leaks on both models (`\qwenCallProbe` on Qwen3-32B; Figure 3).
2. The Qwen3-32B probe, fit only on development episodes, holds on the fresh test episodes, which were never used to fit or choose anything for it (`\qwenFreshCallProbe`).
3. Reading the reasoning adds little on gpt-oss-20b, so most of the signal is already present before the model reasons.
4. The signal is specific to the call that leaks: one call earlier, it is much weaker.

**4.3 The nearer the act, the more predictable**
1. On the same calls, the probe goes from near chance for the eventual outcome, to modest for this round or the next, to high for this call (Figure 1).
2. gpt-oss-20b follows the same pattern, but is near chance at the round level because it usually leaks within a round of the request.

**4.4 The probe beats a text monitor on the same calls**
1. A text monitor shown the same conversation and tool results scores well below the probe on both models (Figure 3).
2. On gpt-oss-20b the monitor flags almost every call made under pressure, so it ranks the calls that leak no higher than the others.

**4.5 What the probe is not reading**
1. Every call that does not leak was also made under pressure, after the request, in the same scenario and round, so detecting the request cannot explain the score.
2. The probe beats keyword rules on the reasoning and a flag for "the protected file was just read" (Figure 4).
3. What the probe does read is open: a probe on only the incoming peer message and tool results also scores high.

### 5. Related work (contrasts, ≤1 page)
1. Probes can detect that a tool-using agent was exposed to an attack, but every call we score has already been exposed to the same pressure.
2. Prior early-warning work reads hidden states before an unwanted action, with weak or mixed results against text monitors; we find a strong per-call signal and a weak round-level one in a peer-recruitment setting.
3. Text monitors catch more coordinated misbehaviour when they see agents' messages, and we compare them with probes on the same calls.
4. Persuasion between agents has been measured from text and outcomes; we add the persuaded agent's activations.

### 6. Discussion and limitations
1. An overseer cannot know early which episode will leak, but it can know which call is about to.
2. For an exact secret, an output filter would also stop the leak, so the per-call probe matters most where no filter can match: paraphrased or encoded leaks, and pausing a call before it acts.
3. Limitations, ordered by impact, one short paragraph each: narrow setting (two models, one task template, one peer, exact strings, so an output filter would catch these leaks); per-call results confirmed only for the gpt-oss reasoning probe, on few leaking calls; warning about the current call only; what the probe reads is open; at per-call thresholds, many refusing episodes get at least one false alarm; one text monitor, untuned; automated labels.
4. Future work in two sentences: causal tests of the probe direction, transfer to other environments, and larger multi-agent settings.

### LLM usage statement (unnumbered, after the conclusion)

## 6. Appendix, as questions with one-line answers

| § | Question | One-line answer |
|---|---|---|
| A | What does an episode look like, and which scenarios did we build? | Six scenarios from one task template; one leaking and one refusing transcript, excerpted. |
| B | How is a leak detected, and can the labels be trusted? | A rule on the tool log finds the first call that writes the secret out; the round-level label used in the Qwen3-32B confirmation is defined here; an automated judge's deliberate-or-accidental labels match the author's blind labels on 36 of 40. |
| C | How were the datasets built and checked? | Which episodes and calls are scored, the count table, and a check that re-running the saved prompts through the open weights reproduces the served replies closely. |
| D | How are probes trained and scored? | Logistic regression with the layer chosen inside each training split; the within-scenario-and-round AUROC with a worked example; bootstrap intervals that resample groups of related episodes. |
| E | What do the text monitors see, and how are they asked? | Three monitor models, two questions and three levels of access, with the full grid in one table. |
| F | What was frozen for the fresh test episodes, and what happened? | Both written plans and their success criteria; both criteria were met; alarm counts in one table. |
| G | Does the per-call result hold under other evaluations and settings? | Yes: cross-validation that mixes scenarios, averaging instead of taking the maximum over reasoning tokens, a channel-only leak label, and fixed layers all give similar rankings. |
| H | Is the probe reading pressure, the secret string or the read step? | No to all three; a probe on the incoming message alone also scores high, so much of the signal arrives with the input. |
| I | Does the probe warn before the call that leaks? | Weakly: one call ahead it mostly detects the protected-file read, and first alarms come at the start of the leaking call. |
| J | How many false alarms would a deployed probe raise? | Many per episode at per-call thresholds; a threshold set per episode catches about a third of leaking episodes. |
| K | What should a round-level text monitor ask and see? | Asking for a forecast and showing the peer's messages helps the strongest monitor; adding the probe helps only a weaker one. |
| L | Why is round-level prediction near chance on gpt-oss-20b? | It usually leaks within a round of the request, so there is little to predict from. |
| M | How does behaviour vary with pressure and model? | Six-row screen summary; the second target's peer strategy; why Gemma stayed behaviour-only. |
| N | Dual use and ethics | What we release, the risks, and why the uplift is low. |
| O | Analysis history | One table: each analysis, when it was decided, what it replaced, whether it was confirmed. |
| P | Reproducibility index | Each figure, table and headline number mapped to its run folder and script. |
| Q | Prompts | Exact target, peer and monitor prompts for the main scenario. |

## 7. Figure plan (one colour-blind palette: Qwen and gpt-oss each keep one colour; probe, monitor and baseline each keep one marker family)

| Fig | Answers | Content | New or adapted |
|---|---|---|---|
| 1 (headline, p.1–2) | "The nearer the act, the more predictable the leak" | One grid that gives every main-text number a home (blind review 1). One panel per model; x = ever / this or next round / this call; probe and Jev in fixed colours; hollow = development episodes (held-out scenarios, same calls for every distance), filled = fresh test episodes (frozen confirmations, plus the Qwen per-call out-of-sample score). Jev at the round-level distances only where its scores exist on the same calls (codex-2 to check). | New (replaces sprint Fig. 2b and Fig. 3) |
| 2 | "How an episode works" | Setup schematic (target, peer, operator rule, probe read points) plus the episode-0032 excerpt | Adapted from sprint Fig. 1, with the L1–L3 codes removed |
| 3 | "A probe picks out the call that leaks; a text monitor does not" | Per-call AUROC per model: last-prompt probe, reasoning probe (gpt-oss), Jev on the same input, with intervals | Adapted from sprint Fig. 2a |
| 4 | "The probe is not reading the obvious shortcuts" | Pre-ask placebo, keyword rules, read-step flag, incoming-only probe, against the probe, on the same calls | Adapted from sprint Fig. L.1 |
| Appendix | one per question where needed | Alarm trade-off (J), monitor design (K), per-layer curves (G), pipeline (C) | Adapted |

## 8. Slots for the follow-up experiments (no placeholder text in the draft)

- **4.6 "Does it generalise?"** (transfer to the Shi et al. environment). It goes after 4.5 and gets one figure (Fig. 5) and one appendix question ("Does the probe work in another environment?"). Its status is confirmed or exploratory, according to how it is run.
- **4.7 "Is the direction causal?"** (steering on gpt-oss-20b). It follows 4.6 and gets one figure (Fig. 6) and one appendix question. It adds one claim (C5) to `docs/claims.md`.
- **Discussion.** Limitation 4 ("what the probe reads") shrinks or is removed depending on the steering result, and the future-work sentence loses the items that have been done.

## 9. File ownership (one writer per file at a time)

| Files | Owner |
|---|---|
| `paper-arxiv/PLAN.md`, `docs/claims.md`, `docs/glossary.md`, `paper-arxiv/title.tex`, `sections/*.tex` | claude-2 (writer) |
| `appendix/*.tex` | claude-2, or one helper writer per file, assigned by claude |
| editing passes on any prose file | claude-4 (editor), after the writer hands the file over on the board |
| `numbers.yaml`, the generator, `numbers.tex`, new `runs/` folders | codex-2 |
| `main.tex`, `latexmkrc`, build and package scripts, `references.bib`, `figures/src/` | codex |
| `math_commands.tex` | codex sets up the template copy; claude-2 adds the notation block, then owns it |
| `HANDOVER.md` | claude (coordinator); writers post entries to claude |
| viewer checks | codex-daybreak |
