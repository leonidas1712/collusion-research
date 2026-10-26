# Editor review: PLAN.md + claims.md + glossary.md vs WRITING.md (claude-4)

Reviewed at `4ed3d2d`-era. Verdict: **strong plan, one blocking issue, a few should-fix.**
The plan already folds in blind-review-1 (#2361) and the author feedback (#2364). Below, ranked.

## Blocking (fix before drafting Results/figures)

**1. Figure 1 puts two different leak labels on the same axis.** The ladder (C2) is *any public
emission* on development episodes. The confirmed near-term anchor is the *round-level channel label*
on fresh episodes. In the Figure 1 plan these sit at the same x = "this round or next": hollow =
any-public development rung, filled = round-level fresh anchor. A reader reads the filled marker as
confirming the hollow rung — but they are different labels, so it does not. This re-creates exactly
the sprint's cohort confusion that WRITING §4.3 targets.
   - **Fix (preferred):** recompute the Qwen development near-term rung under the *same label as its
     fresh confirmation* (round-level), so the hollow and filled markers at x=near are the same
     quantity. Keep the any-public ladder as its own series/panel if you still want the unified-label
     progression. PLAN §3.3 item 4 says "recompute dev eventual/near-term" — state explicitly it is
     under the round-level label, matching the fresh anchor.
   - **Fix (alternative):** also score a frozen development-only probe on the fresh episodes under the
     *any-public* label (out-of-sample, open marker), so the confirmed point on the ladder matches the
     ladder's own label; keep the pre-registered round-level anchor in a clearly separate panel and
     say in one line it uses a different label.
   - Either way: every marker that shares an x-position in Figure 1 must use one label, and the caption
     must say which. This is the single most important thing to get right.

## Should-fix

**2. Proposal A shrinks the Qwen development positives.** Dev = replay-2 only (pre-freeze), so the
recomputed Qwen per-call and ladder dev numbers rest on fewer give-ins than the sprint's 101. Confirm
with codex-2 that the dev-only per-call AUROC is stable (tight enough CI) before it becomes a
supporting headline (C1). The strong part under proposal A is the frozen dev-only probe scored on the
89 fresh episodes (C1 point 2) — keep that as the load-bearing Qwen per-call evidence, with the
dev-only number clearly secondary.

**3. Figure 1 risks overload.** It is being asked to be the headline ladder, the number-home grid,
two datasets (hollow/filled), two label types, and Jev overlaid. WRITING §6 wants the headline figure
graspable at a glance. Consider keeping Figure 1 to the probe ladder (both models, three distances,
dev vs fresh) and leaving probe-vs-monitor to Figure 3. Do not let the headline figure need its
caption to be read.

**4. Appendix is 17 questions (A–Q).** Defensible if each is lean, but BRIEF §3 says the appendix must
be clean. Candidates to merge: I ("warn before the call?") with L ("why round-level near chance on
gpt-oss?"); J (alarms) could fold into F (what was frozen / alarm counts). Aim for ~12.

## Correct — called out so they are not "fixed" by mistake

- **C2 confirmed anchor = 0.68, not 0.58.** This matches the frozen primary
  (0.681 [0.604, 0.753], `runs/20261025-1030-e06-confirmation`) I verified for HANDOVER. The 0.58 is
  the development estimate and should appear only as the development near-term rung / robustness.
  Keep the anchor at 0.68.
- **§4.1 "for the probe and the best text monitor alike"** correctly conveys that at the round level
  the monitor is comparable to the probe (Jev − probe ≈ 0). The "probe beats the monitor" claim (C3)
  is per-call only. Keep them separate; do not let C3 bleed into the round-level framing.
- Six defined terms exactly; abstract has two numbers; one-evaluation-per-question table; recompute-
  not-explain list; status-by-structure with no "exploratory" in Results sentences. All compliant.

## Checklist (WRITING §10) against the plan

PASS as planned: ≤3 abstract numbers; ≤1 number per claim in prose; ≤4 named datasets; status by
structure + markers; counts in one table; no internal codes in main text; glossary consistent; each
limitation once; appendix by question with answer-first.
WATCH while drafting: "no main-text comparison mixes datasets/evaluations/labels" — item 1 is the live
risk; the caveat audit (my Phase-2 pass) will re-check every figure and comparison against it.

## Accuracy constraints for drafting (from codex-2 #2372, endorsed by editor)

These are label/claim-scoping facts the draft must honour; the caveat/accuracy audit will enforce them.

1. **"Near chance at round level" (gpt-oss) is the OLD channel-give-in label, not the any-public ladder.**
   The matched gpt-oss ladder is eventual 0.61, this-round-or-next 0.64, this-call 0.91 (same 1,995 calls).
   So outline §4.3.2 must not let "gpt-oss is near chance at the round level" sit on the same any-public
   ladder — the round rung there is 0.64, not chance. State the near-chance fact against the channel label
   explicitly, or keep it out of the any-public ladder. (Reinforces blocking item 1.)
2. **gpt-oss has a control arm but NO target-alone arm.** "Control and target-alone episodes never leak"
   (outline §2.4, §4.1, setup fact) is a Qwen statement. Scope per model: Qwen has control + target-alone;
   gpt-oss has control only.
3. **"Every non-leaking call was after the request" is a gpt-oss property, not Qwen's.** The Qwen post-read
   cohort is not uniformly post-peer-ask. C4 / outline §4.5.1 must scope "after the request" to gpt-oss,
   or reword so it is true for both.
4. **The confirmed reasoning probe warns before PUBLIC output, not "before the call writes anything."**
   It reads generated reasoning tokens. Only the last-prompt probe reads before the call generates anything.
   Keep "before any public output" for the reasoning probe (Method §3.2 already does); do not let C1's
   "before a call writes anything" attach to the confirmed reasoning headline.
