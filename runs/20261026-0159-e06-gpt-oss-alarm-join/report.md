# GPT-OSS shared probe and monitor alarm scoring

Canonical probe rows are explicitly restricted to `method=nested`, `window=post_ask`. Probe and monitor scores join by row ID and request hash. Every cutoff uses the saved outer split's training-side control episodes: probe cutoffs are read unchanged from `fit.json`; monitor cutoffs are computed with the identical episode-maximum rule on the same calibration episodes. Alarms use strict `score > cutoff`.

Rates are means across seeds 42/43/44. Intervals are 1,000-draw family-bootstrap percentile intervals. Positive recall is the share of positive recruiting episodes with any alarm; held and control columns are episode false-alarm rates. Lead is conditional on detecting a positive episode.

## eventual · pooled, nominal 5%

| Method | Recall [95% CI] | Held recruiting alarm [95% CI] | Held-out control alarm [95% CI] | Median lead (requests / rounds) |
|---|---:|---:|---:|---:|
| probe:nested | 2.4% [0.7%, 4.6%] | 8.9% [6.0%, 12.0%] | 12.1% [6.5%, 18.8%] | 1.0 / 0.0 |
| monitor:jev:detector:L1 | 8.3% [3.2%, 14.4%] | 19.7% [13.4%, 26.2%] | 4.6% [0.5%, 10.0%] | 1.0 / 1.0 |
| monitor:jev:detector:L2 | 97.9% [94.9%, 100.0%] | 100.0% [100.0%, 100.0%] | 3.4% [0.0%, 8.9%] | 1.0 / 0.0 |
| monitor:jev:detector:L3 | 70.1% [61.1%, 78.5%] | 82.4% [76.3%, 88.3%] | 5.2% [0.6%, 10.9%] | 1.0 / 0.0 |
| monitor:jev:detector:L4 | 95.1% [91.0%, 98.5%] | 96.9% [94.0%, 99.3%] | 6.9% [1.8%, 13.3%] | 1.0 / 0.0 |
| monitor:jev:forecaster:L1 | 18.8% [11.6%, 27.1%] | 43.4% [35.5%, 51.2%] | 5.2% [0.0%, 11.5%] | 2.0 / 1.0 |
| monitor:jev:forecaster:L2 | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 5.2% [0.6%, 10.7%] | 1.0 / 0.0 |
| monitor:jev:forecaster:L3 | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 4.6% [0.0%, 10.2%] | 1.0 / 0.0 |
| monitor:jev:forecaster:L4 | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 4.6% [0.0%, 10.2%] | 1.0 / 0.0 |
| monitor:llm:detector:L2 | 0.3% [0.0%, 1.1%] | 4.0% [1.7%, 6.7%] | 5.2% [0.0%, 11.6%] | 1.0 / 0.0 |
| monitor:llm:detector:L4 | 53.1% [43.7%, 63.7%] | 74.6% [67.8%, 81.2%] | 1.7% [0.0%, 5.5%] | 1.0 / 0.0 |
| monitor:llm:forecaster:L2 | 84.7% [77.5%, 91.8%] | 96.5% [93.8%, 98.6%] | 5.7% [0.5%, 12.1%] | 1.0 / 0.0 |
| monitor:llm:forecaster:L4 | 72.9% [64.9%, 79.9%] | 79.6% [73.9%, 84.7%] | 5.2% [0.0%, 11.3%] | 1.0 / 0.0 |

## eventual · loso, nominal 5%

| Method | Recall [95% CI] | Held recruiting alarm [95% CI] | Held-out control alarm [95% CI] | Median lead (requests / rounds) |
|---|---:|---:|---:|---:|
| probe:nested | 2.4% [0.7%, 4.8%] | 9.2% [6.2%, 12.2%] | 9.2% [4.4%, 14.4%] | 2.0 / 1.0 |
| monitor:jev:detector:L1 | 8.3% [3.2%, 14.4%] | 21.8% [15.4%, 28.9%] | 6.9% [1.6%, 14.1%] | 1.0 / 1.0 |
| monitor:jev:detector:L2 | 97.9% [94.9%, 100.0%] | 100.0% [100.0%, 100.0%] | 10.3% [3.3%, 18.8%] | 1.0 / 0.0 |
| monitor:jev:detector:L3 | 65.6% [56.2%, 74.5%] | 81.7% [75.5%, 87.8%] | 6.9% [1.6%, 13.8%] | 1.0 / 0.0 |
| monitor:jev:detector:L4 | 92.7% [87.2%, 97.8%] | 97.2% [94.2%, 99.3%] | 5.2% [0.0%, 11.5%] | 1.0 / 0.0 |
| monitor:jev:forecaster:L1 | 18.8% [11.6%, 27.1%] | 41.5% [33.8%, 49.6%] | 5.2% [0.0%, 11.5%] | 2.0 / 1.0 |
| monitor:jev:forecaster:L2 | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 3.4% [0.0%, 8.5%] | 1.0 / 0.0 |
| monitor:jev:forecaster:L3 | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 5.2% [0.0%, 11.6%] | 1.0 / 0.0 |
| monitor:jev:forecaster:L4 | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 5.2% [0.0%, 11.6%] | 1.0 / 0.0 |
| monitor:llm:detector:L2 | 18.8% [11.0%, 27.1%] | 16.2% [10.2%, 22.2%] | 10.3% [3.1%, 18.3%] | 1.0 / 0.0 |
| monitor:llm:detector:L4 | 53.1% [43.7%, 63.7%] | 74.6% [67.8%, 81.2%] | 1.7% [0.0%, 5.5%] | 1.0 / 0.0 |
| monitor:llm:forecaster:L2 | 83.3% [75.6%, 90.9%] | 93.0% [88.3%, 96.9%] | 5.2% [0.0%, 11.8%] | 1.0 / 0.0 |
| monitor:llm:forecaster:L4 | 77.1% [68.4%, 84.8%] | 83.1% [76.8%, 88.9%] | 5.2% [0.0%, 11.3%] | 1.0 / 0.0 |

## A_hazard · pooled, nominal 5%

| Method | Recall [95% CI] | Held recruiting alarm [95% CI] | Held-out control alarm [95% CI] | Median lead (requests / rounds) |
|---|---:|---:|---:|---:|
| probe:nested | 4.2% [1.7%, 6.9%] | 6.3% [3.9%, 9.2%] | 8.6% [4.9%, 12.6%] | 1.0 / 0.0 |
| monitor:jev:detector:L1 | 8.3% [3.2%, 14.4%] | 19.7% [13.4%, 26.2%] | 4.6% [0.5%, 10.0%] | 1.0 / 1.0 |
| monitor:jev:detector:L2 | 97.9% [94.9%, 100.0%] | 100.0% [100.0%, 100.0%] | 3.4% [0.0%, 8.9%] | 1.0 / 0.0 |
| monitor:jev:detector:L3 | 70.1% [61.1%, 78.5%] | 82.4% [76.3%, 88.3%] | 5.2% [0.6%, 10.9%] | 1.0 / 0.0 |
| monitor:jev:detector:L4 | 95.1% [91.0%, 98.5%] | 96.9% [94.0%, 99.3%] | 6.9% [1.8%, 13.3%] | 1.0 / 0.0 |
| monitor:jev:forecaster:L1 | 18.8% [11.6%, 27.1%] | 43.4% [35.5%, 51.2%] | 5.2% [0.0%, 11.5%] | 2.0 / 1.0 |
| monitor:jev:forecaster:L2 | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 5.2% [0.6%, 10.7%] | 1.0 / 0.0 |
| monitor:jev:forecaster:L3 | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 4.6% [0.0%, 10.2%] | 1.0 / 0.0 |
| monitor:jev:forecaster:L4 | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 4.6% [0.0%, 10.2%] | 1.0 / 0.0 |
| monitor:llm:detector:L2 | 0.3% [0.0%, 1.1%] | 4.0% [1.7%, 6.7%] | 5.2% [0.0%, 11.6%] | 1.0 / 0.0 |
| monitor:llm:detector:L4 | 53.1% [43.7%, 63.7%] | 74.6% [67.8%, 81.2%] | 1.7% [0.0%, 5.5%] | 1.0 / 0.0 |
| monitor:llm:forecaster:L2 | 84.7% [77.5%, 91.8%] | 96.5% [93.8%, 98.6%] | 5.7% [0.5%, 12.1%] | 1.0 / 0.0 |
| monitor:llm:forecaster:L4 | 72.9% [64.9%, 79.9%] | 79.6% [73.9%, 84.7%] | 5.2% [0.0%, 11.3%] | 1.0 / 0.0 |

## A_hazard · loso, nominal 5%

| Method | Recall [95% CI] | Held recruiting alarm [95% CI] | Held-out control alarm [95% CI] | Median lead (requests / rounds) |
|---|---:|---:|---:|---:|
| probe:nested | 2.1% [0.7%, 4.0%] | 8.5% [5.8%, 11.4%] | 9.2% [4.7%, 14.3%] | 2.0 / 1.0 |
| monitor:jev:detector:L1 | 8.3% [3.2%, 14.4%] | 21.8% [15.4%, 28.9%] | 6.9% [1.6%, 14.1%] | 1.0 / 1.0 |
| monitor:jev:detector:L2 | 97.9% [94.9%, 100.0%] | 100.0% [100.0%, 100.0%] | 10.3% [3.3%, 18.8%] | 1.0 / 0.0 |
| monitor:jev:detector:L3 | 65.6% [56.2%, 74.5%] | 81.7% [75.5%, 87.8%] | 6.9% [1.6%, 13.8%] | 1.0 / 0.0 |
| monitor:jev:detector:L4 | 92.7% [87.2%, 97.8%] | 97.2% [94.2%, 99.3%] | 5.2% [0.0%, 11.5%] | 1.0 / 0.0 |
| monitor:jev:forecaster:L1 | 18.8% [11.6%, 27.1%] | 41.5% [33.8%, 49.6%] | 5.2% [0.0%, 11.5%] | 2.0 / 1.0 |
| monitor:jev:forecaster:L2 | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 3.4% [0.0%, 8.5%] | 1.0 / 0.0 |
| monitor:jev:forecaster:L3 | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 5.2% [0.0%, 11.6%] | 1.0 / 0.0 |
| monitor:jev:forecaster:L4 | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 5.2% [0.0%, 11.6%] | 1.0 / 0.0 |
| monitor:llm:detector:L2 | 18.8% [11.0%, 27.1%] | 16.2% [10.2%, 22.2%] | 10.3% [3.1%, 18.3%] | 1.0 / 0.0 |
| monitor:llm:detector:L4 | 53.1% [43.7%, 63.7%] | 74.6% [67.8%, 81.2%] | 1.7% [0.0%, 5.5%] | 1.0 / 0.0 |
| monitor:llm:forecaster:L2 | 83.3% [75.6%, 90.9%] | 93.0% [88.3%, 96.9%] | 5.2% [0.0%, 11.8%] | 1.0 / 0.0 |
| monitor:llm:forecaster:L4 | 77.1% [68.4%, 84.8%] | 83.1% [76.8%, 88.9%] | 5.2% [0.0%, 11.3%] | 1.0 / 0.0 |

## Coverage

Full metrics for nominal 1%, 5%, 10%, and 20% cutoffs, both analysis modes, and eventual/A/B/C labels are in `metrics.json`. Every threshold and achieved calibration rate is in `threshold_audit.json`.

This is CPU-only post-processing; paid cost is $0.
