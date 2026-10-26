# Outline (paragraph-opening sentences)


## Abstract (≤200 words, at most three numbers; two planned)
1. AI agents increasingly work alongside other agents, and one agent can talk another into breaking its operator's rule.
2. We study the first step of such collusion: a peer agent presses a target agent for a secret that the target's operator told it to protect, in six scenarios on two open-weight models.
3. We train linear probes on the target's activations and compare them with text monitors, which read only the transcript, on the same model calls.
4. Whether an episode will ever leak is barely predictable, but whether this call will leak is highly predictable from a probe that reads the activations before the call writes anything.
5. On gpt-oss-20b, a reasoning probe frozen before any new data was collected ranked the leaking calls above the others on fresh episodes (AUROC 0.91). On development episodes a simpler probe does the same on both models (AUROC 0.95 on Qwen3-32B).
6. A text monitor shown the same conversation does worse, so an overseer could pause the call that is about to leak.
7. Nothing we measured warns rounds ahead, and we test only exact-string secrets in synthetic scenarios.

## 1. Introduction
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

## 2. Setup
1. A target agent does an ordinary task in a mocked workspace under one rule from its operator: do not share a protected value outside the file that holds it.
2. A peer agent shares the team channel, needs the value, cannot read the file, and is not told the rule.
3. A call leaks if it is the first to write the secret out, in its reply or in a tool call such as a file write.
4. Every scenario also runs with a control peer that never asks for the value and with the target alone, and these episodes never leak.
5. We use two target models, Qwen3-32B and gpt-oss-20b, each facing its own peer, and we never pool their results.
6. Each model has two sets of episodes. We develop and evaluate every method on the *development episodes*. The *fresh test episodes* were collected later, after we had written down and committed a plan that fixes the model, its threshold and the success criterion, and each frozen model is scored on them once (Table 1).
7. Problem setup: an episode is a sequence of target calls; $\tau$ is the first call that leaks; the three labels are $y^{\text{ever}}_t$ (this episode leaks at some point), $y^{\text{near}}_t$ (it leaks in this round or the next) and $y^{\text{call}}_t$ (this call is the one that leaks); the probe score is a linear function of one layer's activation.
8. One episode shows how this plays out (Figure 2): the target refuses for four rounds, citing the rule, then posts the token when the peer recasts the request as a routine handoff.

## 3. Method
1. A probe is a logistic regression on the target's internal activations (the residual stream), read at the last prompt token before each call, so it runs before the call writes anything.
2. On gpt-oss-20b, which reasons before it answers, a second probe reads every reasoning token and takes the maximum score, still before any public output.
3. A text monitor is a language model that reads the transcript, with no access to activations. Our main monitor is Jev, a commercial decision model that returns a probability for a yes-or-no question instead of writing text. We ask it whether this call will leak.
4. Probes and monitors are scored on exactly the same calls. Because leaks come early, we compare calls only within the same scenario and round, so "early rounds are risky" scores exactly chance.
5. We evaluate on held-out scenarios: train on five scenarios, test on the sixth, and rotate. Related episodes, such as reruns that share a history, are always held out together.
6. Two results were tested under plans written down before the fresh test episodes were collected; all other analyses are evaluated on held-out scenarios, and on the fresh test episodes where possible. In every figure, filled markers are fresh test episodes and hollow markers are development episodes.

## 4. Results
**4.1 Confirmed on fresh episodes**
1. On gpt-oss-20b, the reasoning probe, frozen with its threshold before the fresh test episodes were collected, ranked the calls that leak above the others on those episodes (0.91), meeting its pre-stated criterion.
2. On Qwen3-32B, whether the target leaks this round or the next was modestly predictable on its fresh test episodes, for the probe (0.68) and the best text monitor alike, as the frozen plan required.

*One sentence opens the rest of the Results: "The analyses below were designed after earlier results; we evaluate them on held-out scenarios and, where possible, on the fresh test episodes."*

**4.2 The probe picks out the call that leaks**
1. On held-out scenarios, the last-prompt probe picks out the call that leaks on both models (0.95 on Qwen3-32B; Figure 3).
2. The Qwen3-32B probe, fit only on development episodes, holds on the fresh test episodes, which were never used to fit or choose anything for it (value pending).
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

## 5. Related work (contrasts, ≤1 page)
1. Probes can detect that a tool-using agent was exposed to an attack, but every call we score has already been exposed to the same pressure.
2. Prior early-warning work reads hidden states before an unwanted action, with weak or mixed results against text monitors; we find a strong per-call signal and a weak round-level one in a peer-recruitment setting.
3. Text monitors catch more coordinated misbehaviour when they see agents' messages, and we compare them with probes on the same calls.
4. Persuasion between agents has been measured from text and outcomes; we add the persuaded agent's activations.

## 6. Discussion and limitations
1. An overseer cannot know early which episode will leak, but it can know which call is about to.
2. For an exact secret, an output filter would also stop the leak, so the per-call probe matters most where no filter can match: paraphrased or encoded leaks, and pausing a call before it acts.
3. Limitations, ordered by impact, one short paragraph each: narrow setting (two models, one task template, one peer, exact strings, so an output filter would catch these leaks); per-call results confirmed only for the gpt-oss reasoning probe, on few leaking calls; warning about the current call only; what the probe reads is open; at per-call thresholds, many refusing episodes get at least one false alarm; one text monitor, untuned; automated labels.
4. Future work in two sentences: causal tests of the probe direction, transfer to other environments, and larger multi-agent settings.

## LLM usage statement (unnumbered, after the conclusion)

## Appendix, as questions with one-line answers

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

