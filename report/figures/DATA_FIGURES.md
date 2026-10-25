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

## Figure 2 with both targets

Run `uv run --with matplotlib python report/figures/make_figure2_targets.py` after the original data-figure generator. This replaces only Figure 2's image/data/caption outputs and writes `figure2_targets_manifest.json`, which is authoritative for the updated figure. It reads saved Qwen and gpt-oss estimates without fitting models, checks the gpt-oss probe/monitor row-ID match, and preserves the Qwen estimates. The older `make_data_figures.py` still produces the Qwen-only layout if run alone. The new panel shows both gpt-oss horizons for the same three individual methods; combination results remain unavailable until supplied. The CSV contains every plotted estimate and interval. The caption file is for manuscript assembly; the generator does not edit paper.md.

The two-target Figure 2 now rebuilds from `figure2_targets_input.json`, a compact
committed snapshot of the plotted estimates and their source hashes. No per-row
exports or monitor caches are needed. Use `--refresh-from-runs` to repeat the
original coverage audit from full local exports; that optional audit requires the
untracked per-row probe and monitor files.

## Behaviour eligibility

Table C.1 (`table1_behaviour.csv`) now defaults to `behaviour_uniform_input.json`:
98/224 recruiting give-ins, including deploy-token 19/30. The compact input records
every episode hash and its receipt-based eligibility decision. It requires a
correct summary written at some point, rather than checking only the final file.
The historical 1850 summary remains unchanged and is not the table input.

To repeat the audit with local episode JSONs, run
`uv run --with numpy python report/make_behaviour_table_input.py`.
Then run the normal figure command and restore the two-target Figure 2 with
`uv run --with matplotlib python report/figures/make_figure2_targets.py`.
A fresh clone can render the table directly from the committed compact input.
