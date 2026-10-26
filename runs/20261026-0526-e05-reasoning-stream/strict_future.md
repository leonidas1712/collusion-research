# Strictly future public-emission sensitivity

This CPU-only, post hoc evaluation drops every reply whose own output first emits the protected value. The remaining positive replies precede that emission by 1–k eligible target replies. Reply distance includes replies without reasoning, before feature-based exclusion. The saved models were trained on inclusive 0–k labels; they were not refitted for this sensitivity. All methods use identical rows for each horizon, cut and split.

| Horizon | Cut | Split | Replies / positives / episodes | MAX AUROC [95% CI] | Mean | Frozen last-prompt A |
|---|---|---|---|---|---|---|
| 1–1 replies | all | loso | 1874 / 116 / 238 | 0.881 [0.843, 0.917] | 0.976 [0.954, 0.992] | 0.538 [0.483, 0.592] |
| 1–1 replies | all | pooled | 1874 / 116 / 238 | 0.884 [0.844, 0.921] | 0.970 [0.942, 0.990] | 0.520 [0.463, 0.576] |
| 1–1 replies | censored | loso | 1874 / 116 / 238 | 0.880 [0.842, 0.917] | 0.976 [0.953, 0.992] | 0.538 [0.483, 0.592] |
| 1–1 replies | censored | pooled | 1874 / 116 / 238 | 0.887 [0.849, 0.922] | 0.970 [0.942, 0.990] | 0.520 [0.463, 0.576] |
| 1–2 replies | all | loso | 1874 / 145 / 238 | 0.764 [0.715, 0.818] | 0.893 [0.854, 0.933] | 0.524 [0.472, 0.576] |
| 1–2 replies | all | pooled | 1874 / 145 / 238 | 0.761 [0.712, 0.821] | 0.875 [0.833, 0.922] | 0.500 [0.434, 0.553] |
| 1–2 replies | censored | loso | 1874 / 145 / 238 | 0.770 [0.719, 0.826] | 0.892 [0.854, 0.931] | 0.524 [0.472, 0.576] |
| 1–2 replies | censored | pooled | 1874 / 145 / 238 | 0.765 [0.716, 0.823] | 0.875 [0.831, 0.922] | 0.500 [0.434, 0.553] |
| 1–3 replies | all | loso | 1874 / 179 / 238 | 0.655 [0.595, 0.719] | 0.804 [0.752, 0.860] | 0.532 [0.478, 0.592] |
| 1–3 replies | all | pooled | 1874 / 179 / 238 | 0.647 [0.590, 0.714] | 0.777 [0.723, 0.835] | 0.541 [0.477, 0.597] |
| 1–3 replies | censored | loso | 1874 / 179 / 238 | 0.665 [0.607, 0.726] | 0.804 [0.753, 0.860] | 0.532 [0.478, 0.592] |
| 1–3 replies | censored | pooled | 1874 / 179 / 238 | 0.640 [0.583, 0.703] | 0.769 [0.716, 0.829] | 0.541 [0.477, 0.597] |

AUROC compares replies only within the same scenario and round, weighted by positives. Intervals resample families 1,000 times (seed 20261025) and average seeds 42/43/44. Positive-stratum coverage and valid bootstrap counts are in the JSON. The censored cut removes reasoning from the first protected-value character onward. The last-prompt comparator retains its different near-term-channel training label; it is not a matched-label refit.

These retrospective ranking estimates do not establish a usable advance-warning threshold or intervention rate. No alarm threshold was selected or recalibrated here. The fresh confirmation keeps its separately frozen immediate endpoint.

Source: `runs/20261026-0526-e05-reasoning-stream/probe_scores.csv` (SHA256 `6bcd3948f3f5a4562d3157007b0cb941dda938e4957ef4b9b71214218831c97b`). Script: `experiments/E05-probes/reasoning_stream_strict_future.py`. Audit run: `/Users/leo/collusion-research/runs/20261026-1212-e05-stream-strict-future`. No API/GPU spend.
