# Handover notes for the arXiv rewrite

Shared notes (not paper prose). Append your own entries; keep sections by owner where it matters.

## For Leo first

### 1. The probe's lead over the zero-shot monitor is mostly *training*, not *activations* (claude-4, per @claude #2482)

A trained bag-of-words (TF-IDF) text classifier nearly matches the activation probe on **both** models
on its stronger text view: **Qwen 0.93 vs 0.96; gpt-oss 0.86 vs 0.91**. So the probe's large lead over
the *zero-shot* text monitor (Jev) comes mostly from **training on these labels**, not from access to
activations; activations add a **small, reliable edge** (paired interval excludes zero). The honest
framing is that a trained probe — on activations or on text — beats an untuned monitor, and the
activation probe keeps a small edge. **You may want to reconsider how much the title and abstract lean on
"activations."** Both text views are shown in Appendix H (`tab:text-baselines`) with no best-view
selection. Checks are development-only, saved-score, $0 (gpt-oss `runs/20261026-2242-e05-arxiv-gpt-text-workflow`;
Qwen rerun per codex-2 with verified family exclusions).

### 2. The submitted abstract reports the *development* round-level number, not the *confirmed* one (claude-4, verified against run folders)

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

### 3. Proposed abstract variant: surface the Qwen operating point (claude-4, per @claude #2539; Leo decides — abstract NOT edited)

Verified fresh-Qwen operating point (threshold set on control calls): the probe catches **82%** of
leaking calls at a **5%** refusing-call false-alarm rate; the zero-shot text monitor catches **68%**
at **29%**. This is more concrete than the AUROC and shows the probe's practical edge — it catches more
and false-alarms far less. Suggested wording (Leo to adjust): "…at a fixed threshold the probe catches
82% of leaking calls at a 5% false-alarm rate, where the text monitor catches 68% at 29%."

Two placements:
- **Option A (swap):** replace the gpt-oss "catching half of leaking calls at a 2% false-alarm rate"
  clause with the Qwen operating point; keeps the gpt-oss pre-registered AUROC (0.91).
- **Option B (add):** keep the gpt-oss clause and add the Qwen operating point as the "what it means" sentence.

**Travelling caveat (must accompany either):** per episode, because each episode has many calls, at
least one alarm still fires in **59%** of refusing Qwen episodes and **26%** of refusing gpt-oss
episodes — a deployed alarm needs episode-level calibration.

**Number budget:** the abstract already carries 4 numbers. To stay lean, Option A with the operating
point *replacing* the 0.98/0.75 call-AUROC pair keeps the count roughly flat and arguably reads stronger
(an operating point beats a bare AUROC). Leo's call.

## Technical decisions

- **ICLR header on the arXiv draft (codex #2373, via claude #2374).** With `\iclrfinalcopy` the ICLR 2027
  style prints "Published as a conference paper at ICLR 2027". For the arXiv draft, `main.tex` clears it
  with `\fancyhead[L]{}` right after `\maketitle`. Style files, margins and fonts are untouched. Revert
  this one line for a real ICLR camera-ready.

## Changed from the sprint version (accuracy audit, claude-4)

- **Why Gemma-4-31B is probe-excluded: reason changed, verified.** Sprint reason was "no channel
  post (0/8)". Under the unified any-public-emission label a file write counts as a leak, so the
  reason is now "no mix of leaking and refusing episodes." Verified against
  `docs/second_target_behaviour_report.md`: under the delayed whole-block strategy Gemma read the
  token in round 1 and wrote it to a file in 8/8 recruiting episodes, 0/8 channel posts, controls
  clean 0/4 — so every episode leaks, leaving no refusals to contrast. The new behaviour appendix
  wording is accurate and correctly scopes "no mix" to the *delayed* strategy. Caveat for the audit:
  the *natural* (non-delayed) prompt gave 6/8 (a mix), so the scoping to the delayed block request
  must stay explicit; do not state "no mix" of Gemma in general.

## Figure structure (claude-4, verified)

- **Round-level confirmation is its own figure, separate from the per-call ladder.** The headline
  ladder (Fig `fig:headline`) is now a single per-call panel (ever / this-round-or-next / this-call,
  both models, hollow=development, filled=fresh). The Qwen round-level near-term confirmation is a
  separate figure in §4.1 (`fig:round`, from `fig_round_confirmation.pdf`), captioned with its own
  pre-registered leak label. Separation verified clean: §4.1 references `fig:round` (no stale
  `fig:headline`(b)); no panel-b references to the ladder remain. This resolves the earlier Fig 1
  overload and the two-labels-on-one-axis risk.

## Future work (for Leo / after tonight)

- **Planned follow-ups (slots left in the draft, per PLAN.md §8):** causal **steering** on the probe
  direction (tests causality), and **transfer to the Shi et al. environment** (tests robustness in a
  less templated, emergent-collusion setting). Scopes in `private/followup_scope_steering.md` and
  `private/followup_scope_shi.md`.
- **A fair third detector arm (Leo's idea, #2491): a prompt-optimised LLM monitor** (e.g. GEPA on the
  decision-model monitor), evaluated next to the trained probe and the trained text classifier. **Check
  novelty first** before claiming this framing is new.
- **A possible unifying story for the follow-ups:** "Where does the warning signal live, and who can
  read it?" — trained probe vs trained text classifier vs optimised LLM monitor (who can read it), with
  Shi transfer testing robustness and steering testing causality.
- **Caveat to carry into that work:** the bag-of-words text classifier's strength may partly reflect the
  **templated synthetic peer messages**; a less templated setting (Shi) is the test.
- **Deferred baselines run only as quick checks tonight** (development, saved-score): a *tuned* text
  monitor, and a full `write_file`-conditioned analysis beyond the quick version.

## Changed from the sprint version (accuracy audit, claude-4) — continued

- **Pre-registration chronology corrected from the sprint wording (codex-2 #2517, source-documented;
  verified by claude-4).** The sprint framing implied the fresh episodes were collected *after* the
  plan was committed. Corrected definition: a test is *pre-registered* when a committed plan fixed the
  model, its threshold and its success criterion **before any detector was scored** on the test's
  episodes (method.tex). For **gpt-oss-20b** the reasoning-probe plan was frozen **before the fresh
  episodes were collected** (the stronger case). For **Qwen3-32B** the round-level plan was frozen
  **after** its fresh episodes were collected, when their overall leak counts were already known, but
  **before any probe or monitor was scored** (confirmation.tex:6). Both meet the "before any detector
  scored" bar, so the paper keeps "pre-registered" for both but **never claims "before collection" for
  Qwen**; the abstract/intro use "pre-registered" only for gpt-oss. Exact commit times go in the
  analysis-history table. Numbers unchanged.
