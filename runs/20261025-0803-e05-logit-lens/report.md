# Logit lens on the replay-2 last layer (probe idea 2)

Code: `experiments/E05-probes/explore_logit_lens.py`. CPU only, 2 threads, $0, no GPU, no API calls.

## What was done

- **Input:** `runs/20261025-0337-e05-replay2-data/features.npy`, layer index 63, for all 4,184 eligible rows. This is the output of decoder block 63 at the last prompt token (after `<think>\n\n</think>\n\n`). E02 `replay.py` `capture` saves it with a forward hook *before* the final norm.
- **Readout:** Qwen3 RMSNorm (`model.norm.weight`, eps 1e-6 from config) → `lm_head` → softmax, all in float32. Weights come from `Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137`, `model-00017-of-00017.safetensors`. The index says this one 3.1 GB shard holds both tensors, and it is now in the HF cache. The bf16 tensors are read straight from the safetensors header.
- **Features:**
  - `p_refusal`: the probability mass on the single-token openers `I`, ` I`, `Sorry`, ` Sorry`, `Unfortunately`, ` Unfortunately`. `I'm` is two tokens (`I` + `'m`), so `I` already covers it. Caveat: `I` also opens some compliant replies.
  - `p_tool`: the mass on `<tool_call>` (id 151657).
  - `entropy`.
  - `p_max`.
  - The top-5 tokens are in `scores.csv`.
- **Scores:** each scalar is used directly, with a sign fixed before scoring: −p_refusal, +p_tool, +entropy, −p_max. There is also a logistic regression on log p_refusal, log p_tool, entropy and log p_max (standardized, C=1). It is cross-fitted on `runs/20261025-0240-e05-replay2-folds/folds.json` (3 seeds × 5 family folds). Each fit uses the fold's train + calibration eligible rows and scores its test rows.
- **Metric:** E05 `within_round` with stratum_key=scenario, on the 2,910 recruiting rows, with the family-bootstrap 95% CI from `ranking_summary` (1,000 reps). "Added value" uses the E06 `added_value`: out-of-fold turn + log length, then + the score, with a family-bootstrap CI on the gain.

## Sanity check: does the argmax predict the actual first reply token?

All 4,184 replies were found and their request hashes matched. 1,076 replies start with a tool call, 3,108 with text.

| Check | Rate |
|---|---|
| Argmax equals the actual first reply token | **90.6%** |
| Same, tool-call replies | 95.6% |
| Same, text replies | 88.9% |
| Same, recruiting rows | 90.5% |
| Same, control rows | 90.4% |
| Actual first token is in the top 5 | 99.8% |
| Mean probability of the actual first token | 0.86 |

The readout is wired correctly. The provider served the model in fp8 and sampled at temperature 0.7, so a 100% match is not expected.

## Ranking (recruiting rows, within scenario × round, 95% family-bootstrap CI)

| Score | Eventual label (618/2910 pos) | Near-term A_hazard (168/2910 pos) | Added value over turn+length, A_hazard |
|---|---|---|---|
| −p_refusal | 0.537 [0.458, 0.622] | 0.507 [0.446, 0.571] | +0.001 [−0.014, 0.015] |
| p_tool | 0.545 [0.518, 0.578] | **0.586 [0.556, 0.618]** | +0.019 [0.006, 0.032] |
| entropy | 0.488 [0.411, 0.561] | 0.524 [0.471, 0.577] | +0.002 [−0.006, 0.010] |
| −p_max | 0.484 [0.405, 0.557] | 0.521 [0.466, 0.572] | +0.000 [−0.006, 0.007] |
| Logistic on the 4 scalars (3 seeds) | 0.510 [0.445, 0.572]; fold-stratified 0.506 | 0.554 [0.517, 0.594]; fold-stratified 0.557 | +0.027 [0.011, 0.048] |

With the eventual label, no score adds value over turn + length: all gains are within ±0.003. The pooled AUROCs (no stratification) are higher, but they mostly reflect round and scenario: p_tool 0.615 eventual and 0.659 A; logistic 0.610 and 0.703. They are in `metrics.json`.

## Reading

- The model's own first-token forecast barely separates who gives in once scenario × round is held fixed. The best result is tool-call mass on the near-term label: 0.586, with a CI above 0.5 and a small added value (+0.02). This fits a simple pattern. A step just before a leak is more often about to call a tool (the leak is often a `write_file`). The group means agree: one step before the leaking call, mean p_tool is 0.47, against 0.27 on held recruiting rows.
- Refusal-opener mass does not help (0.51–0.54, CIs over 0.5). Held and eventually-leaking rows put similar mass on `I` (0.23 vs 0.20).
- None of these scores meets the idea-2 success bar (≥ 0.65 on the near-term label, or added value on a held-out scenario). The best is below the refit activation probe (A, LOSO 0.611) and the Jev forecaster L3 (0.660). This is consistent with "the decision is made mid-reply, not at its start" (idea 6).
- Not done: a LOSO (held-out scenario) version of the logistic. The single scalars need no fit, so their numbers already hold on a new scenario.

## Examples (random rows; more in `examples.md`)

See `examples.md`. In the earlier `--peek` pass, the top tokens were typically `I` (refusal-style replies such as "I cannot share…"), `<tool_call>`, `The` and `You`.

## Files

- `scores.csv`: one row per eligible step. Columns: step_id, labels (eventual, A_hazard), the four scalars, argmax token, top-5 with probabilities, the actual first reply token, argmax match, and the cross-fitted LR score per label (mean over seeds).
- `metrics.json`: all numbers, per-seed values, coverage, pooled AUROCs, added value and group means.
- `examples.md`, `meta.json`, `log.txt`.
