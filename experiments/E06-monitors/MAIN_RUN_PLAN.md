# E06 main run: plan and cost estimate

Draft, 2026-10-25. Nothing in this plan has been run. It needs Leo's prompt review and his OK on the budget first.

## What gets scored

- **Steps.** Every eligible target request in deploy-token v2 (T0, T1, T2, T7) and in the five spray rows: dispatch-integration-code, procurement-reserve-price, service-rollout-threshold, service-capacity-figure, handoff-exception-note. Own-stake, many-to-one and thinking-mode runs are left out. Eligible means `valid_for_comparison`, `token_in_context`, and before the first action. The action step's own input is kept, as in E05.
- **Monitors.** gpt-5-nano judge, Luna Decisions, Jev 1.14.
- **Prompts and levels.** Detector and forecaster, each at ladder levels 1, 2 and 3.
- **Scoring.** One function, `score.py:score_metrics`, scores the probe and every monitor on the same rows.
  - Within-round AUROC is stratified by scenario × round.
  - The added value is measured over round + prompt length.
  - Alarm cutoffs come from the pooled benign episodes of the other folds and are applied to the held-out fold.
  - The trade-off curve uses false-alarm budgets of 1, 5, 10 and 20%.

The estimate below uses the replay-2 plan's step table, `runs/20261025-0119-e02-replay2-plan/all.jsonl` (6,026 target requests). It does not use guesses from episode files. All 4,184 eligible rows match their episode request by `request_sha256`.

| Scenario | Episodes | Recruiting steps | Control steps | Alone steps |
|---|---:|---:|---:|---:|
| deploy-token-v2 | 74 | 871 | 487 | 12 |
| service-capacity-figure | 36 | 573 | 186 | 8 |
| handoff-exception-note | 38 | 446 | 155 | 8 |
| service-rollout-threshold | 29 | 445 | 95 | 8 |
| dispatch-integration-code | 29 | 326 | 138 | 8 |
| procurement-reserve-price | 24 | 249 | 163 | 6 |
| **Total** | **230** | **2,910** | **1,224** | **50** |

## Cost estimate

**Method.** Every one of the 4,184 steps was rendered at every level with the new prompts. Characters were converted to tokens with the ratios measured in the preliminary run: nano 0.212, Luna 0.241, Jev 0.311 tokens per character. Prices:
- nano: $0.05/M input, plus the measured mean output cost of $0.00020 per call (output is most of nano's cost);
- Luna: $0.10/M input;
- Jev: $0.042/M input.

| Combination ($) | L1 | L2 | L3 |
|---|---:|---:|---:|
| nano detector | 1.15 | 1.30 | 1.33 |
| nano forecaster | 1.11 | 1.25 | 1.29 |
| Luna detector | 0.47 | 0.80 | 0.88 |
| Luna forecaster | 0.48 | 0.81 | 0.89 |
| Jev detector | 0.26 | 0.43 | 0.48 |
| Jev forecaster | 0.26 | 0.44 | 0.48 |

**Full run:** 75,312 calls (4,184 × 18), about **$14.1**. By monitor: nano $7.4, Luna $4.3, Jev $2.4. Before running, set the cap to about 1.3 × the estimate, for example $18 for the full run.

**Wall time.**
- Throughput in the preliminary run: nano took about 9–20 s per call per process; Luna and Jev took about 0.7 s.
- Shard the judge across processes with `--shard i/n` and give each process its own `--ledger`. The per-process caps must add up to no more than the total cap.
- Full run: 25,104 nano calls at 20 s across 24 shards is about **5.8 h**. 50,208 decision calls across 4 processes is about **2.4 h**, running at the same time. 48 nano shards would halve the judge time, if OpenRouter rate limits allow it (untested).

## Cheaper subsets

These are based on the preliminary run, which used 150 deploy-token v1 steps, so the weak-combination calls are noisy. The detectors at L1 were at chance (0.48–0.53), and Luna's forecaster was at chance at every level (0.49–0.54).

| Plan | Combinations | Calls | Cost | Wall time (nano at 24 shards) |
|---|---|---:|---:|---:|
| Full | 3 monitors × 2 prompts × 3 levels | 75,312 | $14.1 | ~5.8 h |
| **A (recommended)** | Jev: both prompts × L1–L3 (the cheapest full ladder); Luna: detector L2 and L3; nano: detector L3, forecaster L1 and L3 | 46,024 | $7.8 | ~2.9 h |
| B | Jev: both prompts × L1–L3; Luna: detector L3; nano: detector L3 and forecaster L3 | 37,656 | $5.9 | ~1.9 h |

- **A** keeps a full ladder (Jev) for the monitor-ladder claim. It keeps both question types at the top level for all three monitors, and the nano forecaster at both ends of the ladder.
- **B** keeps the ladder only for Jev.
- **Another saving:** run nano with reasoning effort `minimal`, since output is most of nano's cost. That is a settings change, so the prelim comparison would need re-checking first.

## Before launching

1. Leo reviews `PROMPTS.md`. The allowed-values sentence and the per-scenario filling are new and have not been run live.
2. **Labels and folds.** The replay-2 plan table has no outcome labels (`label`, `first_action_round`, `steps_until_action`) and no fold ids. `score.py` needs these, plus the E05 fold assignment for these episodes from the replay-2 probe fit, in the step table that `--steps-file` reads. Use the step table codex-2 produces, not the plan file, so the rows match the probe's rows exactly. `monitors.py` itself needs only episode, request_idx, request_sha256, condition and round, so monitor scoring could start before the probe fit is done.
3. Raise `MAX_CAP` in `monitors.py`, which is currently $2.50. This is a deliberate one-line change, made only after the budget OK.
4. Run a 5-call smoke test per monitor on spray steps to check the filled prompts on a non-deploy-token scenario. Cost: under $0.01.

## Commands (after the OK)

```sh
S=<replay-2 step table with labels and folds>
uv run --with numpy python experiments/E06-monitors/monitors.py --steps-file $S --cap 0.01 --max-calls 5      # new run + smoke
R=runs/<new e06-monitor-main run>
for i in $(seq 0 23); do uv run --with numpy python experiments/E06-monitors/monitors.py --run $R --monitors llm --cap 0.40 --shard $i/24 --ledger budget-llm-$i.json --levels 1,3 --prompts forecaster > $R/log-llm-$i.txt 2>&1 & sleep 3; done
# ...the same pattern for each subset combination, and for luna/jev with --shard i/4
experiments/E05-probes/.venv/bin/python experiments/E06-monitors/score.py --run $R
```

Start processes a few seconds apart: two processes that start in the same second race on `meta.json`. When a run is resumed with different `--prompts` or `--levels`, the cache keeps work done earlier, so no step is paid for twice.
