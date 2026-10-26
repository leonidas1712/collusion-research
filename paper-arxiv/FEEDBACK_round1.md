# Feedback on the overnight draft, round 1

From Leo. Work through this as an edit queue on the `followup` branch. Everything in `WRITING.md` still applies. When done, rebuild, rerun both blind reviews (clarity and rigour) and the viewer check, then update `HANDOVER.md` with what changed.

Overall: this is a big improvement. It has a clear story, an appendix organised by question, a headline figure near the top, and honest pre-registration wording. The problems below are mostly about framing and structure, not rigour.

---

## 1. The introduction must set up the problem, not repeat the abstract

**Problem.** The intro opens with the abstract's first sentence and goes straight into results. A paper introduction sets the background and context first, explains why the problem matters and what is missing, and only then says what we did and found. Look at how two well-known safety papers do it:

- **Arditi et al. 2024, "Refusal is mediated by a single direction."** It opens with deployment context: models are fine-tuned to refuse, people jailbreak them, and the stakes rise with agency. It then gives the research angle (linear representations, steering). Only after that comes "In this work, we show…", followed by a short summary of findings.
- **Betley et al. 2025, "Emergent misalignment."** It opens with assistants being deployed and alignment efforts. It then names prior surprising failures, introduces the new phenomenon, describes the setup and controls, and ends with a numbered summary of contributions.

**What to do.** Rewrite Section 1 as five paragraphs, roughly:

1. **Context.** AI agents increasingly work alongside other agents, sharing channels, tools and credentials. In the 2026 Hugging Face incident, agents coordinated to break their rules, and some pressed others to join (cite OpenAI 2026a; Greenblatt et al. 2026).
2. **The problem.** Collusion often starts with recruitment: one agent pressing another to break its operator's rule. Explain why this is hard to oversee:
   - the request comes openly, from a teammate, in the channel the target is meant to use, so it is not prompt injection;
   - the target often refuses for a while and then gives in.
3. **The gap.** Current oversight mostly acts after the fact:
   - output filters catch an exact secret once it is written;
   - text monitors read transcripts.

   The question is whether an overseer can tell, before a call acts, that the agent is about to give in, in time to pause it. Position against prior work in a few sentences: probes for injection exposure and for agents told to collude, and early-warning work under user pressure or injection. This is a short version of what Related Work expands.
4. **This work.** Give the setup in two sentences, then the three findings in plain words:
   - the call that leaks is predictable just before it acts;
   - the signal is short-range;
   - a zero-shot text monitor does far worse, but a trained text classifier comes close, so activations add a small edge.
5. **Contributions** as a short bulleted list. Keep the headline figure in the intro.

The intro must not reuse sentences from the abstract verbatim.

## 2. Paper structure

Keep the overall order, with these changes:

| Section | Change |
|---|---|
| 1 Introduction | Rewrite as in item 1. |
| 2 Setup | Keep. Round "43.42%" to 43%. |
| 3 Method | Keep. Add the trained text classifier as a third detector alongside the probes and Jev, described in one short paragraph. It is now part of the main comparison. |
| 4.1 The call that leaks is readable before it acts | Bring the **top row of Figure 6** (probe score aligned on the leaking call, jumping at the leak) into this section. It is the most intuitive picture in the paper. |
| 4.2 The warning is short-range | Keep. |
| 4.3 Who can read the signal | Rebuild Figure 3 (item 4). |
| **4.4 What would deployment cost?** (new) | Move the operating-point material here from Appendix I. Bring in the **Qwen panel of Figure 7** (catch rate against false alarms, probe vs Jev). Explain per-call vs per-episode false alarms here (item 5). |
| 5 Related work | Keep it after Results. That is standard in ML papers, and both papers above do it. The intro now carries the key positioning, so this section can expand on it. |
| 6 Discussion and limitations | Add the cascade framing (item 5). |

Note the planned follow-up slots in `PLAN.md`: a "Does it generalise?" section (Shi et al. transfer) and an "Is the direction causal?" section (steering). Both go after 4.4, without restructuring. Do not write placeholder text in the paper.

Main text is about 7 pages. With the two figures moved in and the new 4.4, expect about 8–9 pages, which is fine.

## 3. Title

Change it. "An Agent's Activations Reveal…" overleans, given that a trained text classifier nearly matches the probe. Use:

> **Pre-Crime for Agents, at the Last Second: Probing When an Agent Gives In to a Recruiting Peer**

"Probing" signals the white-box method without claiming that only activations carry the signal. "At the last second" matches the short-range finding.

## 3a. The paper must stand alone: no "sprint cohort"

The arXiv version should not refer to the sprint version except in one place.

- **First-page footnote** (on the title or author line): "This work began at the Apart Research AI Collusion Research Sprint (October 2026), where an earlier version was submitted. Appendix N lists the numbers that changed." Do not mention the sprint anywhere else, apart from the analysis-history appendix.
- **Remove the term "sprint cohort" everywhere,** including Appendix J, Appendix K and Table 19. Describe each analysis by what it is:
  - **Per-episode checks:** recount them on the current development episodes from the stored judge labels. This covers the leak route split, deliberate vs accidental, and the authority-claim audit. This needs no new model calls. Report them on the named datasets.
  - **Round-level analyses:** they genuinely use a different label and call set, fixed by the pre-registered round-level test. Name them by that: "round-level label (Section B)".
  - **Any check that cannot be recounted and does not support a claim:** drop it.
- Retitle Appendix K as a question once its content is updated.

## 3b. Table of contents for the whole paper, after the references

There are many sections and appendices, so add a clickable table of contents. Place it after the references and before Appendix A, covering the main sections and every appendix section and subsection. Follow the format of our earlier paper, "Hidden in Memory" (arXiv 2605.15338).

- Use `etoc` or `titletoc` (for example `\startcontents` at the start of the document and `\printcontents` after the references). The entries must be hyperlinks through `hyperref`.
- Use depth: sections and subsections.
- Title it "Contents".
- Check in the viewer that every entry links to the right page.

## 4. Figure 3 and the trained text classifier

- **Add the trained text classifier as a bar in Figure 3,** next to the probe and Jev, on both models. Use the input view decided in the appendix, and report both views in the appendix table as now. It is the main comparison now, so it belongs in the main figure, not only in Table 16.
- **Retitle Figure 3** to: "A probe picks out the call that leaks; a zero-shot monitor does not, and a trained text classifier comes close."
- In 4.3, state the finding plainly once: most of the probe's lead over the zero-shot monitor comes from training on labels; activations add a small, reliable edge; much of the signal arrives with the incoming message.

## 5. False alarms: per call vs per episode, and the cascade framing

Readers will be confused by "5% false alarms" next to "59% of refusing episodes alarm". Explain it plainly in 4.4:

- **Per call:** 5% of calls in refusing episodes get flagged. If each flag sends that one call to review, this is the review workload.
- **Per episode:** a refusing episode has many calls, so the chance that at least one is flagged adds up. Roughly 1 − 0.95¹⁷ ≈ 58% for a typical Qwen episode, which is where the 59% comes from. This matters only if an alarm stops the whole agent.

In Discussion, frame the intended deployment as a **cascade**, as in Constitutional Classifiers++ (Cunningham et al., 2026, already cited):
- a cheap probe or trained text classifier runs on every call;
- a flagged call is escalated to a stronger automated monitor or a human before it acts.

Under that design, the per-call rate is the relevant cost, and the per-episode rate describes how often an episode sees at least one escalation. Present this as a takeaway, not as a caveat.

## 6. Abstract

Replace the abstract with this text:

> Just before an AI agent gives in and breaks its operator's rule, a linear probe on its activations can tell. We study recruitment, a common first step of collusion: a peer agent presses a target agent, over many rounds, to reveal a secret its operator told it to keep, such as a deploy token. The target often refuses at first, then gives in. Read at each call, before the model generates anything, a probe tells whether that call is about to leak the secret. On fresh Qwen3-32B episodes, at a fixed threshold, it catches 82% of leaking calls while flagging 5% of other calls for review, catching more leaks with far fewer false alarms than a zero-shot text monitor. A bag-of-words classifier trained on the same text comes close to the probe, so most of the gain comes from training on labelled calls, with activations adding a small edge. On gpt-oss-20b, a reasoning probe scores AUROC 0.91 in a pre-registered test on fresh episodes.
>
> The signal is sharp but short-range: it weakens when asked about the next round, and is weak when asked whether an episode will ever leak.
>
> For multi-agent oversight, this suggests a cheap per-call monitor that flags an agent just before it gives in and escalates that call for review, and much of its signal can be read from the text alone. Such monitors would matter most where output filters fail, such as paraphrased, encoded or slowly coordinated leaks, which we leave to future work.

Check before keeping it:
- The Qwen operating point must be the one in Table 18 (82%, 5.5%, rounded to 5%).
- The Jev comparison for the same calls must also come from Table 18 (68% at 29%).
- The bag-of-words sentence is a development-episode result. Keep the body explicit about that.

## 7. Decisions from HANDOVER.md

- **Leak boundary:** keep the frozen gpt-oss definition for both models, with the sensitivity check in the appendix.
- **Round-level number:** lead with the confirmed 0.68, and put 0.58 in robustness. The body already does this.
- **"Pre-registered":** use it for gpt-oss only. For Qwen, say "on fresh episodes held out from training".
- **Claims list:** update `docs/claims.md` so that the per-call claim includes the trained-text-classifier finding. I will sign off after this round.

## 8. Small fixes

- Table 16 shows "++0.250" etc. Fix the doubled plus signs in the macro.
- Table 22 renders "ona12%" and "testb". Fix the footnote markers.
- "Gao (2026) combine" should be "combines", and "as Gao (2026) also argue" should be "argues". It is a single author.
- The intro's "although per episode many refusing episodes still see at least one alarm" is moving to 4.4. Remove it from the intro.
- Check that nothing in the main text still frames the result as "activations vs text monitors" without the zero-shot qualifier.

## 9. Before handing back

1. Rebuild the PDF and the arXiv package.
2. Run a fresh clarity review and a fresh rigour review on the new PDF.
3. Run the viewer check in a real viewer. If computer use still fails, say so, and I will check it myself.
4. Update `HANDOVER.md` with:
   - what changed in this round,
   - the new review verdicts,
   - anything you disagreed with or could not do.
