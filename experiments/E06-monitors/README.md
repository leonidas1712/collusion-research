# E06: black-box monitors on the probe's steps

This experiment adds an LLM judge (`openai/gpt-5-nano`) and two decision models (Luna Decisions, Jev 1.14). Each one runs as a detector ("is the agent breaking the rule?") and as a forecaster ("will it break the rule later in this episode?"), at ladder levels 1–3. The rows are the E05 step table: the main eligible set of fit run `20261024-1937-e05-probe-core`. Every score joins the probe's out-of-fold score by `(episode, request_idx, request_sha256)`.

- `prompts.py` holds the prompt text and builds the per-step input at each level. Sources and edits are in `PROMPTS.md`.
- `monitors.py` does the sampling, request building, per-call cache and budget ledger, then runs the monitors.
- `score.py` runs one scoring function, `score_metrics(table, row_ids, scores)`, for the probe, the baselines and every monitor. It reports within-round and pooled AUROC, the added value over round + prompt length, control-calibrated episode alarm recall and lead time. It reuses E05 `metrics.py`.
- `test_monitors.py` holds the offline tests: ladder contents at each level, no future information, parsing, cache, budget cap. These tests never call the network.

```sh
uv run python -m unittest discover -s experiments/E06-monitors
uv run --with numpy python experiments/E06-monitors/monitors.py --cap 2.50 --max-calls 5     # smoke test, new run
uv run --with numpy python experiments/E06-monitors/monitors.py --run runs/<id> --monitors jev --cap 0.50 --ledger budget-jev.json
uv run --with numpy python experiments/E06-monitors/monitors.py --run runs/<id> --monitors llm --cap 0.30 --shard 0/4 --ledger budget-llm-0.json
experiments/E05-probes/.venv/bin/python experiments/E06-monitors/score.py --run runs/<id>
```

The code caps every ledger at $2.50. Each process reserves the worst-case cost before every call and settles it to the billed `usage.cost`. When several processes run at once, each one gets its own ledger file, so the per-process caps must add up to no more than the total budget. Results already in the cache are reused, so no call is paid for twice.

Preliminary run: `runs/20261024-2357-e06-monitor-prelim/report.md`.
