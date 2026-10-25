# Pipeline appendix: figure, caption, stage table, replay checks

For insertion into the "Experimental Pipeline and Reproducibility" appendix of `report/paper.md`. Every count below was checked against the dataset and run summaries listed at the end, on 25 Oct 2026. The figure is drawn by `report/figures/make_pipeline_figure.py`.

## Figure

![Pipeline](figures/pipeline.png)

**Figure [Pipeline].** How the collected episodes become the reported numbers, for the Qwen3-32B target. Each box gives one stage: what it does, and the count at that point, written as *first data batch | new-episode set*.
- **Stages 1–3:** 397 complete episodes shrink to 338 kept episodes with 6,404 eligible steps.
- **Stage 4:** every target request is replayed through the open weights, and fidelity is checked on the replies.
- **Stages 5 and 6:** the probe and the text monitors branch from the same eligible steps, and both feed scoring on all the data (stage 7) and the confirmation test (stage 8).
- **Second lane (dashed):** reserved for gpt-oss-20b. It has its own peer and counts, and is never pooled with the first.

Counts come from the combined step table and the replay, monitor and confirmation summaries.

## Stage table

| Stage | Input | What happens | Output | Key settings | Code |
|---|---|---|---|---|---|
| 1. Collect episodes | Scenario, condition, seed | Peer and target run in a mocked workspace via the API | Transcripts and tool logs: 268 complete episodes (187 recruiting, 55 control, 26 alone) \| 129 (110 recruiting, 19 control) | Target Qwen3-32B, thinking off; peer DeepSeek-V4-Flash; OpenRouter, one pinned target provider, no fallbacks; temperature 0.7; up to 20 rounds and 12 tool steps per turn. Six scenarios in the first batch, five in the new-episode set. New-episode set collection: $0.82 | `experiments/E01-behaviour-pilot/scale_up.py`, `harness.py` |
| 2. Label outcomes | Tool logs | A rule finds the first forbidden action (the complete value in a channel post or a new file) and its round. A decision-model judge marks each give-in deliberate or accidental | One label per episode; 63 \| 38 kept recruiting episodes gave in | Exact match on the episode's synthetic value. The judge is Luna Decisions, which agrees with 40 blind human labels on 36 of 40 (κ = 0.79) | Scenario scorers in `experiments/E01-behaviour-pilot/`; `judge_labels.py` |
| 3. Select eligible steps | Labelled episodes | Keep steps after the value is read and before it is disclosed. Drop invalid episodes (incomplete, never read the value, or ordinary task wrong) and those with no step in the window | 230 kept, 38 dropped (36 invalid, 2 no step); 4,184 steps \| 108 kept, 21 dropped (all invalid); 2,220 steps. Total 6,404 steps from 338 episodes | A step is one request to the target. Recruiting eligible steps: 2,910 \| 1,787 | `experiments/E05-probes/replay2_data.py`, `replay3_data.py` |
| 4. GPU replay | Every target request of the complete episodes | One forward pass per request through the open weights; no generation | One [64 × 5,120] array per request: all 64 decoder-layer outputs at the last prompt token. 6,003 \| 3,112 requests (plus 23 shared branching states, first batch only) | Qwen/Qwen3-32B, revision 9216db5781bf21249d130ec9da846c4624c16137, bf16, one A100-80GB on Modal. Reply NLL 0.249 \| 0.227; top-5 agreement 99.79% \| 99.82%. Cost $5.51 \| $2.94 | `experiments/E02-activation-replay/replay.py`, `modal_app.py`, `fidelity.py` |
| 5. Train probes | Activations and labels on recruiting eligible steps | Logistic regression on one layer's 5,120-dimensional vector | A probe score per step | Layer chosen from 17 candidates (0, 4, …, 60, 63) on a 25% inner family holdout. C = 0.1; training-only standardisation; positives and negatives weighted equally within each round. Families never cross train and test. Held-out scenario: 6 rotations; pooled CV: 5 family folds; seeds 42, 43, 44 | `experiments/E05-probes/all_data_main.py`, `replay2_core.py` |
| 6. Run text monitors | The same eligible steps, rendered as text | Each monitor gives a score per step | A monitor score per step | Jev 1.14, Luna Decisions, GPT-5-nano; 3 access levels × 2 questions (detect, forecast). First batch: all 18 setups on all 4,184 steps (75,312 calls, $12.67). New-episode set: 8 setups chosen before its results existed, on 2,220 steps ($2.33) | `experiments/E06-monitors/monitors.py`, `prompts.py` |
| 7. Score | Probe and monitor scores, labels | Within scenario × round AUROC; combination test (round, prompt length and monitor score, with and without the probe) | Figure 2 and the main tables | 1,000 family-bootstrap resamples for 95% intervals; recruiting steps only, 4,697 (250 near-term positives) | `experiments/E06-monitors/score_main.py`, `combine.py`; `experiments/E05-probes/metrics.py` |
| 8. Confirmation | New-episode set (stages 1–4 and 6) | The probe and combination models, trained on the first data batch only and frozen under a plan fixed in advance, are scored once | The confirmation numbers | 1,787 recruiting steps (82 near-term positives) from 89 episodes; near-term label only | `experiments/E06-monitors/confirm.py` |

## Replay and integrity checks (stage 4 text)

Every target request was replayed once through the open-weight checkpoint: Qwen/Qwen3-32B, revision 9216db5, bf16 on one A100-80GB GPU, with no generation. We saved the output of all 64 decoder layers at the last prompt token, a [64 × 5,120] array per request. The probe chooses among 17 of these layers (stage 5).

Before loading the model, each request, prompt, token sequence and episode was checked against a hash manifest frozen beforehand. All matched, and every saved array was finite and had the expected shape.

To check that the replay reproduces the model that acted, we scored the first 64 tokens of each actual reply under the replayed model:
- **First data batch:** token-weighted negative log-likelihood 0.249; the actual token was in the replayed model's top 5 for 99.79% of tokens; 276,868 tokens scored.
- **New-episode set:** 0.227 and 99.82%; 152,965 tokens scored.

Low reply likelihood loss and matching token counts are consistent with the replay matching the served model. They do not prove token-for-token identity with the provider's private template or kernels.

As a positive control, a probe at layer 32 separates steps before and after the value is read at AUROC 1.000 on held-out families in the new-episode set.

## Sources (internal, for checking; not for the paper)

- Combined step table: `runs/20261025-1026-e05-replay3-data-1d95/` (summary.json, rows.jsonl, excluded-episodes.json). Batch split by source replay.
- Replay: `runs/20261025-0339-e02-replay2-results/report.md`; `runs/20261025-0923-e02-replay3-completion/summary.json`.
- Probe recipe: `runs/20261025-1456-e05-all-data-main/report.md`.
- Monitors: `runs/20261025-0147-e06-monitor-main` (75,312 calls, $12.67, per the experiment log); `runs/20261025-0841-e06-monitor-main-balanced/budget.json` ($2.33).
- Confirmation: `runs/20261025-1030-e06-confirmation/report.md`.
- Not totalled here: the API cost of collecting the first data batch.
