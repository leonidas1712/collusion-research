# Appendix tracker

Working list of everything promised to an appendix, so nothing gets lost before submission. Appendix letters are assigned at assembly; names follow `docs/report_plan_outline.md` §5. Status: **in paper** = text is in `report/paper.md`; **source ready** = numbers exist in a run folder but not yet written up; **pending** = analysis not finished.

Main-text "in passing" mentions are listed under **Main-text pointer** so the paper says it in one line and points here.

**Update (25 Oct, claude-4):** the final structure is **9 appendices, A–I**, per `private/appendix_plan.md` (F merged into E = "Detectors and Evaluation"). The skeleton for all nine is now in `report/paper.md`, each item slotted into its appendix; items still shown as **[TODO]** in `paper.md` are the unwritten analyses and tables. The per-row "Appendix" column below predates the merge; the live letters are: A Limitations and Dual-Use; B Experimental Pipeline; C Scenarios, an Example, and Model Choice; D Labels and Judges; E Detectors and Evaluation; F Second Target (gpt-oss); G Behaviour Screening; H Robustness and Diagnostics; I Prompts.

| # | Item | Appendix | Main-text pointer | Source | Status |
|---|------|----------|-------------------|--------|--------|
| 1 | Limitations list, dual-use reasoning | A. Limitations and Dual-Use | Discussion | `docs/report_plan_outline.md` §5, `docs/writeup_limitations.md` | draft ready (`report/appendix_drafts/A.md`); merge after render |
| 2 | Pipeline figure, stage table, replay fidelity | B. Pipeline and Reproducibility | §3.2 | `report/appendix_pipeline.md` | in paper |
| 3 | Eligibility rule (wrote a correct summary at some point); 11 Qwen exclusions; same set for Qwen; behaviour slice 304→226 vs scored 241 | B. Pipeline (stage 3) | §4.1, Table 1 caption | `runs/20261025-2143-e05-ever-correct-summary-audit-a9bf`, `runs/20261025-2140-e05-behaviour-exclusions-audit` | in paper |
| 4 | Example trajectories (one give-in, one held) | C. Example Trajectories | §3.1 / Fig 1 | viewer reading lists | TODO |
| 5 | Scenario table, incident grounding, per-scenario counts | C. Scenarios/Example/Model | §3.1 | `SCENARIO_SPECS.md`, Table 1 CSV | counts in paper; new columns drafted (`report/appendix_drafts/C.md`) |
| 6 | Model choice (candidates tried, why Qwen3-32B) | C. Scenarios/Example/Model | §3.1 | `docs/scenario_guidelines.md`, `EXPERIMENT_LOG.md` | draft ready (`report/appendix_drafts/C.md`); candidate counts to confirm |
| 7 | Full monitor grid (18 setups), Luna, decision models defined, prompts, costs | Monitor setups | §3.4 | `runs/20261025-0147-e06-monitor-main`, `experiments/E06-monitors/PROMPTS.md` | TODO |
| 8 | Eventual label: learning curve, per-layer, branching | H. Robustness and Diagnostics | §4.2 | `runs/20261025-1456-e05-all-data-main`, branching run | prose drafted (`report/appendix_drafts/H.md`); codex builds per-layer figure |
| 9 | Near-term robustness: labels B/C, per-layer, scenario-mean, per-scenario | Near-term robustness | §4.3 | `runs/20261025-1456-e05-all-data-main/report.md` | TODO |
| 10 | Pooled CV and fold mixing | Pooled CV | §3.5 | same | TODO |
| 11 | Pressure-probe check (first batch, layer 32) | Pressure vs outcome | §4.3 (in paper) | `runs/20261025-0800-e05-explore-trajectories-pressure` | main text done; appendix TODO |
| 12 | Error overlap, score correlations, alarms at 5% false alarms, peer-text sway | Errors and alarms | §4.5 (in paper) | `runs/20261025-1504-e06-appendix-errors` | main text done; appendix TODO |
| 13 | Behaviour screening (rule strength, tactics, own stake, thinking, peers), reporting per `docs/pressure_reporting_practices.md` (Wilson CIs, coverage grid) | Behaviour screening | §4.1 | E01 behaviour summaries | TODO |
| 14 | Judge validation: deliberate/accidental vs author hand labels 36/40, κ 0.79 | Behaviour screening | §3.1 | hand-label run | TODO |
| 15 | **Leak route:** first channel leaks via `send_message` vs auto-posted end-of-turn reply (Qwen 50 vs 48; gpt-oss ~1 vs ~124) | Behaviour screening or Second target | §3.1 one line: the end-of-turn reply is posted to the channel | `runs/20261025-2157-e05-reasoning-route-audit` | source ready (rerun on canonical gpt-oss) |
| 16 | **Addressee check:** Jev judged 51/51 Qwen, 122/132 gpt-oss leak replies written to the peer; base rate 96.9% / 90.3% of all end-of-turn replies; author spot check of Jev's 10 misses: 9 to peer, 1 unclear (not blind) | same as 15 | one sentence next to 15 | `runs/20261025-2202-e06-addressee-audit` | source ready (canonical rerun pending) |
| 17 | gpt-oss deliberate/accidental judge labels | Second target | §4.6 | see #26 | done (see #26) |
| 18 | Second target: tactic development, selection gate, blunt-pressure failure (gpt-oss 0/27, Gemma 1/35), Gemma file-only, scaled collection (128/300 channel, controls 0/60) | Second target | §3.6 / §4.6 | `docs/second_target_*.md`, `runs/20261025-2212-e03-gpt-oss-full-collection` | source ready |
| 19 | gpt-oss rule amendments: public-only cutoff (reasoning mentions not a leak; inclusive cutoff would drop 53 held steps), eligibility rule | F. Second Target | §3.6 | `docs/confirmatory_plan.md` Addendum 6 | in paper (F) |
| 20 | gpt-oss replay fidelity (+ provider quantization unknown caveat) | F. Second Target | §3.6 | replay run | pending (slot in F, replay-works branch) |
| 21 | gpt-oss pre-ask placebo split; family 200114 (no post-ask window) | Second target | none | replay analysis | pending |
| 22 | gpt-oss probe + monitors (incl. + reasoning level) | Second target | §4.6 | replay analysis | pending |
| 23 | Reasoning-token probe (optional; else Future Work) | Second target or Future Work | Future Work | none | optional |
| 24 | Exposure positive control (AUROC 1.000) | Methods details | §3.3 (in paper) | E05 report | main text done |
| 25 | Prompts (peer, target, monitor) | Prompts | Appendix A | experiments/ | TODO |
| 26 | **gpt-oss disclosure-kind judge** (frozen Qwen question, Luna Decisions): 198/200 deliberate, 0 accidental, 2 uncertain. First public emission is write_file in 196/200 (final reply 4); among channel-positive episodes the first channel leak is the end-of-turn reply in 127/128 (send_message 1) | Second target | §4.6 | `runs/20261025-2228-e03-gpt-oss-disclosure-kind-judge` | source ready |
| 27 | **gpt-oss replay rendering check:** does our prompt rendering reproduce the provider's tokens? Gates #20–22. Rendering gate numbers (AkashML 68%→98.9%; DekaLLM ~4.5% unresolved) now in F | F. Second Target | §3.6 | `runs/20261025-2236-e02-gpt-oss-rendering-gate` | in paper (F); replay still on hold over the mismatch |
