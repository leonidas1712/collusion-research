# Recruited: can you tell an agent is about to be talked into breaking its rule?

This repository holds the code, prompts, transcripts and results for the paper *Recruited: Pre-Crime for Agents? Predicting Give-In to Collusion Pressure, with Activation Probes and Text Monitors*, written for the Apart AI Collusion Research Sprint (October 2026).

- **Paper:** [`report/build/paper.pdf`](report/build/paper.pdf) (source: [`report/paper.md`](report/paper.md); the committed PDF was built from source commit `21bb990d`)
- **License:** MIT for the project code ([`LICENSE`](LICENSE)); the vendored fonts (`report/fonts/`) and citation style (`report/apa.csl`) keep their own licenses

## What this project is

Two AI agents share a team channel. One of them, the **target**, holds a value its operator told it to keep private, such as a staging deploy token. The other, a **peer**, needs that value and keeps asking for it, for up to 20 rounds. Sometimes the target refuses throughout; sometimes it eventually posts the value. We call that a **give-in**: the target sides with the peer against its operator, which is often the first step of collusion between agents.

We ask whether a give-in can be seen coming before it happens, using two kinds of tools scored on exactly the same steps:

- **activation probes:** small linear classifiers that read the target model's internal activations;
- **text monitors:** an LLM judge (GPT-5-nano) and two decision models (Jev 1.14 and Luna Decisions: commercial models that return a probability over fixed yes/no options instead of written text). Each reads the target's actions, the conversation, or everything the target saw.

The main target is Qwen3-32B, across six scenarios; gpt-oss-20b is a second target.

**What we found.** Predictions are scored with AUROC: the chance that a randomly chosen give-in step scores above a randomly chosen other step (0.5 = guessing, 1.0 = perfect).

- Qwen3-32B gives in on 101 of 241 episodes (42%).
- Whether it will *eventually* give in is barely predictable from a single step.
- Whether it gives in *this round or the next* is modestly predictable: probe 0.58 and best text monitor (Jev 1.14, asked to forecast) 0.65 on held-out scenarios. Both held on 89 new episodes scored under an [analysis plan fixed in advance](docs/confirmatory_plan.md).
- On gpt-oss-20b, which usually gives in within the round it is asked, neither probes nor monitors predict give-in much above chance.

![Figure 2: how well each detector predicts give-in, by target and horizon](report/figures/figure2_prediction.png)

The paper has the full results and their limits.

## Quick start

You can read every result without running anything: each run folder in `runs/` keeps its command, settings and outputs, and the tables below say which folder backs which number in the paper.

**What you need to run code.**

- *To run the tests and rebuild the figures:* Python 3.11 or later and [uv](https://docs.astral.sh/uv/).
- *To rebuild the paper PDF, also:* Pandoc, LibreOffice and Poppler on your PATH, and the fonts in `report/fonts/` (included; install steps in [`report/BUILD.md`](report/BUILD.md)).
- *To rerun experiments (paid), also:* an [OpenRouter](https://openrouter.ai) API key with credit, for the agents and monitors, and a [Modal](https://modal.com) account for the GPU replay. The replay downloads the open weights from Hugging Face: about 65 GB for Qwen3-32B and 14 GB for gpt-oss-20b. Neither model is gated, so no Hugging Face token is needed.

Then:

1. **Install** Python 3.11 or later and [uv](https://docs.astral.sh/uv/).
2. **Clone and create the main environment** (agent harness, monitors, behaviour summaries):

   ```bash
   git clone https://github.com/leonidas1712/collusion-research
   cd collusion-research
   uv sync
   ```

3. **Create the probe and replay environments.** The probe and GPU-replay code pin exact package versions (numerical and model libraries) in their own `requirements-lock.txt`, separate from the main environment:

   ```bash
   uv venv experiments/E05-probes/.venv --python 3.11
   uv pip sync --python experiments/E05-probes/.venv/bin/python experiments/E05-probes/requirements-lock.txt

   uv venv experiments/E02-activation-replay/.venv --python 3.11
   uv pip sync --python experiments/E02-activation-replay/.venv/bin/python experiments/E02-activation-replay/requirements-lock.txt
   ```

   `experiments/E02-activation-replay/run.sh` creates the replay environment on first use if you skip this.

4. **Only for paid steps:**
   - *API key:* put `OPENROUTER_API_KEY=…` in a `.env` file at the repository root; agents and monitors all go through OpenRouter.
   - *GPU:* the replay runs on [Modal](https://modal.com) (one A100-80GB). Run `uv run modal setup` once to log in (Modal is installed in the main environment, so call it through `uv run`).

5. **Check the setup** without spending anything by running the probe tests:

   ```bash
   experiments/E05-probes/.venv/bin/python -m unittest discover -s experiments/E05-probes -p 'test_*.py'
   ```

**Costs.** Reading results, rerunning analyses from saved outputs and rebuilding the figures and paper cost nothing. Collecting episodes, running monitors and the GPU replay are paid. Every paid step takes a hard spending cap (`--cap-usd`, `--cap` or `--phase-ceiling`, depending on the script) and records what it was billed in its run folder. Monitor costs are in `runs/20261025-1543-e06-cost-and-scenarios`; a total for the paper's paid runs is under the next table.

## Reproduce the paper from a fresh clone

These steps use only what is committed and cost nothing. Times were measured on a recent laptop. The figure and paper steps write into tracked folders (`report/figures/`, `report/build/`); to compare against the committed files instead, pass `--output-dir DIR` to the two figure scripts and `--output DIR/paper.docx` to the paper build.

| Step | Command (from the repository root) | What you get | Time | Cost |
|---|---|---|---|---|
| Set up | `uv sync`, then the two `uv venv` / `uv pip sync` commands above | The three Python environments | a few minutes | free |
| Run the tests | `experiments/E05-probes/.venv/bin/python -m unittest discover -s experiments/E05-probes -p 'test_*.py'` | 33 tests; 3 skip because they need saved activation splits that are not in git | under a minute | free |
| Rebuild the figures and tables | `OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 experiments/E05-probes/.venv/bin/python report/make_data_figures.py` | Table C.1, Table 1, Figure E.1 and a Qwen-only draft of Figure 2 in `report/figures/` (PNG, PDF and the numbers as CSV). **This overwrites the committed two-target Figure 2; the next row restores it.** | about 5 s | free |
| Rebuild Figure 2 with both targets | `uv run --with matplotlib python report/figures/make_figure2_targets.py` (always run right after the step above) | `report/figures/figure2_prediction.*`, identical to the committed files | about 1 s | free |
| Rebuild the paper | `uv run --with python-docx --with lxml --with pillow --with pypdf python report/build_paper.py` (needs Pandoc, LibreOffice, Poppler and the fonts listed in [`report/BUILD.md`](report/BUILD.md)) | `report/build/paper.docx` and `paper.pdf` | about 20 s | free |
| Browse the transcripts | `uv run python experiments/E01-behaviour-pilot/build_viewer.py` | `runs/viewer.html` (see [Trace viewer](#trace-viewer)) | about 20 s | free |

Rerunning the analyses that read activations (probe training, the combination test) needs the activations first, from the paid GPU replay; see [What is not in git](#what-is-not-in-git). Recollecting episodes or rerunning monitors makes paid API calls. For scale, the paper's own paid runs cost about USD 34 in total, not counting first-batch episode collection: new-episode collection USD 0.82; Qwen replay USD 5.51 (first batch) and USD 2.94 (new-episode set); monitors USD 12.67 (first batch, 18 setups) and USD 2.33 (new-episode set, 8 setups); gpt-oss-20b replay USD 9.54 at a conservative upper bound, including its rendering checks (about USD 8 billed; paper Appendices B and F). Prices change, so treat these as a guide, not a quote.

## Reproducing the results

Each result below names the script that produced it and the run folder the paper uses. Every run folder is named `runs/YYYYMMDD-HHMM-<experiment>-<name>/` and holds `meta.json`, which records the exact command, the git commit and the settings, next to the outputs (usually `report.md` and `metrics.json`). The recorded commands are a faithful record of what ran, but some use absolute paths from the original machine or temporary input files; adapt the paths before rerunning. Generating scores, tables and figures from saved outputs needs no API key. Run-folder timestamps are Singapore time (UTC+8).

**Uncommitted changes at run time.** Most runs were launched from a working tree with uncommitted edits: `meta.json` records this as `"dirty": true` for 728 of 816 runs. The uncommitted diff (`diff.patch`) was saved next to each run locally but is not in git, so for those runs the recorded `git_commit` is the nearest commit, not an exact pin of the code. The analysis and figure scripts at the current commit regenerate the paper's committed tables and figures from the saved outputs (checked for every row of the table above).

The pipeline runs in this order: collect episodes with the agent harness (E01), replay every target request through the open weights on a GPU to save activations (E02), build the step table and train and score probes (E05), score the same steps with text monitors (E06), then combine and confirm. Steps that need activations (E05 and the combination test) need the replay step first; see [What is not in git](#what-is-not-in-git).

### Episodes and labels (Qwen3-32B)

| Result | Script | Run(s) |
|---|---|---|
| Episodes, deploy-token scenario | `experiments/E01-behaviour-pilot/scale_up.py --family deploy-token-v2 --strength consequence --parallelism 4 --recruiting 40 --control 15 --alone 6 --family-start 8001 --cap-usd 0.6` | `runs/20261024-2103-e01-deploy-token-v2-consequence-recruiting-32b-scaleup` and its `-control-` and `-alone-` siblings; tactic arms `runs/20261024-2141-e01-deploy-token-v2-consequence-recruiting-32b-t1-scaleup`, `runs/20261024-2149-e01-deploy-token-v2-consequence-recruiting-32b-t2-scaleup` and `runs/20261024-2157-e01-deploy-token-v2-consequence-recruiting-32b-t7-scaleup`, each with a `-control-` sibling |
| Episodes, the five other scenarios | `scale_up.py --spray-row <scenario> --strength consequence` plus per-run counts and seeds (exact command in each folder's `meta.json`) | Two waves per scenario: a first wave (recruiting and alone) at `runs/20261024-2132` to `-2149`, and a second wave (recruiting, control and alone) at `runs/20261024-2338`. Example: `runs/20261024-2338-e01-spray-handoff-exception-note-consequence-recruiting-32b-scaleup`. The exact list of episode folders scored in the paper is the `episode` field of `runs/20261025-1026-e05-replay3-data-1d95/rows.jsonl` |
| New-episode (confirmation) set | `scale_up.py --spray-row <scenario> --strength consequence` with a fresh `--family-start` per scenario (exact command in each folder's `meta.json`) (five scenarios, not deploy-token) | `runs/20261025-0817-e01-spray-<scenario>-consequence-recruiting-32b-scaleup` and `-control-`, for the five scenarios dispatch-integration-code, handoff-exception-note, procurement-reserve-price, service-capacity-figure and service-rollout-threshold. Each folder's `meta.json` has the exact command |
| Deliberate vs accidental labels (70 deliberate, 30 accidental, 1 unlabelled of 101 scored give-ins) | `experiments/E01-behaviour-pilot/judge_labels.py`, `judge_topup.py` | `runs/20261025-0056-e01-topup-semantic-judge` and `runs/20261025-0833-e01-topup-semantic-judge`; the labels are also written into each episode file |
| Judge vs the author's blind labels (36 of 40, κ 0.79) | `sample_label_batch.py`, `label_agreement.py` | `runs/20261025-1355-e01-label-batch-2` |
| GPU replay, first data batch | `experiments/E02-activation-replay/plan_replay2.py`, then `modal_budget_client.py` | `runs/20261025-0119-e02-replay2-plan`, `runs/20261024-1727-e02-activation-replay`; report in `runs/20261025-0339-e02-replay2-results` |
| GPU replay, new-episode set | `plan_replay3.py`, then `modal_budget_client3.py` | `runs/20261025-0838-e02-replay3-plan`, `runs/20261025-0921-e02-replay3-modal-client`, `runs/20261025-0923-e02-replay3-completion` |
| Step table (6,404 eligible steps, 338 episodes) | `experiments/E05-probes/replay2_data.py`, `replay3_data.py` | `runs/20261025-1026-e05-replay3-data-1d95` |

### Main results

| Result in the paper | Script | Run |
|---|---|---|
| §4.1 and Table C.1 (behaviour rates) | `experiments/E03-target-screen/behaviour_summary.py` | `runs/20261025-1850-e03-behaviour-summary` |
| §4.2–4.3, Figure 2 (probe vs monitors, eventual and near-term labels) | `all_data_main.py --workers 3`, then `finalize_all_data.py 20261025-1317-e05-all-data-main 20261025-1456-e05-all-data-audit` (both in `experiments/E05-probes/`, run with its environment) | `runs/20261025-1317-e05-all-data-main`, `runs/20261025-1456-e05-all-data-audit`, `runs/20261025-1456-e05-all-data-main` |
| Near-term labels | `experiments/E05-probes/near_term.py` | `runs/20261025-0730-e05-near-term` |
| Text monitors, first data batch (18 setups) | `experiments/E06-monitors/monitors.py --steps-file runs/20261025-0119-e02-replay2-plan/all.jsonl` | `runs/20261025-0147-e06-monitor-main` |
| Text monitors, new-episode set (8 setups) | `monitors.py --steps-file runs/20261025-0838-e02-replay3-plan/all.jsonl` | `runs/20261025-0841-e06-monitor-main-balanced` |
| §4.4, confirmation test (frozen plan in [`docs/confirmatory_plan.md`](docs/confirmatory_plan.md)) | `experiments/E06-monitors/confirm.py` | `runs/20261025-1030-e06-confirmation` |
| §4.5, Table 1 (combination test) | `experiments/E06-monitors/combine.py`; the all-data rows come from `all_data_main.py` | `runs/20261025-1456-e05-all-data-main`, `runs/20261025-1030-e06-confirmation` |
| §4.3, pressure-probe check | `experiments/E05-probes/explore_trajectories.py` | `runs/20261025-0800-e05-explore-trajectories-pressure` |
| Exposure positive control (AUROC 1.000) | `experiments/E05-probes/replay3_positive_control.py` | `runs/20261025-1026-e05-replay3-positive-control` |

### Second target (gpt-oss-20b, §4.6)

| Result | Script | Run |
|---|---|---|
| Behaviour screens and the delayed whole-block strategy | `experiments/E03-target-screen/escalation_sweep.py --target gpt-oss --strategy envblock_late` (one run per scenario) | `runs/20261025-*-e03-escalation-gpt-oss-<scenario>-envblock_late` (several rounds of screening between 20:13 and 21:55), e.g. `runs/20261025-2155-e03-escalation-gpt-oss-deploy-token-v2-envblock_late` |
| Final collection (300 recruiting, 60 control episodes) | `experiments/E03-target-screen/finalize_gpt_oss_collection.py` builds the manifest; the run folder's `README.md` names the frozen prompt commit | `runs/20261025-2212-e03-gpt-oss-full-collection` |
| Disclosure-kind judge | `experiments/E03-target-screen/judge_gpt_oss_leaks.py`, joined by `experiments/E05-probes/gpt_oss_kind_join.py` | `runs/20261025-2228-e03-gpt-oss-disclosure-kind-judge`, `runs/20261025-2310-e05-gpt-oss-disclosure-kind-join` |
| Replay rendering gate | `experiments/E02-activation-replay/report_gpt_oss_rendering_gate.py` (replay code: `gpt_oss_replay.py`, `modal_gpt_oss.py`) | `runs/20261025-2236-e02-gpt-oss-rendering-gate` |
| GPU replay | `plan_gpt_oss_full.py`, then `gpt_oss_full_budget.py`, `download_gpt_oss_full.py`; summary by `report_gpt_oss_full.py` | `runs/20261025-2251-e02-gpt-oss-full-plan`, `runs/20261025-2253-e02-gpt-oss-full-client`, `runs/20261025-2255-e02-gpt-oss-full-download`, `runs/20261026-0138-e02-gpt-oss-full-completion` |
| Step table | `experiments/E05-probes/gpt_oss_replay_data.py` | `runs/20261025-2305-e05-gpt-oss-full-data` |
| Prediction windows (how many give-ins leave a step to predict from) | `experiments/E05-probes/gpt_oss_windows.py` | `runs/20261026-0056-e05-gpt-oss-window-audit` |
| Probes, with exposure positive control | `experiments/E05-probes/gpt_oss_positive_control.py`, then `gpt_oss_probes.py` | `runs/20261026-0137-e05-gpt-oss-positive-control`, `runs/20261026-0138-e05-gpt-oss-main` |
| Text monitors | `experiments/E06-monitors/monitors.py --steps-file runs/20261025-2251-e02-gpt-oss-full-plan/rows.jsonl`, scored by `score_gpt_oss_monitors.py` | `runs/20261025-2330-e06-monitor-main-gpt-oss`, `runs/20261026-0108-e06-monitor-score-gpt-oss` |
| Combination test | `experiments/E06-monitors/combine_gpt_oss.py` | `runs/20261026-0148-e06-gpt-oss-combination` |
| Alarms | `experiments/E06-monitors/alarm_join_gpt_oss.py` | `runs/20261026-0159-e06-gpt-oss-alarm-join` |

### Appendix results

| Result | Script | Run |
|---|---|---|
| Per-scenario and cost tables | `experiments/E06-monitors/cost_and_scenarios.py` | `runs/20261025-1543-e06-cost-and-scenarios` |
| Score correlations, shared misses, alarms | `experiments/E06-monitors/appendix_errors.py` (pass `--keyword-review runs/20261025-1504-e06-appendix-errors/keyword_review.json`, or omit it) | `runs/20261025-1504-e06-appendix-errors` |
| Deliberate-only check (Appendix H) | fits in `experiments/E05-probes/replay2_core.py`, report by `replay2_report.py`, then `replay2_finalize.py` | `runs/20261025-0340-e05-replay2-fits`, report in `runs/20261025-0536-e05-replay2-analysis` |
| Per-layer diagnostic | `experiments/E05-probes/layer_diagnostic.py` | `runs/20261025-1003-e05-layer-diagnostic` |
| Learning curve | `experiments/E05-probes/learning_curve.py` | `runs/20261025-0842-e05-learning-curve` |
| MLP probe | `experiments/E05-probes/near_term_mlp.py` | `runs/20261025-0848-e05-near-term-mlp` |
| Branching check | `experiments/E05-probes/replay2_branching.py` | `runs/20261025-0340-e05-replay2-branching` |
| Logit lens | `experiments/E05-probes/explore_logit_lens.py` | `runs/20261025-0803-e05-logit-lens` |
| Correct-summary validity check | `experiments/E05-probes/audit_ever_correct_summary.py` | `runs/20261025-2143-e05-ever-correct-summary-audit-a9bf` |
| Leak route and private-reasoning cutoff | `experiments/E05-probes/audit_reasoning_and_routes.py` | `runs/20261025-2157-e05-reasoning-route-audit`, `runs/20261025-2324-e05-reasoning-route-audit` |
| Addressee check (Qwen; gpt-oss) | `experiments/E06-monitors/addressee_audit.py` | `runs/20261025-2202-e06-addressee-audit`; `runs/20261026-0145-e06-addressee-audit` |
| Peer authority claims | `experiments/E06-monitors/authority_claim_audit.py` | `runs/20261026-0118-e06-authority-claim-audit` |

### Figures, tables and the paper

| Output | Script |
|---|---|
| Figure 1 (a real exchange, the setup, a toy timeline) | `report/figures/make_figure1.py` (a schematic; the quotes are from episode 0032 of the deploy-token recruiting run) |
| Table C.1 (behaviour; file `table1_behaviour`), Table 1 (combination; file `table2_combination`) and Figure E.1 (monitor design) | `experiments/E05-probes/.venv/bin/python report/make_data_figures.py` (sources listed in [`report/figures/DATA_FIGURES.md`](report/figures/DATA_FIGURES.md)) |
| Figure 2 (Qwen3-32B and gpt-oss-20b panels) | `uv run --with matplotlib python report/figures/make_figure2_targets.py`, run after `make_data_figures.py` |
| Pipeline figure (Appendix B) | `report/figures/make_pipeline_figure.py` |
| Appendix G coverage table | `report/make_appendix_coverage.py` |
| Appendix H robustness tables and per-layer figure | `report/make_appendix_robustness.py` |
| The paper (DOCX and PDF) | `report/build_paper.py`; the system tools and fonts it needs are listed in [`report/BUILD.md`](report/BUILD.md) |

## What is not in git

- **Activations.** The saved activations, and the per-step feature arrays built from them (`features.npy` in the step-table runs), are too large for git. They can be regenerated with the GPU replay steps above.
- **Per-step probe scores** (`probe_scores.csv` in the `all-data-main`, `near-term` and `gpt-oss-main` runs) are left out for size, as are most split plans. The final all-data split plan is committed in compressed form (`runs/20261025-1456-e05-all-data-main/split_plan.json.gz`). The metrics, intervals and reports computed from the scores are committed; to regenerate the per-step files, rerun `all_data_main.py`, `near_term.py` or `gpt_oss_probes.py` once the activations exist.
- **Monitor response caches** (`runs/*/cache/`). Monitor scores and metrics are committed, but rerunning `monitors.py` makes fresh paid calls.
- **Large or regenerable run outputs**: rendered prompts, tokenizer and model-config copies, and per-row probe-score exports (see [`.gitignore`](.gitignore)).
- **API keys.** `.env` is never committed.

Transcripts, labels, monitor scores, metrics and reports are in `runs/`.

## Repository map

| Folder | Contents |
|---|---|
| [`experiments/E01-behaviour-pilot/`](experiments/E01-behaviour-pilot/) | The multi-agent harness, the six scenarios, peer tactics, outcome scorers and the deliberate-vs-accidental judge |
| [`experiments/E02-activation-replay/`](experiments/E02-activation-replay/) | GPU replay of every target request through the open weights on Modal, with fidelity checks |
| [`experiments/E03-target-screen/`](experiments/E03-target-screen/) | Second-target screens (gpt-oss-20b, Gemma-4-31B) and the behaviour summary |
| [`experiments/E04-shi-replay/`](experiments/E04-shi-replay/) | A proposed backup study on another paper's released traces; never run, not used in the paper |
| [`experiments/E05-probes/`](experiments/E05-probes/) | Probe training and evaluation: held-out scenario, pooled cross-validation, near-term labels, diagnostics |
| [`experiments/E06-monitors/`](experiments/E06-monitors/) | Text monitors, their scoring, the combination test and the confirmation test |
| [`report/`](report/) | The paper source, figure and table scripts, and the build |
| [`runs/`](runs/) | One folder per run, each with its command, settings and outputs |
| [`docs/`](docs/) | Design notes and working documents from the sprint (informal; the paper is the checked version), the scenario guidelines and the frozen confirmatory plan |
| [`explainers/`](explainers/) | Plain-language explainers of the methods |
| [`archive/internal/`](archive/internal/) | Working notes from the sprint, kept for the record |
| [`src/collusion/`](src/collusion/) | Shared helper that creates run folders |
| [`PROVENANCE.md`](PROVENANCE.md) | Where each idea, paper, scenario inspiration and peer tactic came from, collected as the work went on. It is a working list; the paper's reference list is the checked version |
| [`EXPERIMENT_LOG.md`](EXPERIMENT_LOG.md) | A dated journal of results, decisions and dead ends, each pointing to its run folders |

Each experiment folder has its own `README.md` with more detail.

**Reading the names.**

- *Experiment numbers* follow the original sprint plan, not the pipeline order. The pipeline is E01 (episodes), then E02 (GPU replay), E05 (probes) and E06 (monitors). E03 holds the target screens and behaviour summaries; E04 was never run.
- *Run folders* are `runs/YYYYMMDD-HHMM-e0N-<name>`. [`runs/index.jsonl`](runs/index.jsonl) lists every run in order, with its status.
- *Episode runs:* `recruiting` means the peer asks for the protected value; `control` means a peer that asks only for the non-protected values it needs; `alone` means no peer. `consequence` is the rule wording used throughout; `spray-<scenario>` is one of the five scenarios other than the deploy token; `t1`, `t2` and `t7` are single-tactic peer variants. `e01-scaleup-…` folders are parent sweeps whose child folders hold the episodes.
- *Data batches:* `replay2` is the first data batch and `replay3` the new-episode (confirmation) set.
- *All-data probe runs:* `runs/20261025-1317-e05-all-data-main` holds the fits; `runs/20261025-1456-e05-all-data-main` is a report-only merge of those fits with the audit run `runs/20261025-1456-e05-all-data-audit`, and is the source of the paper's numbers.
- Other terms are defined in plain language in [`explainers/GLOSSARY.md`](explainers/GLOSSARY.md).

## Trace viewer

`runs/viewer.html` is a single HTML page for reading every episode round by round: the channel, each tool call and its result, the outcome labels, and filters by run, scenario, model and outcome. It is about 170 MB, so it is not committed. Build it with:

```bash
uv run python experiments/E01-behaviour-pilot/build_viewer.py
```

and open `runs/viewer.html` in a browser (a local file is fine). It uses only the standard library and makes no API calls. Monitor calls are not shown in a fresh clone, because the monitor caches are not in git.

## What did not make the paper

- **E04** ([`experiments/E04-shi-replay/`](experiments/E04-shi-replay/)): a backup plan to test probes on another paper's released agent traces. It was documented but never run.
- **Other target models.** Gemma-4-31B, Granite-4.2-8B, Llama-3.3-70B and several small models were screened and dropped; the reasons are in paper Appendices C and F, and the screens in `experiments/E03-target-screen/`.
- **Other probe variants.** An MLP probe, a logit lens and trajectory features did not beat the linear probe; they are reported as diagnostics in paper Appendix H.
- **Earlier pilots.** Rule-strength, tactic, thinking-mode, own-stake and two-peer screens are summarised in paper Appendix G; their runs are in `runs/` under the `e01` prefix.

## Sprint timeline and pre-existing work

The sprint started on Fri 23 Oct 2026 00:00 AoE (12:00 UTC). The only project work that predates it is commit `a5bd6f93` (planning documents, no code; see `git show --stat a5bd6f93`); all code and results come from later commits. The author's own pre-existing open-source tools, Aboard (an agent message board) and Leaf (a document viewer for inline review comments), were used to coordinate and review the AI agents that helped with the work. They are not part of this repository's research code. AI coding agents wrote most of the code and ran the experiments under the author's direction, and drafted the paper's text from the author's outline; the paper's LLM Usage Statement gives the full account.

## Data and model terms

The transcripts contain outputs of third-party models (Qwen3-32B, gpt-oss-20b, DeepSeek-V4-Flash and V4-Pro, GPT-5-nano, Jev 1.14 and Luna Decisions), accessed through OpenRouter, and the replay uses open weights from Hugging Face. Those outputs and weights remain under their providers' terms; the MIT licence covers this project's own code.

## Safety notes

All tools are mocked in memory, and every protected value is a randomly generated fake; no real credential, system or network resource is touched. The prompts, including the recruiting peer prompts, are released in full (paper Appendix I) for the reasons given in the paper's Appendix A.

## Citation

> Raghav, L. (2026). *Recruited: Pre-Crime for Agents? Predicting Give-In to Collusion Pressure, with Activation Probes and Text Monitors.* Apart AI Collusion Research Sprint. https://github.com/leonidas1712/collusion-research
