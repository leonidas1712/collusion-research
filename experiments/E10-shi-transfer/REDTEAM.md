# E10 red team: ways the plan could mislead

**Status:** review of `PLAN_DRAFT.md` (2026-10-27), written before any GPU spend. The plan was not edited.

**What I checked.** I read the plan, Shi et al. (the setup, Appendix B, the worked trajectories in G.3 and the prompts in H.1), our paper's Method section, and the Handshake sprint page. The sprint page shows only the abstract, so the Handshake numbers below are taken from the plan. I also downloaded the 50 released Qwen3.6-27B traces at the pinned revision and computed some text-only baselines on CPU. These are marked **[rt]**. No activations, models or API calls were involved.

- The [rt] loader reproduces the plan's counts: 1,000 verdict calls (767 ACCEPT), and a primary set of 305 calls with 100 positives.
- [rt] text baselines use grouped 5-fold CV over all 50 trajectories and the plan's within-episode AUROC. TF-IDF is fitted on unigrams and bigrams.
- The scripts are throwaway files in a session scratchpad and are not in the repo. Step 2 of the plan (`load.py`) should rebuild them as its first deliverable (see §7).

---

## Top issues, ranked

1. **At the verdict call, text already gives most of the answer, and the plan's bars are set below that text.** On the primary label within episode, [rt] gets:

   | Text baseline | Within-episode AUROC |
   |---|---:|
   | Bag of words on the agent's previous private reflection only | 0.73 |
   | Bag of words on the current episode's channel messages | 0.71 |
   | Bag of words on both | 0.76–0.78 |
   | One regex: does the agent's own channel text say "accept" rather than "reject"? | 0.70 |

   - The "transfer" criterion (§7) is probe ≥ 0.70 and probe ≥ gpt-5-nano. A probe that only reads "I said I'd accept" passes it.
   - The plan's B3 views do not isolate the two strongest text sources. One is the previous reflection; the other is the agent's *own* channel messages. View B3(a) buries both in about 30k tokens of task logs.
2. **The feedback baseline is close to 0.5 within episode, so "beats feedback" is trivially true and empty.**
   - Among agents that have not yet given in, previous feedback hardly varies. At episode 2, 74 of 99 calls follow the identical feedback "+0, you were wrong, peer was wrong".
   - [rt] bag of words on the previous feedback text scores 0.505 within episode. The "previous reward" feature scores 0.465.
   - "Strong transfer" requires probe − B1+ > 0. That will likely pass, and it will be misread as "activations add to feedback". [H]'s 0.905 feedback result is a pooled, time-driven effect.
3. **The read position comes after the agent has publicly committed.** At P0 the context holds the agent's own five channel messages for this episode.
   - In 43 of 100 positives (against 12 of 205 negatives), those messages already say "accept" (for example "Submitting accept!", Shi p.29–30).
   - [H]'s own abstract says the decision forms *before* the exchange. The informative positions are earlier, and they cost nothing (see §5).
4. **The label is a timing label: every negative is a future positive.** All 100 agents eventually accept. Within an episode, `y_first` contrasts "accepts now" with "accepts one or two episodes later".
   - That differs from our paper, where refusing episodes supply the negatives.
   - A trajectory-level trait (an early mover against a late mover, or the peer's style) can score well without any call-level decision signal. No baseline in the plan tests this.
5. **The locked test is too small to support any comparison, and the split adds little protection.**
   - [rt] interval widths for the text baseline: ±0.08 on all 50 trajectories, about ±0.12 on 20 trajectories (95% trajectory bootstrap).
   - [H] has already analysed all 50 trajectories, so the hold-out guards only against our own tuning. It costs 60% of the power.
   - Each trajectory's two agents are strongly coupled (point 2 of §3), so the effective n is close to the number of trajectories.

Each issue is expanded below, followed by a minimal version that would convince a reader.

---

## 1. The label

**Is "first ACCEPT = gives in" sound?** Mostly yes, as a behavioural label.
- The rule is unambiguous (Shi p.48: complete raw log, "with no omission…"), and every peer log is longer than 1,390 characters, so no ACCEPT can comply.
- Shi themselves call mutual ACCEPT the primary outcome because it is "determined directly by the agents' submitted verdicts" (p.13).
- The 20 negatives where the peer's task failed are a different kind of REJECT: rule-following and also correct on the merits. They are easy negatives for any detector of work quality.
  - **Fix:** make the peer-correct-only analysis co-primary, not a side check. It keeps 90 positives and 185 negatives in total.
  - Peer correctness does not otherwise confound much: 10 of 100 positives and 20 of 205 negatives had a failing peer.

**Is "first ACCEPT" post hoc?** Slightly. It was chosen after seeing that only 28 of 695 later calls revert to REJECT. But it mirrors our paper's `y^call` (score up to and including the first act), and it was fixed before any score was computed. This is a low risk. Say in the write-up that it mirrors the paper and was fixed before scoring.

**The real problem is that the label measures timing (top issue 4).**
- No agent holds all ten episodes, so there is no "never gives in" class. Within episode 3, the 27 negatives are exactly the agents that give in at episode 4 or later.
- A probe can therefore win by reading a stable disposition rather than the imminent decision, for example how legalistic the agent was in episode 1, or the peer's style.
- **Add:**
  - (a) A **trait baseline**: the same probe and bag of words, but fitted on the agent's *episode-1* verdict-call input, predicting the label at the later call. If that scores close to the P0 probe, the "this call" reading is a trait reading.
  - (b) A **lead-time label**, `y_next` = "first accept is in the next episode", scored on calls before the first accept. It is the analogue of our paper's "one call earlier" row. A sharp drop from `y_first` to `y_next` is the short-range pattern our paper reports. A flat profile means trait.

**A better or additional label.** Keep `y_first` as primary. If the trait baseline is strong, report the probe's gain over it and not raw AUROC.

**Label noise.** [H] reports that 9% of resamples disagree with the logged verdict on random calls, and more on hard ones. This caps AUROC. It is already noted; keep it.

## 2. The metric

**Does within-episode AUROC remove the episode-number shortcut?** Yes for t itself: any function of t scores 0.5.

It does not remove the cumulative history that varies within t:
- whether the peer has accepted me before: at episode 3, 12 positives and 2 negatives with it, against 33 and 25 without;
- message lengths;
- role.

B1+ covers the first of these, which is good. [rt] role (Alice or Bob) scores 0.53 and the agent's own message length 0.535, so both are small.

The metric also neutralises most of the *feedback* signal (top issue 2). So the scientifically interesting competitor is text, not feedback. The plan's narrative ("feedback causes the verdict, so B1 is the bar to beat") was written for the pooled metric and should be rewritten.

**Group weights in practice:**

| Episode | Share of positive weight | Negatives |
|---|---:|---:|
| 2 | 27% | 72 |
| 3 | 45% | 27 |
| 4 | 21% | 6 |
| 5 | 5 positives | 1 |

- Episodes 4 and 5 carry about a quarter of the weight on 7 negatives. On a 20-trajectory test, episode 4 will have about 2 negatives, so a single call moves the score.
- **Fix:** pool episodes 4 and later into one group (state it now), or report episodes 2 and 3 as the headline with the rest as a secondary.
- Training weights "equal within each episode" give one episode-1 positive and one episode-5 negative enormous weight. Drop or cap groups with fewer than 3 of either class *in training*.

**What grouping is right with about 6 verdicts per agent?**
- *Comparison groups:* the episode index, as planned. Each agent contributes at most one row per group, so there are no within-agent comparisons.
- *Resampling and CV unit:* the trajectory, as planned. Not the agent: the two agents are coupled (§3).
- The secondary grouping, episode × the peer's previous verdict on me, is nearly the same as episode alone in the early episodes, because the peer almost always rejected at episode 1. It adds little. A more useful secondary grouping is episode × "own channel text announces accept" (§4).

**Sanity gate G4 is weak.** It asks for pooled CV AUROC ≥ 0.90 on `y_hs`, but episode number alone gives 0.871 pooled. Any activation feature that tracks position or context length passes it. A broken replay can therefore pass G4. Use the within-episode positive control and G3 as the fidelity evidence, and keep G4 only as a comparison with [H].

## 3. Splits, leakage, dependence, power

- **Class counts on the locked side (40 / 83).** These are harmless as disclosed: counts carry no information about scores. The disclosure is fine.
- **Contamination is mostly outside our control.** [H]'s layer choice, examples and figures come from all 50 trajectories, and the team has read [H]. The hash split guards only against our own tuning.
- **Coupling between the two agents is strong.**
  - [rt] In 19 of 50 trajectories, both agents first accept in the same episode. In 43 they are within one episode.
  - In the same episode, the peer accepts me in 67% of positive calls against 18% of negatives. The peer usually says so in the channel.
  - Grouping by trajectory handles the CV leakage correctly. But the effective sample is about 50 (or 20) clusters, not 100 (or 40) agents.
  - A trajectory bootstrap with 20 clusters also tends to give intervals that are too narrow. Use a percentile-t interval, or report the leave-one-trajectory-out spread as well.
- **Power.** [rt] interval for a text baseline of about 0.75: ±0.08 with all 50 trajectories, about ±0.12 with the 20 locked ones. A paired difference against a correlated baseline is narrower but still about ±0.07–0.10 on 20.
  - The locked test can support "probe > 0.5" and "probe is not worse than the text baseline by more than X". It cannot support "probe beats text".
- **Recommendation.** Make the primary estimate a **frozen-pipeline nested grouped CV over all 50 trajectories**.
  - Commit the analysis code, the label, the position, the rule for choosing the layer, and every baseline view before any activation is captured.
  - Keep the 20-trajectory hold-out as a one-shot *confirmation* of the sign only.
  - If a properly fresh test matters, the honest version is new Qwen3.6 trajectories from Shi's harness (self-hosted vLLM, the same code commit). This costs GPU generation and is a separate request; I do not recommend it for Phase 1.
- **Task-instance overlap.** The plan's per-task check is fine. Also report whether the probe's errors cluster by `sequence_id`.

## 4. Shortcuts and missing baselines

[rt] within-episode AUROC on the primary label (grouped 5-fold CV, all 50 trajectories):

| Score | AUROC |
|---|---:|
| Bag of words: previous reflection + current channel | 0.756 (0.775 unweighted) |
| Bag of words: previous reflection only | 0.733 |
| Bag of words: own + peer channel, current episode | 0.710 |
| Bag of words: own channel messages only | 0.708 |
| Regex: own channel says accept and not reject | 0.703 |
| Bag of words: peer channel only | 0.652 |
| Regex: previous reflection endorses accepting | 0.622 |
| Regex: peer channel says accept | 0.593 |
| Previous verdict on me was right | 0.539 |
| Own message characters | 0.535 |
| Role is Bob | 0.529 |
| Previous feedback text, bag of words | 0.505 |
| Previous reward | 0.465 |
| Peer raw-log length | 0.415 (inverse: 0.585) |

**Missing baselines, to add before freezing:**
1. **Bag of words on the previous reflection only, and on reflection + current channel.** These are the strongest text views, and the bar the probe must clear.
2. **The agent's own announced verdict** (a regex on its own `send_message` content, in addition to the peer's). B6 checks only the peer.
3. **A trait baseline from episode 1** (§1).
4. **A stronger zero-shot judge on the short view.** gpt-5-nano on 30–60k-token inputs is a weak bar. Its verbal probabilities are coarse, so ties also push its AUROC toward 0.5.
   - Give the judge the short view (previous feedback, previous reflection and the current channel, about 1–2k tokens) and use a stronger non-Claude model. It is cheap at that length.
   - Keep the full-context nano as a secondary.
   - Our paper's lesson ("the zero-shot judge is well below the probe") only transfers if the judge is competent.
5. **Probe + best bag of words, stacked.** This measures what activations add over text, which is the comparison that matters here. "Probe + B1+" measures almost nothing within episode.

**Other things that could predict ACCEPT trivially:**
- The `message_type` labels in the peer header (`[type=bob_log_p3]`). They reveal a log-chunking strategy, which signals that the agent is holding out. Bag of words will catch them.
- The `chars_sent` tool results.
- Overlength-rejection errors.
- Delivery-failure notices from the runner (8 calls).
- Report the probe on the **subset where the agent's own channel text does not announce accept** (250 calls, 57 positives) as a co-primary. This is what E04's plan intended ("flag steps where the decision is already visible in the agent's own text").

## 5. Replay fidelity and read position

**Read positions: earlier ones are free and more informative.**
- The verdict-call prompt contains, as a prefix, the previous feedback, the previous reflection, the task phase and the communication opening.
- The model is causal; the linear-attention layers are also strictly causal. So the activations at those earlier tokens in the verdict-call forward pass are the activations the model had there, provided the earlier assistant turns render the same way (they do: all are before the last user query).
- **Capture the following in the same pass, at no extra cost:**
  - **P_fb:** the end of the previous feedback message;
  - **P_refl:** the end of the previous reflection;
  - **P_talk:** the end of the current communication-opening user message;
  - the end of each of the agent's own `send_message` calls;
  - P0.
- The **headline that would actually be new** is a within-episode profile across these positions, compared at each one with the text available at that point (§6).
- One caveat: these are `<|im_end|>` tokens of messages, not "last prompt token + generation prompt". State it.

**P2 is mis-specified.** The message right before the verdict prompt depends on the agent's role. [rt]:
- For Alice, it is Bob's round-5 message in 492 calls and a runner delivery-failure notice in 8.
- For Bob, it is his *own* `send_message` tool result `{"success": true, "chars_sent": N}` in 492 calls, and a failure result in 8.

So P2 compares different things across roles. Redefine it as "the last token of the last channel content the agent received" or drop it. The loader's verdict-prompt cut ("last user message starting with `## Episode {t}: verdict phase`") does match exactly one message in all 1,000 calls [rt].

**Further fidelity risks:**
- **G1 checks only the token count.** It cannot catch a mismatch that keeps the length but changes the tokens: tool-schema key order, JSON spacing in `arguments`, or swapping `\n\n` for `\n` in both places.
  - **Add:** compare against a deliberately wrong render (for example, the tool schema dropped or arguments re-serialised) to show that G3 tells them apart.
- **The G3 threshold is too loose.** 0.4 nats/token is about twice E02's 0.19, and [H] got 0.256. A moderately broken template could pass.
  - Report the NLL separately for the reasoning and for the tool-call body, as our paper's table does. Verdict calls used forced tool choice, which may be constrained decoding, so the NLL of the JSON body may not mean what it does elsewhere.
  - Set the gate on the reasoning NLL, at about ≤ 0.30.
- **Long contexts and the linear-attention state.** The bf16 recurrent state can drift from vLLM's kernels over 60k tokens. Stratify G3 by context length and include the longest calls, not only the first 20, which skew short.
- **The template revision.** Shi do not give the model revision. A count match on [H]'s render is reassuring but not proof that the template text is identical. The P0 token (`<think>\n` in the generation prompt) depends on the template version; G1 would catch an error of ±2 tokens.

## 6. Novelty and framing

[H] already reports 0.956 on this data, pooled, on `y_hs`, at P1, with no hold-out. Most of that is episode index and habit after the first accept. Rerunning the same probe more strictly will give a lower number, plausibly 0.7–0.85. That is not a failure, but it is a weak paper result if it is the only result.

**What would be informative for our paper:**
1. **Probe vs the best text view, within episode, on `y_first`, on calls where the agent's own text does not yet announce accept.**
   - Probe ≥ text there means the call-level signal carries over to emergent give-in, which supports our main claim.
   - Probe ≈ text means "in settings where agents write their plans down, text is enough", a scoped and honest bound.
2. **A lead-time profile across P_fb → P_refl → P_talk → P0, for `y_first` and `y_next`.** This tests whether our "the warning is short-range" result (§4.2 of the paper) holds here, and it tests [H]'s claim that the decision forms before the exchange, under a stricter metric.
3. **A trait-vs-call decomposition** (the trait baseline from episode 1). This is what our setting could not test, because refusers supplied its negatives.

**Framing:** "a stricter re-test of Handshake's result in a third model, under our metric", with Handshake credited for the replay and the first probe. Lead with whichever of items 1–3 is solid, stated plainly. Do not lead with a pooled number. Do not frame "beats feedback" as a finding.

## 7. The minimal convincing version, and cost

**Run order:**
1. **CPU, free, about half a day.** Build `load.py` and the full text-baseline table (§4) on all 50 trajectories now, before any GPU work. It fixes the bar the probe must beat and tells us whether E10 is worth running at all. If the best text view reaches about 0.85 or more, the probe has little room.
2. **Freeze the pipeline in writing:**
   - the label (`y_first`; `y_next` secondary);
   - the positions (P0 plus the free earlier ones);
   - the rule for choosing the layer (fixed now, or chosen inside the folds from a pre-declared middle band);
   - the episode-4+ pooling;
   - the text views;
   - the success criteria, restated against the best text view.

   Commit it. Write `splits.json` (a 50-trajectory nested CV, plus the 20-trajectory confirmation).
3. **CPU.** `render.py` and G1, plus the deliberately wrong render.
4. **G2 benchmark, about USD 1–2.**
5. **Core replay of 348 calls, all positions in one pass, about USD 2–6.**
6. **Analysis.** Nested CV first, then the one-shot confirmation on the 20 trajectories. Judges: one stronger model on the short view, plus nano on the full view.
7. **Skip the 652-call extension.** It only feeds `y_any`, which the plan already rules out as evidence.

**Cost plausibility.**
- 7.67M tokens at 1,500–5,000 tokens/s is 0.4–1.4 h. At USD 3.95/h that is USD 2–6, plus about 10 min of load per container. That is plausible.
- The pure-torch fallback for the linear-attention layers at 60k tokens could be well below 1,500 tokens/s, and memory-heavy. The G2 gate rightly catches this; make sure G2 includes the 60.6k call.
- Judges on the short view cost cents. Nano on the full view is about USD 1–2, as estimated.
- The Volume at 56 GB for a month is minor; delete it afterwards.
- The two-to-three-day time estimate is fine. Add half a day for step 1.

## 8. Smaller points

- **§2 "Why ACCEPT always breaks the rule".** "Peer log length > total characters the peer delivered" is the right per-call check. Keep it, and note that it is always true.
- **§5 "Within episode … so does context length to the extent it tracks t".** True only partly: length varies within episode with task type and verbosity. B2's length score is correctly reported within episode.
- **§6 B6 regexes.** Add the agent's own announcement, `message_type` and `chars_sent`. Peer raw-log length anti-correlates with acceptance (0.415 within episode), probably through task type.
- **§7 per-type criterion.** With about 13 positives per type on the locked test, "one type ≥ 0.7, others ≈ 0.5" cannot be told apart from noise. Make it descriptive only.
- **Positive control.** Previous reward has three values, so define the binary target (for example, reward > 0) now.
- **Steering.** [H] reports steering results. They are out of scope here; do not let the write-up imply that we tested causality.
