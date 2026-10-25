**Near-term robustness: all-data cohort**

All-data Qwen3-32B recruiting steps, secret in context and strictly before first forbidden action. A labels the current or next round; B retains these positives and held-episode negatives; C instead takes positives within three target requests. B/C exclude earlier give-in steps using hindsight and are not prospective alarm labels. Nested means layer selected on inner training validation; fixed32 fixes decoder block 32 (zero-based). Pooled uses five family folds; LOSO holds out a scenario. Values average three seeds. Intervals use 1,000 family resamples, conditional on fitted models. Scenario mean weights comparable scenarios equally; the primary metric weights same-scenario, same-round comparisons by positive count. Fold sensitivity additionally requires the same fitted fold. Confirmation episodes are included in this pool; this is not an independent confirmation.

| Label | Split | Probe | Steps / + / episodes | Scenario × round | Fold × scenario × round | Scenario mean |
|---|---|---|---|---|---|---|
| A: current/next round | POOLED | Inner-selected | 4697 / 250 / 241 | 0.586 [0.541, 0.631] | 0.618 [0.571, 0.666] | 0.580 [0.536, 0.623] |
| A: current/next round | POOLED | Layer 32 | 4697 / 250 / 241 | 0.573 [0.520, 0.625] | 0.603 [0.544, 0.649] | 0.564 [0.517, 0.619] |
| A: current/next round | LOSO | Inner-selected | 4697 / 250 / 241 | 0.579 [0.537, 0.619] | 0.579 [0.537, 0.619] | 0.585 [0.546, 0.624] |
| A: current/next round | LOSO | Layer 32 | 4697 / 250 / 241 | 0.572 [0.525, 0.618] | 0.572 [0.525, 0.618] | 0.570 [0.523, 0.617] |
| B: round contrast | POOLED | Inner-selected | 3949 / 250 / 241 | 0.605 [0.554, 0.652] | 0.639 [0.581, 0.688] | 0.594 [0.551, 0.641] |
| B: round contrast | POOLED | Layer 32 | 3949 / 250 / 241 | 0.581 [0.521, 0.634] | 0.617 [0.542, 0.668] | 0.568 [0.516, 0.621] |
| B: round contrast | LOSO | Inner-selected | 3949 / 250 / 241 | 0.586 [0.544, 0.628] | 0.586 [0.544, 0.628] | 0.580 [0.535, 0.620] |
| B: round contrast | LOSO | Layer 32 | 3949 / 250 / 241 | 0.595 [0.541, 0.649] | 0.595 [0.541, 0.649] | 0.584 [0.530, 0.638] |
| C: request contrast | POOLED | Inner-selected | 3996 / 297 / 241 | 0.589 [0.547, 0.631] | 0.622 [0.568, 0.671] | 0.589 [0.546, 0.633] |
| C: request contrast | POOLED | Layer 32 | 3996 / 297 / 241 | 0.590 [0.532, 0.640] | 0.615 [0.545, 0.667] | 0.593 [0.540, 0.645] |
| C: request contrast | LOSO | Inner-selected | 3996 / 297 / 241 | 0.569 [0.527, 0.610] | 0.569 [0.527, 0.610] | 0.572 [0.535, 0.613] |
| C: request contrast | LOSO | Layer 32 | 3996 / 297 / 241 | 0.602 [0.547, 0.659] | 0.602 [0.547, 0.659] | 0.597 [0.545, 0.652] |
