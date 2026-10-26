# Does a protected-file read explain strict-one-ahead ranking?

On the same 1,874 replies, 108/116 positives and 49/1,758 negatives call `read_file` on a protected source file. Another 3 positives have malformed read-file names and are excluded from this exact-name baseline.

The tool-call baseline sees the call produced after reasoning, so it is a diagnostic, not an information-matched pre-tool monitor. The lexical baseline is prefix-causal: case-insensitive `read` or `file`, with non-letter boundaries (underscores count as separators), evaluated after each observed reasoning token and aggregated by running maximum. Both are post hoc additions and use no fitting or new API/GPU calls.

| Split / subset / method | Rows / positives | Within scenario × round AUROC [95% CI] |
|---|---|---|
| pooled/own_protected_read_call | 1874 / 116 | 0.851 [0.817, 0.887] |
| pooled/reasoning_read_file_keyword | 1874 / 116 | 0.657 [0.621, 0.693] |
| pooled/protected_reads_only/token_max | 157 / 108 | 0.854 [0.781, 0.915] |
| pooled/protected_reads_only/token_mean | 157 / 108 | 0.943 [0.882, 0.989] |
| pooled/protected_reads_only/frozen_last_prompt_A | 157 / 108 | 0.532 [0.427, 0.646] |
| loso/own_protected_read_call | 1874 / 116 | 0.851 [0.817, 0.887] |
| loso/reasoning_read_file_keyword | 1874 / 116 | 0.657 [0.621, 0.693] |
| loso/protected_reads_only/token_max | 157 / 108 | 0.853 [0.782, 0.911] |
| loso/protected_reads_only/token_mean | 157 / 108 | 0.965 [0.925, 0.994] |
| loso/protected_reads_only/frozen_last_prompt_A | 157 / 108 | 0.540 [0.455, 0.623] |

## Paired comparison on all 1,874 replies

- pooled: MAX probe minus read-step baseline = 0.033, paired family-bootstrap 95% CI [-0.015817771517416184, 0.08348951071519793].
- loso: MAX probe minus read-step baseline = 0.030, paired family-bootstrap 95% CI [-0.01952723013816531, 0.07687089085542381].

The conditional read-only metric retains 98 of 108 positive replies in strata with both classes (90.7% positive coverage); single-class strata do not contribute. The read-only subset compares positive read calls with negative read calls, using the saved inclusive-horizon models without refitting. Confidence intervals resample families 1,000 times (seed 20261025) and average seeds 42/43/44. A high conditional score would not identify a causal mechanism; a low score would support a read-step confound. The frozen last-prompt secondary retains its different training label.

Source: `runs/20261026-0526-e05-reasoning-stream/probe_scores.csv`, SHA256 `6bcd3948f3f5a4562d3157007b0cb941dda938e4957ef4b9b71214218831c97b`. Script: `experiments/E05-probes/reasoning_stream_readstep.py`. Audit: `/Users/leo/collusion-research/runs/20261026-1223-e05-stream-readstep`.
