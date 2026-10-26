# Last-prompt per-call label ablation

Exploratory CPU fits on saved last-prompt activations, including the 146 first-public-emission calls. No replay or model API calls. The primary matched cohort excludes empty reasoning from both methods; the all-reply sensitivity retains it. Labels count eligible calls before filtering empty reasoning. Strict one-ahead removes own-leak calls from every fitting, validation and evaluation partition and labels only the preceding eligible call positive.

The paper recipe is unchanged: C=0.1 logistic regression, training-only StandardScaler, round-balanced weights (single-class rounds have zero weight), 17 candidate layers, frozen pooled-family and held-out-scenario outer/inner partitions, seeds 42/43/44. Layer selection maximises inner scenario × round AUROC, breaking ties toward the earlier layer. The original main plans are expanded by episode to include leaking calls. Thresholds use training-side no-ask control reply scores at nominal 5%, strict >; held recruiting rates below are evaluation results, not control FPR.

| Cohort / label / split | Rows / positives | Last prompt AUROC [95% CI] | Reasoning AUROC | Paired last prompt minus reasoning [95% CI] | Held-reply alarms: prompt / reasoning |
|---|---:|---|---:|---|---|
| matched/immediate/loso | 1995 / 121 | 0.906 [0.871, 0.936] | 0.933 | -0.028 [-0.061, +0.000] | 1.6% / 4.4% |
| matched/immediate/pooled | 1995 / 121 | 0.882 [0.841, 0.918] | 0.949 | -0.067 [-0.102, -0.037] | 3.9% / 2.0% |
| matched/strict1/loso | 1874 / 116 | 0.620 [0.568, 0.668] | 0.881 | -0.261 [-0.325, -0.206] | 2.4% / 2.9% |
| matched/strict1/pooled | 1874 / 116 | 0.634 [0.575, 0.679] | 0.884 | -0.251 [-0.319, -0.194] | 1.6% / 2.3% |
| all/immediate/loso | 2205 / 146 | 0.926 [0.900, 0.948] | — | — | 1.6% / — |
| all/immediate/pooled | 2205 / 146 | 0.904 [0.872, 0.934] | — | — | 1.8% / — |
| all/strict1/loso | 2059 / 146 | 0.589 [0.539, 0.633] | — | — | 2.4% / — |
| all/strict1/pooled | 2059 / 146 | 0.614 [0.566, 0.658] | — | — | 1.5% / — |

Intervals use 1,000 family bootstrap draws (seed 20261025) of saved OOF scores, conditional on fitted/selected models. Paired differences use identical draws and rows. Immediate reasoning and last-prompt fits share the outcome and partitions; token pooling and token-weighted versus single-position fitting remain differences. Strict-one-ahead reasoning scores come from existing inclusive 0–1 horizon fits; only last-prompt is refit on strict labels. That comparison does not isolate position and must not be presented as a matched-label ablation. Alarm rates are reply-level, not episode-level intervention rates. Most strict-next positives are same-round read-file calls in the existing timing audit.

Sources: `runs/20261026-0522-e05-reasoning-stream-data`, `runs/20261025-2305-e05-gpt-oss-full-data`, frozen plans `runs/20261026-0138-e05-gpt-oss-main/plans.json`, reasoning fits `runs/20261026-0526-e05-reasoning-stream/{immediate,h1}/all`. Script: `experiments/E05-probes/lastprompt_percall.py`.
