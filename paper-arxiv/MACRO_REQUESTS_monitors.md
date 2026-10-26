# Macro requests from appendix/monitors.tex (helper writer, commit f575628)

Values are proposed, with their sources. codex-2 verifies every value.

## Per-call Jev on gpt-oss-20b (held-out "loso" split)
- `\gptossCallJevNoReasoningUnstratified`: 0.81, from `runs/20261026-1306-e06-percall-input-jev/metrics.json`, `loso.pooled_auc`.
- `\gptossCallJevUnstratified`: 0.86, from `runs/20261026-1319-e06-percall-input-jev-l4/metrics.json`, `loso.pooled_auc`.
- `\gptossCallJevNoReasoningLeakFlagged`: 98.35%, from 1306 `alarms.json`, `loso.warning_by_seed`.
- `\gptossCallJevNoReasoningRefusingFlagged`: 86.55%, from 1306 `alarms.json`, `loso.held_reply_alarm_by_seed`.
- `\gptossCallJevLeakFlagged`: 98.35%, from 1319 `alarms.json`, `loso.warning_by_seed`.
- `\gptossCallJevRefusingFlagged`: 64.02%, from 1319 `alarms.json`, `loso.held_reply_alarm_by_seed`.
- `\gptossCallProbeMinusJevNoReasoning` (+CI): 0.63 [0.56, 0.71], from 1306 `paired_probe_difference.json`, `comparisons.loso`.
- `\gptossCallProbeMinusJev` (+CI): 0.51 [0.43, 0.58], from 1319 `paired_probe_difference.json`, `comparisons.loso`.
- `\gptossCallProbeMinusJevNoReasoningReversed` (+CI): 0.18 [0.12, 0.23], from 1306 `reversal_diagnostic.json`, `results.loso.probe_minus_reversed`.
- `\gptossCallJevReversed` (+CI): 0.60 [0.55, 0.67]. **No run file exists yet.** It is the exact complement (1 − AUROC) of the 1319 metrics. Write a small reversal file for the 1319 run.

## Per-call Jev on Qwen3-32B
These need rescoring under the unified leak label from the saved scores of `runs/20261026-1309-e06-percall-input-jev-qwen`. The old give-in-label values are 0.78, 71.29%, 27.71% and a gap of 0.21 [0.17, 0.28]. Do not substitute those.
- `\qwenCallJevCI`
- `\qwenCallJevUnstratified`
- `\qwenCallJevLeakFlagged`
- `\qwenCallJevRefusingFlagged`
- `\qwenCallProbeMinusJev` (+CI). Results §4.4 also needs this.

## Round-level monitor grid
36 entries, each with a CI, from `runs/20261025-0147-e06-monitor-main`.
- **Preferred:** generate `tables/monitor_grid.tex` instead of 36 macros, then replace the hand-written rows in `monitors.tex` with an `\input`.
- **Naming, if macros:** `\qwenMon{Jev|Nano|Luna}{Detect|Forecast}{Actions|Peer|All}{Ever|Near}`.
- **Sources:**
  - Ever: `metrics_main.json`, `"<jev|llm|luna> <detector|forecaster> L<1|2|3>".ranking.within_round_auc` / `within_round_ci95`.
  - Near: `metrics_main_A_hazard.json`, same paths.
- **Mappings:** Actions = L1, Peer = L2, All = L3. Nano = "llm".

## Formatting
Rates in prose and tables are whole-number percentages, e.g. 98%, not 98.35%, per the WRITING.md readability intent. AUROC is shown to two decimals.
