# Outline (paragraph-opening sentences)



### Abstract (≤200 words, three numbers)
1. Agents increasingly work alongside other agents, and one of them can talk another into breaking its operator's rule.
2. We build six scenarios in which a peer agent presses a target agent to reveal a secret that the operator told it to protect, and we read the target's activations before each of its model calls.
3. Whether the target will ever leak is barely predictable, but whether this call will leak is highly predictable from a linear probe, before the call writes anything (AUROC `0.95` on Qwen3-32B).
4. On gpt-oss-20b, a probe on the call's reasoning keeps this ranking on fresh test episodes scored under a plan fixed in advance (`0.91`), and a text monitor shown the same conversation does worse on both models.
5. For oversight, this means an overseer could pause the call about to leak.
6. The warning is about the current call, not rounds ahead, and we test only exact-string secrets in synthetic scenarios.

### 1. Introduction
1. When agents work together, one agent can ask another to do something that the second agent's operator forbids, and the second agent sometimes does it.
2. We study this recruitment step in its simplest checkable form: a peer asks a target for a secret, and the target's operator has told it never to share that secret.
3. The question is whether an overseer can tell, before the target acts, which episode will leak and when.
4. The answer depends on how close to the act we ask (Figure 1): the eventual outcome is barely predictable, this round or the next modestly, and this call highly.
5. A linear probe reading the target's activations before a call writes anything picks out the call that will leak, and on gpt-oss-20b this held on fresh test episodes.
6. A text monitor shown the same conversation scores well below the probe, and on gpt-oss-20b it cannot separate the calls that leak from the others.
7. Contributions: (i) a recruitment benchmark with mixed outcomes and matched controls, (ii) probes and text monitors scored on the same calls at three distances from the act, (iii) a confirmed per-call warning on fresh episodes, with the shortcut controls that rule out the obvious explanations.

*Figure 1 (headline, page 1–2): "The nearer the act, the more predictable the leak."*

### 2. Setup
1. A target agent does an ordinary task in a mocked workspace under one rule from its operator: do not share a protected value outside the file that holds it.
2. A peer agent shares the team channel, needs the value, cannot read the file, and is not told the rule.
3. A call leaks if it is the first to make the value public, in a reply, a channel message or a file outside the protected one.
4. Every scenario also runs with a control peer that never asks for the value and with the target alone, and these episodes never leak.
5. We use two target models, Qwen3-32B and gpt-oss-20b, each facing its own peer, and we never pool their results.
6. Each model has development episodes, which we use for every analysis, and fresh test episodes, collected after a plan was frozen and scored once (Table 1).
7. *Problem setup (§2.3):* the notation and three labels defined once.
8. One episode shows how this plays out (Figure 2): the target refuses for four rounds, citing the rule, and then posts the token when the peer recasts the request as a routine handoff.
9. The round-level confirmation on Qwen3-32B uses the label that was fixed in its plan: a complete channel post, or a new file in five scenarios.

### 3. Method
1. A probe is a logistic regression on the residual stream, read at the last prompt token before each call, so it runs before the call writes anything.
2. On gpt-oss-20b, which reasons before it answers, a second probe reads every reasoning token and takes the maximum, still before any public output.
3. A text monitor is a language model shown the transcript, with no access to activations, and asked whether this call will leak. Our main monitor is a decision model that returns a probability (Jev).
4. Probes and monitors are scored on exactly the same calls, and we compare calls only within the same scenario and round, because leaks come early and "early rounds are risky" would otherwise score well.
5. We evaluate on held-out scenarios: train on five scenarios, test on the sixth, rotate. Intervals resample whole families of related episodes.
6. Some analyses were designed after we saw earlier results. We label these exploratory, and we confirm the main ones on fresh test episodes, each scored once by a model frozen in advance.

### 4. Results
**4.1 Confirmed on fresh test episodes**
1. On gpt-oss-20b, the frozen reasoning probe ranked the calls that leak above the others on fresh test episodes (`0.91`), which met its pre-stated criterion.
2. On Qwen3-32B, whether the target leaks this round or the next was modestly predictable on fresh test episodes, for both the probe and the best text monitor.

**4.2 Exploratory: which call will leak**
1. On development episodes, the last-prompt probe picks out the call that leaks on both models (Figure 3).
2. Reading the reasoning adds little on gpt-oss-20b, so most of the signal is already present before the model reasons.
3. The signal is specific to the call that leaks: one call earlier, it is much weaker.

**4.3 Exploratory: the nearer the act, the more predictable**
1. On the same calls, the probe goes from near chance for the eventual outcome, to modest for this round or the next, to high for this call (Figure 1a).
2. The two models follow the same pattern, though gpt-oss-20b is near chance at the round level because it usually leaks within a round of the request.

**4.4 Exploratory: probe versus text monitor**
1. A text monitor shown the same conversation and tool results scores well below the probe on both models (Figure 3).
2. On gpt-oss-20b the monitor flags almost every call made under pressure, so it ranks the calls that leak no higher than the others.

**4.5 Exploratory: what the probe is not reading**
1. Every call that does not leak was also made under pressure, after the request, in the same scenario and round, so detecting the request cannot explain the score.
2. The probe beats keyword rules on the reasoning and a flag for "the protected file was just read" (Figure 4).
3. What the probe does read is open: a probe on only the incoming peer message and tool results also scores high.


### 5. Related work (contrasts, ≤1 page)
1. Probes can detect that a tool-using agent was exposed to an attack, but every call we score has already been exposed to the same pressure.
2. Prior early-warning work reads hidden states before an unwanted action, with weak or mixed results against text monitors. We find a strong per-call signal and a weak round-level one in a peer-recruitment setting.
3. Text monitors catch more coordinated misbehaviour when they see agents' messages, and we compare them with probes on the same calls.
4. Persuasion between agents has been measured from text and outcomes. We add the persuaded agent's activations.

### 6. Discussion and limitations
1. An overseer cannot know early which episode will leak, but it can know which call is about to.
2. For an exact secret an output filter would also work, so the per-call probe matters most where no filter can match: paraphrased or encoded leaks, and pausing a call before it acts.
3. Limitations, ordered by impact, one short paragraph each:
   - narrow setting (two models, one template, one peer, exact strings);
   - per-call results confirmed only for the gpt-oss reasoning probe, on few leaking calls;
   - warning about the current call only;
   - what the probe reads is open;
   - alarm cost per episode is high at per-call cutoffs;
   - one monitor family, untuned;
   - automated labels and judges.
4. Future work in two sentences: causal tests of the probe direction, transfer to other environments, larger multi-agent settings.

### LLM usage statement (unnumbered, after the conclusion)

## 6. Appendix, as questions with one-line answers
## 6. Appendix, as questions with one-line answers

| § | Question | One-line answer |
|---|---|---|
| A | What does an episode look like, and which scenarios did we build? | Six scenarios from one task template; one leaking and one refusing transcript, excerpted. |
| B | How are leaks labelled, and can the labels be trusted? | A rule on the tool log decides the leak; an automated judge's deliberate-or-accidental labels agree with the author's blind labels (κ in table). |
| C | How were the datasets built and checked? | Eligibility rules, the count table and replay fidelity: the replay reproduces the served model's replies closely. |
| D | How are probes trained and scored? | Logistic regression, layer chosen inside each training fold, within-stratum AUROC with a worked example, and the family bootstrap. |
| E | What do the text monitors see, and how are they asked? | The monitor setups, prompts and access levels, with the full grid in one table. |
| F | What was frozen for the fresh test episodes, and what happened? | Both plans and their criteria; both were met. Alarm counts in one table. |
| G | Does the per-call result hold under other evaluations and settings? | Yes: pooled CV, the mean aggregate, the channel-only label and fixed layers all give similar rankings. |
| H | Is the probe reading pressure, the secret string or the read step? | No to all three; the incoming-message probe shows that much of the signal arrives with the input. |
| I | Does the probe warn before the call that leaks? | Weakly: one call ahead it mostly detects the protected-file read, and first alarms come at the start of the leaking call. |
| J | What would alarms cost in deployment? | High per episode at per-call cutoffs; an episode-calibrated cutoff catches about a third of leaking episodes. |
| K | What should a round-level text monitor ask and see? | Forecasting, with the peer's messages, helps the strongest monitor; adding the probe helps only a weaker one. |
| L | Why is round-level prediction near chance on gpt-oss-20b? | It usually leaks within a round of the request, so there is little to predict from. |
| M | How does behaviour vary with pressure and model? | Six-row screen summary; the second target's peer strategy and why Gemma stayed behaviour-only. |
| N | Dual use and ethics | What we release, the risks, and why the uplift is low. |
| O | Analysis history | One table: each analysis, when it was decided, what it replaced, whether it was confirmed. |
| P | Reproducibility index | Each figure, table and headline number mapped to its run folder and script. |
| Q | Prompts | Exact target, peer and monitor prompts for the main scenario. |

## 7. Figure plan (one colour-blind palette: Qwen and gpt-oss each keep one colour; probe, monitor and baseline each keep one marker family)
