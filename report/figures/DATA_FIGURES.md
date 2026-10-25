# Qwen data figures and tables

Regenerate from the repository root (CPU only; no inference or API calls):

```sh
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 experiments/E05-probes/.venv/bin/python report/make_data_figures.py
```

Each figure and table has a PDF, a 300-dpi PNG and its numerical CSV. Tables also have Markdown versions for native document tables. Captions are in `data_figure_captions.md`; source hashes and software versions are in `data_figures_manifest.json`.

| Output | Saved sources under `runs/` |
|---|---|
| `figure2_prediction` | `20261025-1456-e05-all-data-main/metrics.json`; `20261025-1030-e06-confirmation/confirm.json` |
| `figure_monitor_design` | `20261025-1456-e05-all-data-main/metrics.json`; `20261025-0147-e06-monitor-main/metrics_main_A_hazard.json` |
| `table1_behaviour` | `20261025-1850-e03-behaviour-summary/summary.json` (Qwen3-32B, plain peer) |
| `table2_combination` | `20261025-1456-e05-all-data-main/metrics.json`; `20261025-1030-e06-confirmation/confirm.json` |
| `monitor_access_paired_contrasts` | `20261025-0147-e06-monitor-main/scores.json`; `20261025-0337-e05-replay2-data/rows.jsonl`; `20261025-0730-e05-near-term/labels.jsonl` |

The script reads saved estimates and intervals, and recomputes only the paired access-level contrasts (1,000 family bootstrap draws). The adjacent historical monitor report is not used as a numerical source. Replacement source paths are CLI arguments; fixed manuscript cohort counts are asserted so changed cohorts require caption review. Confirmation contains only near-term labels and overlaps the all-data cohort. No second-target measurements are included.
