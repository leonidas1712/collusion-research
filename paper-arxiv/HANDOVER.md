# Handover notes for the arXiv rewrite

Shared notes (not paper prose). Append your own entries; keep sections by owner where it matters.

## For Leo first

### The submitted abstract reports the *development* round-level number, not the *confirmed* one (claude-4, verified against run folders)

**What to know:** the submitted abstract's near-term clause — "(Qwen3-32B: probe AUROC 0.58,
best monitor 0.65, both holding on new episodes)" — states the **development** estimate (0.58)
in the same breath as the holding-on-new-episodes claim. The pre-registered **confirmed primary**
on the fresh episodes is **0.681 [0.604, 0.753]**, higher than 0.58. So it is not an overclaim,
but it is a misleading conflation: a reader takes 0.58 to be the confirmed number, and it is not.

**Verified (read-only, old checkout):**
- Pre-registered plan `docs/confirmatory_plan.md`: primary analysis = near-term A-hazard probe
  AUROC vs 0.5, within scenario × round, on the 89 fresh episodes; primary score = mean of the
  three seed models.
- Run `runs/20261025-1030-e06-confirmation/report.md`: A_hazard (primary) probe
  **0.681 [0.604, 0.753]** (1,787 calls, 82 positives, 89 episodes); success criterion "probe CI
  above 0.5" **PASS**. Best monitor on the fresh set = Jev forecaster L3 **0.644 [0.560, 0.722]**.
- The **0.58 is the development estimate**, not a fresh-episode number: held-out-scenario all-data
  = 0.579 (rounded to 0.58 in the paper), pooled CV = 0.586 (`runs/20261025-1456-e05-all-data-main`).
  codex-2's "all-data CV number" is correct in substance.

**Is the submitted wording accurate?**
- **Abstract:** imprecise / misleading (the one spot). It credits a development point estimate
  (0.58) with "holding on new episodes." Not false, not an overclaim (0.58 < 0.68).
- **Body §4.4 and Figure 3 caption:** accurate. They separate development (probe 0.58, monitor 0.65)
  from the fresh set (probe 0.68, Jev 0.64), with filled vs hollow markers. The explicit
  0.681 [0.604, 0.753] appears in the body only as the rounded "0.68"; Appendix E Table E.2 reports
  the confirmation combination numbers (Jev 0.643 → 0.695; GPT-5-nano 0.554 → 0.667).

**For the rewrite (per coordinator + WRITING.md §4.3):**
- Report the confirmed round-level near-term number **as-is: 0.681 [0.604, 0.753]** as the headline
  for that claim. Put the development estimate (0.579 held-out / 0.586 pooled) in the robustness
  appendix, named, once.
- Fix the abstract so the confirmed number is the one the reader sees; do not attach a development
  point estimate to a "holds on new episodes" claim.
- codex-2 agreed, and I concur: any **new** per-call analysis run on the already-inspected fresh
  sets is **exploratory out-of-sample**, not a new confirmation. Only the frozen round-level
  near-term result (and the frozen gpt-oss this-call reasoning probe) are confirmed.

**Open question for Leo:** confirm you want the abstract to lead the round-level claim with the
confirmed 0.68, with 0.58 moved to the robustness appendix. (Default taken for the draft: yes.)
