# Feedback round 2 (Leo, 27 Oct ~02:45): process in parallel

E09 (permitted vs forbidden) is shelved; it may become its own paper. The Shi et al. plan and its red-team come later.

## A. Title
Change the title to:

```latex
\title{Pre-Crime for Agents, at the Last Second:\\ Probing When a Recruited Agent Gives In}
```

Keep the manual break after the colon. Check the render. If the subtitle still spills onto a third line, report it.

## B. Abstract
Replace the abstract with this text. Every number goes through its macro.

> Just before an AI agent leaks a secret its operator told it to keep, a linear probe on its activations can tell. We study recruitment, a common first step of collusion: a peer agent presses a target agent, over many rounds, to reveal such a secret, for example a deploy token. The target often refuses at first, then gives in. Read at each call, before the model generates anything, a probe tells whether that call is about to leak the secret. On fresh Qwen3-32B episodes, at a fixed threshold, it catches 82% of leaking calls while flagging 5% of calls in refusing episodes, catching more leaks with far fewer false alarms than a zero-shot text monitor; counted per episode, most refusing episodes still see at least one flag. A bag-of-words classifier trained on the same text comes close to the probe, so most of the gain comes from training on labelled calls, with activations adding a small edge. Making the disclosure permitted leaves the probe's score essentially unchanged, so it detects the coming disclosure rather than the rule being broken. On gpt-oss-20b, a reasoning probe scores AUROC 0.91 (95% CI 0.78–0.99, 26 leaking calls) in a pre-registered test on fresh episodes. The signal is sharp but short-range: it weakens when asked about the next round, and is weak when asked whether an episode will ever leak. For multi-agent oversight, this suggests a cheap per-call monitor that flags an agent just before it leaks and escalates that call for review, and much of its signal can be read from the text alone. Such monitors would matter most where output filters fail, such as paraphrased, encoded or slowly coordinated leaks, which we leave to future work.

arXiv caps the abstract at 1,920 characters. Check the plain-text character count after macro expansion.

## C. Fixes
1. **Tables 26 and 27 disagree.** Table 26 gives the development near-term probe as 0.57. The first row of Table 27 (label A, held-out scenarios, logistic, layer selected) gives 0.61. They look like the same quantity. Table 27 matches the sprint's first-batch table (0.611 logistic, 0.608 MLP), so one of the two may come from a different call set. Reconcile them, or state each one's call set in its caption.
2. **The protected-file writeback count is stated three ways.** Appendix B says "a few calls", Appendix G says "the episode", and HANDOVER says 2 episodes. Pick the correct number and use it in both appendices.
3. **The Fig. 4 caption.** Add: "the stronger of two text views for each model; both are in Table 21." Qwen uses the latest-message view (0.93 vs 0.71 for full input); gpt-oss uses the full input (0.86 vs 0.84).
4. **Section O** cites Table 30 for the changed numbers. It should cite Table 31.
5. **Table 30, E08 row.** Replace the internal shorthand ("prompt-only FORBID failed reproduction; accepted 1717 …", "(1700/1703)") with: "A first replay did not reproduce the frozen scores and was discarded; the reported replay holds the saved reply fixed and reproduces them."
6. **Table 22** labels the last-prompt probe "Input probe". Rename it "Last-prompt probe". The incoming-only probe is a different probe.
7. **A stale HANDOVER note.** It still says "keeps 'pre-registered' for both". The paper now uses it for gpt-oss only. Update the note.

## Deferred (not now)
- Fig. 3 duplicates the top half of Fig. 8.
- Table 19 has mixed labels.
- The Contents placement.
