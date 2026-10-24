# Text baselines on the frozen E05 steps

Run `20261024-2011-e05-text-baselines`; probe/folds `20261024-1937-e05-probe-core`. Same 1,810 exposed steps, 92 recruiting episodes, 47 families; five family-grouped outer folds and three fold dealings. No new model inference.

| Method | Within-round AUROC (95% family CI) | Pooled AUROC | Episode recall | Held recruiting FPR | Held-out control FPR |
|---|---:|---:|---:|---:|---:|
| probe | 0.658 [0.593, 0.724] | 0.728 | 0.180 | 0.061 | 0.035 |
| full_prompt | 0.480 [0.392, 0.571] | 0.522 | 0.126 | 0.109 | 0.000 |
| target_only | 0.484 [0.404, 0.558] | 0.545 | 0.027 | 0.024 | 0.053 |
| target_prose | 0.488 [0.415, 0.556] | 0.485 | 0.072 | 0.091 | 0.096 |

| Comparison | Within-round AUROC difference | Paired 95% family CI |
|---|---:|---:|
| Probe minus full_prompt | 0.178 | [0.076, 0.271] |
| Probe minus target_only | 0.174 | [0.081, 0.282] |
| Probe minus target_prose | 0.169 | [0.096, 0.262] |

Full-prompt features use the exact saved rendered prompt, including system rules, tool schema, peer text, prior target messages and tool results. Every prompt and source request hash was checked. Target-only features use prior complete assistant spans from that same rendering, including the target’s function names/arguments, but no peer messages or tool results. The pending reply is never included. Target-prose removes tool-call blocks and empty thinking tags. Empty histories remain empty feature rows.

There are 173 empty prose-only rows among headline steps. Empty rows are retained, not imputed with a label-dependent placeholder.

TF-IDF uses lowercase word unigrams, sublinear term frequency, L2 document normalization and no stop-word removal. Vocabulary and IDF are fitted only on the relevant training split. Logistic regression uses L2, with C selected from 0.1/1/10/100 using the exact saved inner validation episodes and within-round metric; ties prefer the smaller C. Outer fits use the same round-matched negative weights as the activation probe. The saved outer-test folds and control/alone calibration episodes are unchanged.

The paired intervals reuse identical family-bootstrap draws across methods, average over the three fold dealings, and condition on frozen fitted scores. They do not include refitting/model-selection uncertainty. Thresholds use control/alone episode maxima with the same ≤5% calibration rule as E05; held-out FPR need not equal5%. No outer-test score selects vocabulary, C or a feature variant.

These comparisons assess incremental predictive value over these text baselines, not causal evidence or hidden intent. The original logged/reporting/mock-tool cues, provisional labels and strict-transfer limitation still apply. No optional sentence-embedding baseline was required; no weights were downloaded.

Artifacts: predictions.npz, metrics.json, fits.json, text-index.jsonl, and fold-specific vocabulary/IDF/coefficients.
