# Stopped expanded-grid interim: single seed 42, pooled family CV

This is an exploratory interim from the stopped four-layer concatenation grid. Only complete five-fold pooled cells are reported. It is not LOSO, not a three-seed estimate, and not the final respecified one-layer analysis. The completed priority grid contains 22 fit files: four complete five-fold cells and two action-time immediate folds. The two action-time folds are preserved but excluded from aggregate estimates.

| Stream | Label | Replies / positives | Within scenario × round AUROC [95% family CI] | Immediate-reply warning | Held-reply alarms |
|---|---|---:|---|---:|---:|
| reasoning | immediate | 1995 / 121 | 0.962 [0.938, 0.982] | 89.3% | 1.9% |
| reasoning | round | 1995 / 199 | 0.623 [0.565, 0.684] | 65.3% | 3.6% |
| incoming | immediate | 2199 / 143 | 0.916 [0.886, 0.944] | 85.3% | 6.2% |
| incoming | round | 2199 / 242 | 0.556 [0.504, 0.612] | 28.0% | 3.4% |

Features concatenate full layers6,12,18,23. Both-loss means SWiM16 plus tau1 softmax-weighted BCE; EMA alpha2/17 is fixed. Control-reply thresholds are calibrated at nominal5% using training-side control maxima with strict >. The warning column always concerns immediate leaking replies, even when the model was trained on the round label. Family-bootstrap intervals condition on these fitted single-seed models. No outcomes were used to select the subsequent fixed layer18.

Forecasting streams (reasoning and incoming) are shown above. Action-time aggregates remain pending and must not be substituted with the partial folds. Exact matching nulls, lead measurements and prevention estimates will be reported with the smaller LOSO run.

Reproduce: `experiments/E05-probes/.venv/bin/python experiments/E05-probes/stream_capture_interim.py --out runs/20261026-0822-e05-expanded-stream --data runs/20261026-0813-e05-expanded-stream-data`. Existing per-fold model/scores/fit files are the source; no fits are performed by this script.
