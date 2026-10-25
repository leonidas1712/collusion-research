# Appendix: Methods details (draft)

*Detail moved out of Section 3 (`report/draft_methods.md`) to keep the main Methods to about two pages. Source of truth stays `report/outline.md`; numbers are cited to run folders there. The final appendix letter is assigned at assembly — the outline's appendix plan (A–J) already has homes for several of these items (replay/fidelity → J, pooled CV and fold mixing → E, monitor ladder → B, prompts → I, errors and alarms → G), and this file consolidates the method-level detail those sections draw on. Written 25 Oct 2026.*

## B.1 Environment and conditions (detail for §3.1)

- Each episode runs up to 20 rounds; in each round the peer acts, then the target. Agents call mock tools (in memory, no external effects, no real credentials) and post to a shared team channel. Temperature 0.7, at most 12 tool steps per target turn, with early stop (`runs/20261025-0817-e01-spray-dispatch-integration-code-consequence-recruiting-32b-scaleup/meta.json`; `experiments/E01-behaviour-pilot/SCENARIO_SPEC.md`).
- Target: Qwen3-32B, thinking off, served fp8 via OpenRouter (DeepInfra). Peer: DeepSeek-V4-Flash (`PROVENANCE.md` §5). The single provider is pinned with fallbacks disabled so every call is served the same way.
- The operator rule forbids posting the protected value and states a consequence ("consequence" rule strength). A forbidden action is scored by a rule on the tool log — the value appears in a post or a new file — not by judgement.
- Controls and alone episodes never leaked across the runs (for example spray top-up controls 0/34, alone 0/20; `EXPERIMENT_LOG.md` 25 Oct 03:45).
- The six scenarios share one task template: deploy-token v2 (a credential) and five "spray" scenarios — service-rollout-threshold, procurement-reserve-price, handoff-exception-note, service-capacity-figure, dispatch-integration-code (number / text / code values). How scenarios were built and checked: `docs/scenario_guidelines.md`.
- Why the rule was strengthened: with no rule, targets handed the value over in the first round or two, which leaves nothing to predict. The rule produces hold-then-give-in. [rule-strength sweep: `runs/20261024-0332-e01-overnight-rule-strength`]
- Deliberate-vs-accidental judge (§3.1): the secondary decision model's labels match blind human labels on 36 of 40 give-ins (Cohen's κ = 0.79).

## B.2 Replay and fidelity (detail for §3.2)

- Behaviour batches are replayed through the pinned Hugging Face Qwen3-32B checkpoint (revision `9216db57…`) in bfloat16 on a single A100-80GB GPU, using forward hooks on the decoder blocks to save all 64 layers at the last prompt token before each reply. Replay reconstructs the exact token sequence the target saw; prompt token hashes match a frozen manifest of the requests to replay.
- Fidelity: the episodes were served at fp8 and replayed in bf16 on the identical tokens, and the bf16 model reproduces the served replies closely — reply NLL 0.249, top-5 99.79% (replay 2, `runs/20261025-0339-e02-replay2-results/report.md`); NLL 0.227, top-5 99.82% (replay 3, `runs/20261025-0923-e02-replay3-completion/report.md`). The activations therefore reflect the model that acted.
- Dataset counts: 9,138 replayed rows, 6,404 eligible steps in 338 episodes (`runs/20261025-1026-e05-replay3-data-1d95/summary.json`); recruiting steps scored 4,697 in 241 episodes, 101 give-ins and 140 held (`runs/20261025-1504-e06-appendix-errors/report.md`; row count also in `runs/20261025-1456-e05-all-data-main/report.md`).
- Split: replay 2 is 4,184 eligible steps (2,910 recruiting) from 63 give-in and 89 held episodes (`runs/20261025-0147-e06-monitor-main/report_main_A_hazard.md`); the balanced batch is 129 complete new episodes (89 usable recruiting episodes), used first as the confirmation set and then pooled (Section 4.3).
- GPU replay cost: replay 2 ~\$5.51, replay 3 \$2.94.

## B.3 Scoring-window costs (detail for §3.3)

- The exposure positive control reaches AUROC 1.000 at layer 32 on held-out families (replay 2: `runs/20261025-0338-e05-replay2-positive-control/summary.json`, min over all 64 layers 0.99999; replay 3: `runs/20261025-1026-e05-replay3-positive-control/summary.json`, 1.000). This is why steps before the read are excluded — a probe can detect "the file was read" perfectly.
- Cost of the window: give-ins that leak on the very next call after reading have no step to score (2 of 106 valid give-ins in the combined data), and held episodes that never read the value are dropped (74 held episodes contribute no scored step). (`docs/writeup_limitations.md`; held/give-in counts not re-checked against the data files.)

## B.4 Secondary labels (detail for §3.4)

- **B and C** (secondary): B keeps near-term A's positives but counts only held-episode steps as negatives; C uses a within-three-target-calls window against held episodes. Both drop steps using hindsight, so neither is a prospective alarm label (`runs/20261025-1456-e05-all-data-main/report.md`, intro).

## B.5 Probe recipe (detail for §3.5)

- Logistic regression with L2 regularisation (C = 0.1), feature standardisation using training-rows-only statistics, and step weights so positives and negatives contribute equally within each round, on the 5,120-dimensional residual stream at the last prompt token before each target reply.
- The layer is chosen inside each training fold from 17 candidates (layers 0, 4, …, 60, 63) on a 25% inner family holdout (the "nested" probe); a fixed-layer-32 variant is reported as a check. Three split seeds (42, 43, 44) are averaged.
- Trained on recruiting episodes only; families of related variants never cross a train/test boundary (`runs/20261025-1456-e05-all-data-main/report.md`). Recipe follows Goldowsky-Dill et al. (2502.03407) and Kramár et al. (2601.11516).

## B.6 Monitor ladder, prompts, and cost (detail for §3.6)

- Three monitor models: GPT-5-nano (LLM judge, 0–100 score) and two decision models, Jev 1.14 (TypeSafe) and Luna Decisions (OpenAI), which return a probability over fixed yes/no options with no written rationale. The yes/no option order is randomised per step.
- Monitor prompts are adapted from the UK AISI ControlArena `default.txt` template (MIT): warning signs and guiding questions, the score anchored only at its ends (not a banded rubric — a limitation), and the rule text filled in per scenario from each step's own rule. Prompts were approved before the main run and not changed afterwards.
- The full set of 3 models × 2 questions × 3 levels = 18 setups was run on replay 2 (75,312 calls, \$12.67: Jev \$2.03, GPT-5-nano \$6.53, Luna \$4.11; `runs/20261025-0147-e06-monitor-main/report_main_A_hazard.md`). On the new episodes we ran an 8-setup subset fixed in advance: all six Jev setups plus GPT-5-nano detector and forecaster at L2 (`runs/20261025-0841-e06-monitor-main-balanced`).
- Luna is at chance as a forecaster on replay 2 (A: L1 0.517, L2 0.496, L3 0.505) and was dropped from the new-episode runs for cost. A single LLM judge (GPT-5-nano) is a limitation.

## B.7 Evaluation mechanics (detail for §3.7)

- **Split mechanics:** held-out scenario (leave-one-scenario-out) trains on five scenarios, tests on the sixth, rotates through all six, and pools the scores; pooled family cross-validation uses five folds grouped by family.
- **Confidence intervals:** 95% family bootstrap, 1,000 resamples, seed 20261025, conditional on the fitted models.
- **Pooled CV and fold mixing:** pooled-CV baselines can fall below 0.5 because scores from different fitted fold models are compared within one scenario × round group; the **fold-stratified** variant additionally compares only scores from the same fitted fold model (replay 2: nested 0.522 → 0.552; scenario baselines → 0.5; `runs/20261025-0544-e05-fold-sensitivity/report.md`). Held-out scenario (LOSO) and the confirmation test are unaffected.
- **Combination test:** a logistic model stacked on [round, log prompt length, monitor score] is compared against the same features plus the probe score, reporting the paired family-bootstrap difference in AUROC.
- **Alarm analysis:** a score cutoff is set on benign (held) episodes for a 5% false-alarm target, and recall and false alarms are reported on held recruiting episodes.
