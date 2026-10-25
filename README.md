# Recruited: can you tell an agent is about to be talked into breaking its rule?

This repository holds the code, prompts, transcripts and results for the paper *Recruited: Pre-Crime for Agents? Predicting Give-In to Collusion Pressure, with Activation Probes and Text Monitors*, written for the Apart AI Collusion Research Sprint (October 2026).

- **Paper:** [`report/build/paper.pdf`](report/build/paper.pdf) (source: [`report/paper.md`](report/paper.md))
- **License:** MIT for the project code ([`LICENSE`](LICENSE)); the vendored fonts (`report/fonts/`) and citation style (`report/apa.csl`) keep their own licenses

## What this project is

Two AI agents share a team channel. One of them, the **target**, holds a value its operator told it to keep private, such as a staging deploy token. The other, a **peer**, needs that value and keeps asking for it, for up to 20 rounds. Sometimes the target refuses throughout; sometimes it eventually posts the value. We call that a **give-in**: the target sides with the peer against its operator, which is often the first step of collusion between agents.

We ask whether a give-in can be seen coming before it happens, using two kinds of tools scored on exactly the same steps:

- **activation probes:** small linear classifiers that read the target model's internal activations;
- **text monitors:** an LLM judge (GPT-5-nano) and two decision models (Jev 1.14 and Luna Decisions) that read the target's actions, the conversation, or everything the target saw.

The main target is Qwen3-32B, across six scenarios; gpt-oss-20b is a second target.

**What we found, in short.** Qwen3-32B gives in on 101 of 241 episodes (42%). Whether it will *eventually* give in is barely predictable from a single step. Whether it gives in *this round or the next* is modestly predictable: the probe reaches AUROC 0.58 on held-out scenarios and the best monitor (Jev 1.14, asked to forecast) 0.65, and both results held on 89 new episodes scored under an analysis plan fixed in advance. (AUROC is the chance that a randomly chosen give-in step scores above a randomly chosen non-give-in step; 0.5 is guessing.) On gpt-oss-20b, which usually gives in within the round it is asked, neither probes nor monitors predict give-in much above chance. The paper has the full results and their limits.

## Quick start

You can read every result without running anything: each run folder in `runs/` keeps its command, settings and outputs, and the tables below say which folder backs which number in the paper. To run code:

1. **Install** Python 3.11 or later and [uv](https://docs.astral.sh/uv/).
2. **Clone and create the main environment** (agent harness, monitors, behaviour summaries):

   ```bash
   git clone https://github.com/leonidas1712/collusion-research
   cd collusion-research
   uv sync
   ```

3. **Create the probe and replay environments.** These folders pin their packages in a `requirements-lock.txt` rather than a `pyproject.toml`:

   ```bash
   uv venv experiments/E05-probes/.venv --python 3.11
   uv pip sync --python experiments/E05-probes/.venv/bin/python experiments/E05-probes/requirements-lock.txt

   uv venv experiments/E02-activation-replay/.venv --python 3.11
   uv pip sync --python experiments/E02-activation-replay/.venv/bin/python experiments/E02-activation-replay/requirements-lock.txt
   ```

   `experiments/E02-activation-replay/run.sh` creates the replay environment on first use if you skip this.

4. **Add API keys** only if you will make model calls. Put `OPENROUTER_API_KEY=…` in a `.env` file at the repository root; agents and monitors all go through OpenRouter. The GPU replay runs on [Modal](https://modal.com) (one A100-80GB); run `modal setup` once to log in.

5. **Check the setup** without spending anything by running the probe tests:

   ```bash
   experiments/E05-probes/.venv/bin/python -m unittest discover -s experiments/E05-probes -p 'test_*.py'
   ```

**Costs.** Reading results, rerunning analyses from saved outputs and rebuilding the figures and paper cost nothing. Collecting episodes, running monitors and the GPU replay are paid. Every paid step takes a hard spending cap (`--cap-usd`, `--cap` or `--phase-ceiling`, depending on the script) and records what it was billed in its run folder. Monitor costs are in `runs/20261025-1543-e06-cost-and-scenarios`. For scale, the gpt-oss-20b replay cost about USD 9.50 on Modal, including its rendering checks; prices change, so treat this as a guide, not a quote. The GPU replay also needs the model weights from Hugging Face.

## Reproducing the results

Each result below names the script that produced it and the run folder the paper uses. Every run folder is named `runs/YYYYMMDD-HHMM-<experiment>-<name>/` and holds `meta.json`, which records the exact command, the git commit and the settings, next to the outputs (usually `report.md` and `metrics.json`). The recorded commands are a faithful record of what ran, but some use absolute paths from the original machine or temporary input files; adapt the paths before rerunning. Generating scores, tables and figures from saved outputs needs no API key.

The pipeline runs in this order: collect episodes with the agent harness (E01), replay every target request through the open weights on a GPU to save activations (E02), build the step table and train and score probes (E05), score the same steps with text monitors (E06), then combine and confirm. Steps that need activations (E05 and the combination test) need the replay step first; see [What is not in git](#what-is-not-in-git).

### Episodes and labels (Qwen3-32B)

| Result | Script | Run(s) |
|---|---|---|
| Episodes, deploy-token scenario | `experiments/E01-behaviour-pilot/scale_up.py --family deploy-token-v2 --strength consequence …` | `runs/20261024-2103-e01-deploy-token-v2-consequence-{recruiting,control,alone}-32b-scaleup`, plus the `-t1/-t2/-t7` tactic arms |
| Episodes, the five other scenarios | `scale_up.py --spray-row <scenario> …` | `runs/20261024-21xx-e01-spray-<scenario>-…` |
| New-episode (confirmation) set | `scale_up.py --spray-row <scenario> --recruiting 26 --control 4 --family-start 96xx …` (five scenarios, not deploy-token) | `runs/20261025-0817-e01-spray-<scenario>-consequence-{recruiting,control}-32b-scaleup` |
| Deliberate vs accidental labels | `experiments/E01-behaviour-pilot/judge_labels.py`, `judge_topup.py` | `runs/*-e01-topup-semantic-judge` |
| Judge vs the author's blind labels (36 of 40, κ 0.79) | `sample_label_batch.py`, `label_agreement.py` | `runs/20261025-1355-e01-label-batch-2` |
| GPU replay, first data batch | `experiments/E02-activation-replay/plan_replay2.py`, then `modal_budget_client.py` | `runs/20261025-0119-e02-replay2-plan`, `runs/20261024-1727-e02-activation-replay`; report in `runs/20261025-0339-e02-replay2-results` |
| GPU replay, new-episode set | `plan_replay3.py`, then `modal_budget_client3.py` | `runs/20261025-0838-e02-replay3-plan`, `runs/20261025-0921-e02-replay3-modal-client`, `runs/20261025-0923-e02-replay3-completion` |
| Step table (6,404 eligible steps, 338 episodes) | `experiments/E05-probes/replay2_data.py`, `replay3_data.py` | `runs/20261025-1026-e05-replay3-data-1d95` |

### Main results

| Result in the paper | Script | Run |
|---|---|---|
| §4.1, Table 1 and Appendix C (behaviour rates) | `experiments/E03-target-screen/behaviour_summary.py` | `runs/20261025-1850-e03-behaviour-summary` |
| §4.2–4.3, Figure 2 (probe vs monitors, eventual and near-term labels) | `all_data_main.py --workers 3`, then `finalize_all_data.py 20261025-1317-e05-all-data-main 20261025-1456-e05-all-data-audit` (both in `experiments/E05-probes/`, run with its environment) | `runs/20261025-1317-e05-all-data-main`, `runs/20261025-1456-e05-all-data-audit`, `runs/20261025-1456-e05-all-data-main` |
| Near-term labels | `experiments/E05-probes/near_term.py` | `runs/20261025-0730-e05-near-term` |
| Text monitors, first data batch (18 setups) | `experiments/E06-monitors/monitors.py --steps-file …replay2-plan/all.jsonl` | `runs/20261025-0147-e06-monitor-main` |
| Text monitors, new-episode set (8 setups) | `monitors.py --steps-file …replay3-plan/all.jsonl` | `runs/20261025-0841-e06-monitor-main-balanced` |
| §4.4, confirmation test (frozen plan in [`docs/confirmatory_plan.md`](docs/confirmatory_plan.md)) | `experiments/E06-monitors/confirm.py` | `runs/20261025-1030-e06-confirmation` |
| §4.5, Table 2 (combination test) | `experiments/E06-monitors/combine.py`; the all-data rows come from `all_data_main.py` | `runs/20261025-1456-e05-all-data-main`, `runs/20261025-1030-e06-confirmation` |
| §4.3, pressure-probe check | `experiments/E05-probes/explore_trajectories.py` | `runs/20261025-0800-e05-explore-trajectories-pressure` |
| Exposure positive control (AUROC 1.000) | `experiments/E05-probes/replay3_positive_control.py` | `runs/20261025-1026-e05-replay3-positive-control` |

### Second target (gpt-oss-20b, §4.6)

| Result | Script | Run |
|---|---|---|
| Behaviour screens and the delayed whole-block strategy | `experiments/E03-target-screen/escalation_sweep.py --target gpt-oss --strategy envblock_late …` | `runs/20261025-2053-e03-escalation-gpt-oss-*-envblock_late` |
| Final collection (300 recruiting, 60 control episodes) | manifest builder; the run folder's `README.md` names the frozen prompt commit | `runs/20261025-2212-e03-gpt-oss-full-collection` |
| Disclosure-kind judge | `experiments/E03-target-screen/judge_gpt_oss_leaks.py`, joined by `experiments/E05-probes/gpt_oss_kind_join.py` | `runs/20261025-2228-e03-gpt-oss-disclosure-kind-judge`, `runs/20261025-2310-e05-gpt-oss-disclosure-kind-join` |
| Replay rendering gate | `experiments/E02-activation-replay/report_gpt_oss_rendering_gate.py` (replay code: `gpt_oss_replay.py`, `modal_gpt_oss.py`) | `runs/20261025-2236-e02-gpt-oss-rendering-gate` |
| GPU replay | `plan_gpt_oss_full.py`, then `gpt_oss_full_budget.py`, `download_gpt_oss_full.py`; summary by `report_gpt_oss_full.py` | `runs/20261025-2251-e02-gpt-oss-full-plan`, `runs/20261025-2253-e02-gpt-oss-full-client`, `runs/20261025-2255-e02-gpt-oss-full-download`, `runs/20261026-0138-e02-gpt-oss-full-completion` |
| Step table | `experiments/E05-probes/gpt_oss_replay_data.py` | `runs/20261025-2305-e05-gpt-oss-full-data` |
| Prediction windows (how many give-ins leave a step to predict from) | `experiments/E05-probes/gpt_oss_windows.py` | `runs/20261026-0056-e05-gpt-oss-window-audit` |
| Probes, with exposure positive control | `experiments/E05-probes/gpt_oss_positive_control.py`, then `gpt_oss_probes.py` | `runs/20261026-0137-e05-gpt-oss-positive-control`, `runs/20261026-0138-e05-gpt-oss-main` |
| Text monitors | `experiments/E06-monitors/monitors.py --steps-file …gpt-oss-full-plan/rows.jsonl`, scored by `score_gpt_oss_monitors.py` | `runs/20261025-2330-e06-monitor-main-gpt-oss`, `runs/20261026-0108-e06-monitor-score-gpt-oss` |
| Combination test | `experiments/E06-monitors/combine_gpt_oss.py` | `runs/20261026-0148-e06-gpt-oss-combination` |
| Alarms | `experiments/E06-monitors/alarm_join_gpt_oss.py` | `runs/20261026-0159-e06-gpt-oss-alarm-join` |

### Appendix results

| Result | Script | Run |
|---|---|---|
| Per-scenario and cost tables | `experiments/E06-monitors/cost_and_scenarios.py` | `runs/20261025-1543-e06-cost-and-scenarios` |
| Score correlations, shared misses, alarms | `experiments/E06-monitors/appendix_errors.py` (pass `--keyword-review runs/20261025-1504-e06-appendix-errors/keyword_review.json`, or omit it) | `runs/20261025-1504-e06-appendix-errors` |
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
| Tables 1–2 and the monitor-design figure | `experiments/E05-probes/.venv/bin/python report/make_data_figures.py` (sources listed in [`report/figures/DATA_FIGURES.md`](report/figures/DATA_FIGURES.md)) |
| Figure 2 (Qwen3-32B and gpt-oss-20b panels) | `uv run --with matplotlib python report/figures/make_figure2_targets.py`, run after `make_data_figures.py` |
| Pipeline figure (Appendix B) | `report/figures/make_pipeline_figure.py` |
| Appendix G coverage table | `report/make_appendix_coverage.py` |
| Appendix H robustness tables and per-layer figure | `report/make_appendix_robustness.py` |
| The paper (DOCX and PDF) | `report/build_paper.py`; the system tools and fonts it needs are listed in [`report/BUILD.md`](report/BUILD.md) |

## What is not in git

- **Activations.** The saved activations are too large for git. They are kept on the Modal volume `collusion-activations` and can be regenerated with the GPU replay steps above. Everything computed from them (step tables, probe scores, metrics and reports) is in `runs/`.
- **Monitor response caches** (`runs/*/cache/`). Monitor scores and metrics are committed, but rerunning `monitors.py` makes fresh paid calls.
- **Large or regenerable run outputs**: rendered prompts, tokenizer and model-config copies, and per-row probe-score exports (see [`.gitignore`](.gitignore)).
- **API keys.** `.env` is never committed.

Transcripts, labels, scores and reports are all in `runs/`.

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
| [`docs/`](docs/) | Design notes, scenario guidelines, the frozen confirmatory plan and limitations |
| [`explainers/`](explainers/) | Plain-language explainers of the methods |
| [`archive/internal/`](archive/internal/) | Working notes from the sprint, kept for the record |
| [`src/collusion/`](src/collusion/) | Shared helper that creates run folders |

Each experiment folder has its own `README.md` with more detail.

## Safety notes

All tools are mocked in memory, and every protected value is a randomly generated fake; no real credential, system or network resource is touched. The prompts, including the recruiting peer prompts, are released in full (paper Appendix I) for the reasons given in the paper's Appendix A.

## Citation

> Raghav, L. (2026). *Recruited: Pre-Crime for Agents? Predicting Give-In to Collusion Pressure, with Activation Probes and Text Monitors.* Apart AI Collusion Research Sprint. https://github.com/leonidas1712/collusion-research
