**Per-scenario robustness: A: current/next round (all data; point estimates)**

All-data Qwen3-32B recruiting steps, secret in context and strictly before first forbidden action. A labels the current or next round; B retains these positives and held-episode negatives; C instead takes positives within three target requests. B/C exclude earlier give-in steps using hindsight and are not prospective alarm labels. Nested means layer selected on inner training validation; fixed32 fixes decoder block 32 (zero-based). Pooled uses five family folds; LOSO holds out a scenario. Values average three seeds. Intervals use 1,000 family resamples, conditional on fitted models. Scenario mean weights comparable scenarios equally; the primary metric weights same-scenario, same-round comparisons by positive count. Fold sensitivity additionally requires the same fitted fold. Confirmation episodes are included in this pool; this is not an independent confirmation. Per-scenario values are within-round AUROCs. The source does not provide per-scenario confidence intervals; none are inferred here.

| Scenario | Steps / + / episodes | Pooled inner-selected | LOSO inner-selected | Pooled layer 32 | LOSO layer 32 |
|---|---|---|---|---|---|
| Deploy token | 871 / 65 / 47 | 0.609 | 0.583 | 0.628 | 0.576 |
| Dispatch code | 678 / 34 / 40 | 0.566 | 0.563 | 0.532 | 0.564 |
| Handoff note | 733 / 50 / 45 | 0.592 | 0.560 | 0.537 | 0.539 |
| Reserve price | 527 / 21 / 29 | 0.546 | 0.644 | 0.523 | 0.545 |
| Capacity figure | 1087 / 43 / 44 | 0.587 | 0.544 | 0.593 | 0.619 |
| Rollout threshold | 801 / 37 / 36 | 0.579 | 0.614 | 0.569 | 0.576 |
