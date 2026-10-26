# Exploratory audit of reasoning length and alarm onset

The frozen immediate/all/loso token scores were compared with each saved fit's original reply-calibrated threshold using strict `>`. No fitting, calibration changes, model calls or activation computation were performed.

| Quantity | Result |
|---|---:|
| Median reasoning tokens, 1,995 nonempty recruiting replies | 7 |
| Median reasoning tokens, 121 nonempty leaking replies | 16 |
| Median including empty reasoning, 2,205 recruiting replies | 6 |
| Median including empty reasoning, 146 leaking replies | 14 |
| First-token crossings / alarmed leaking reply-seed observations | 221/308 (71.8%) |
| Conditional median crossing fraction | 0.076923 |

The three seeds contribute 73/105, 73/101 and 75/102 first-token crossings among their alarmed leaking replies. These are repeated observations across seeds, not 308 independent replies or episodes. The first token means the first captured reasoning-body token, consumed by the probe. It is before the public answer/tool header, not before all generated output.

## Matched-recipe comparison

For the stopped four-layer grid, seed 42 pooled family CV, both-loss training and EMA-max aggregation, re-reading saved scores and thresholds gives:

| Input | Held-reply alarms | Rate |
|---|---:|---:|
| Reasoning | 32/1,665 | 1.92% |
| Incoming messages/tool results | 111/1,794 | 6.19% |

This matches `runs/20261026-0822-e05-expanded-stream/stopped_grid_interim.json`. The recipe is matched, but reply coverage differs. These are not LOSO or three-seed results. The original 4% versus reduced incoming-only 19% comparison mixes recipes as well as eligible reply sets.

## Interpretation

Most observed alarms arise at the first captured reasoning token. The relative-position median therefore does not establish that the probe follows a decision forming across reasoning text. The result is consistent with predictive state already being present at reply onset, but does not identify whether that state represents context, an incipient decision, or another correlate. The first reasoning-token activation also depends on that token itself.

The original last-prompt comparison changes the training label, input, and eligible cohort, including appended first-public-emission requests. It cannot establish that label choice matters more than token position. That requires a matched ablation. The incoming-only estimate supports early availability of a signal, without isolating its cause. Use “before public answer/tool output”, not “before any output”.

Reproduce: `uv run --with numpy python experiments/E05-probes/reasoning_stream_onset_audit.py`. The adjacent JSON includes every alarmed reply-seed observation and onset index. Inputs: `runs/20261026-0522-e05-reasoning-stream-data/replies.json`, this run's `immediate/all/loso/*/{fit.json,scores.npz}`, and the stopped expanded-grid score files with `runs/20261026-0813-e05-expanded-stream-data/replies.json`.
