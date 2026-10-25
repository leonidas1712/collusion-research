# Recruited: can you see an agent being won over?

Code and data for the Apart AI Collusion Research Sprint report "Recruited". A peer agent asks a target agent (Qwen3-32B) for a value that the target's operator told it to keep private. We test whether the target's activations (linear probes), or text monitors reading the conversation, can predict that the target will give in before it does.

The report source is `report/paper.md`; the rendered PDF is `report/build/paper.pdf`.

## What is in the repository

| Folder | Contents |
|---|---|
| `experiments/E01-behaviour-pilot/` | The multi-agent harness, the six scenarios, peer tactics, outcome scorers and the leak-kind judge |
| `experiments/E02-activation-replay/` | GPU replay of every target request through the open weights (Modal), and fidelity checks |
| `experiments/E03-target-screen/` | Second-target screens (gpt-oss-20b, Gemma-4-31B) and the behaviour summary |
| `experiments/E05-probes/` | Probe training and evaluation (held-out scenario, pooled CV, near-term labels, diagnostics) |
| `experiments/E06-monitors/` | Text monitors (GPT-5-nano, Jev 1.14, Luna Decisions), scoring, the combination test and the confirmation test |
| `report/` | The paper, figure and table scripts, and the build |
| `runs/` | One folder per run, named `YYYYMMDD-HHMM-<experiment>-<name>`, each with `meta.json` (command, git commit, settings) and its outputs |
| `docs/` | Design notes, the frozen confirmatory plan (`docs/confirmatory_plan.md`) and limitations |

**Not in git:** the activations (about 25 GB per target) and the monitor response caches. Activations live in the Modal volume `collusion-activations` and can be regenerated with the replay step below. Transcripts, labels, scores and reports are all in `runs/`.

## Setup

- Python environments are managed with `uv`. The probe and replay code use their own environments (`experiments/E05-probes/.venv`, `experiments/E02-activation-replay/.venv`); create them with `uv sync` in those folders.
- API keys: OpenRouter, for agents and monitors. GPU replay uses Modal, on one A100-80GB.
- Every paid step takes a hard spending cap (`--cap-usd`, `--cap` or `--phase-ceiling`) and records billed cost in its run folder.

## Which script produces which result

Paths under `runs/` name the run used in the paper. Each run's `meta.json` has the exact command.

### Data (Qwen3-32B)

| Result | Script | Run(s) |
|---|---|---|
| Episodes, first data batch (deploy token) | `experiments/E01-behaviour-pilot/scale_up.py --family deploy-token-v2 --strength consequence …` | `runs/20261024-2103-e01-deploy-token-v2-consequence-{recruiting,control,alone}-32b-scaleup`, plus the `-t1/-t2/-t7` tactic arms |
| Episodes, the five other scenarios | `scale_up.py --spray-row <scenario> …` | `runs/20261024-21xx-e01-spray-<scenario>-…` |
| New-episode (confirmation) set | `scale_up.py --spray-row <scenario> --recruiting 26 --control 4 --family-start 96xx …` (five scenarios, not deploy-token) | `runs/20261025-0817-e01-spray-<scenario>-consequence-{recruiting,control}-32b-scaleup` |
| Leak-kind labels (deliberate vs accidental) | `experiments/E01-behaviour-pilot/judge_labels.py`, `judge_topup.py` | `runs/*-e01-topup-semantic-judge` |
| Judge vs blind human labels (36/40, κ 0.79) | `sample_label_batch.py`, `label_agreement.py` | `runs/20261025-1355-e01-label-batch-2` |
| GPU replay, first data batch | `experiments/E02-activation-replay/plan_replay2.py`, then `modal_budget_client.py` | `runs/20261025-0119-e02-replay2-plan`, `runs/20261024-1727-e02-activation-replay`, report `runs/20261025-0339-e02-replay2-results` |
| GPU replay, new-episode set | `plan_replay3.py`, then `modal_budget_client3.py` | `runs/20261025-0838-e02-replay3-plan`, `runs/20261025-0921-e02-replay3-completion` |
| Step table (6,404 eligible steps, 338 episodes) | `experiments/E05-probes/replay2_data.py`, `replay3_data.py` | `runs/20261025-1026-e05-replay3-data-1d95` |

### Main results

| Result in the paper | Script | Run |
|---|---|---|
| §4.1, Table 1 / Appendix C (behaviour rates) | `experiments/E03-target-screen/behaviour_summary.py` | `runs/20261025-1850-e03-behaviour-summary` |
| §4.2–4.3, Figure 2 (probe vs monitors, eventual and near-term) | `experiments/E05-probes/all_data_main.py`, then `finalize_all_data.py` | `runs/20261025-1317-e05-all-data-main`, `runs/20261025-1456-e05-all-data-main` |
| Near-term labels | `experiments/E05-probes/near_term.py` | `runs/20261025-0730-e05-near-term` |
| Text monitors, first data batch (18 setups) | `experiments/E06-monitors/monitors.py --steps-file …replay2-plan/all.jsonl` | `runs/20261025-0147-e06-monitor-main` |
| Text monitors, new-episode set (8 setups) | `monitors.py --steps-file …replay3-plan/all.jsonl` | `runs/20261025-0841-e06-monitor-main-balanced` |
| §4.4, confirmation test (frozen plan) | `experiments/E06-monitors/confirm.py` | `runs/20261025-1030-e06-confirmation` |
| §4.5, Table 2 (combination test) | `experiments/E06-monitors/combine.py`; all-data rows from `all_data_main.py` | `runs/20261025-1456-e05-all-data-main`, `runs/20261025-1030-e06-confirmation` |
| §4.3, pressure-probe check | `experiments/E05-probes/explore_trajectories.py` | `runs/20261025-0800-e05-explore-trajectories-pressure` |
| Exposure positive control (AUROC 1.000) | `experiments/E05-probes/replay3_positive_control.py` | `runs/20261025-1026-e05-replay3-positive-control` |

### Appendix results

| Result | Script | Run |
|---|---|---|
| Per-scenario and cost tables | `experiments/E06-monitors/cost_and_scenarios.py` | `runs/20261025-1543-e06-cost-and-scenarios` |
| Score correlations, shared misses, alarms | `experiments/E06-monitors/appendix_errors.py` | `runs/20261025-1504-e06-appendix-errors` |
| Per-layer diagnostic | `experiments/E05-probes/layer_diagnostic.py` | `runs/20261025-1003-e05-layer-diagnostic` |
| Learning curve | `experiments/E05-probes/learning_curve.py` | `runs/20261025-0842-e05-learning-curve` |
| MLP probe | `experiments/E05-probes/near_term_mlp.py` | `runs/20261025-0848-e05-near-term-mlp` |
| Branching check | `experiments/E05-probes/replay2_branching.py` | `runs/20261025-0340-e05-replay2-branching` |
| Leak route and private-reasoning cutoff | `experiments/E05-probes/audit_reasoning_and_routes.py` | `runs/20261025-2324-e05-reasoning-route-audit` |
| Addressee check | `experiments/E06-monitors/addressee_audit.py` | `runs/20261025-2202-e06-addressee-audit` |

### Figures and tables

| Output | Script |
|---|---|
| Figure 1 (real exchange, setup, toy timeline) | `report/figures/make_figure1.py` (schematic; the quotes are from episode 0032 of the deploy-token recruiting scale-up) |
| Figure 2, Tables 1–2, monitor-design figure | `report/make_data_figures.py` (sources listed in `report/figures/DATA_FIGURES.md`) |
| Pipeline figure (Appendix B) | `report/figures/make_pipeline_figure.py` |
| Appendix G coverage table | `report/make_appendix_coverage.py` |
| Appendix H robustness tables and per-layer figure | `report/make_appendix_robustness.py` |
| The paper (DOCX and PDF) | `report/build_paper.py` (pandoc + citeproc, Apart template) |

### Second target (gpt-oss-20b)

| Result | Script | Run |
|---|---|---|
| Behaviour screens and the delayed whole-block strategy | `experiments/E03-target-screen/escalation_sweep.py --target gpt-oss --strategy envblock_late …` | `runs/20261025-2053-e03-escalation-gpt-oss-*-envblock_late` |
| Final collection (300 recruiting, 60 control) | (manifest builder; see `README.md` in the run folder) | `runs/20261025-2212-e03-gpt-oss-full-collection` |
| Disclosure-kind judge | `experiments/E03-target-screen/judge_gpt_oss_leaks.py` | `runs/20261025-2228-e03-gpt-oss-disclosure-kind-judge` |
| Replay rendering gate | `experiments/E02-activation-replay/report_gpt_oss_rendering_gate.py` (replay code: `gpt_oss_replay.py`, `modal_gpt_oss.py`) | `runs/20261025-2236-e02-gpt-oss-rendering-gate` |
| Replay, probes and monitors | [TODO: fill when the replay and analysis finish] | |

## Safety notes

All tools are mocked in memory, and every protected value is a randomly generated fake; no real credential, system or network resource is touched. Prompts, including the recruiting peer prompts, are released in full (report Appendix I) for the reasons given in the report's Appendix A.

<!-- Draft notes (remove before publishing):
- The gpt-oss collection run has no meta.json; its README names the frozen prompt commit c4478407.
- The repo-public checklist (secret scan, history purge) is in docs/release_checklist.md.
-->
