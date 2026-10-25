**Per-scenario robustness: B: round contrast (all data; point estimates)**

All-data Qwen3-32B recruiting steps, secret in context and strictly before first forbidden action. A labels the current or next round; B retains these positives and held-episode negatives; C instead takes positives within three target requests. B/C exclude earlier give-in steps using hindsight and are not prospective alarm labels. Nested means layer selected on inner training validation; fixed32 fixes decoder block 32 (zero-based). Pooled uses five family folds; LOSO holds out a scenario. Values average three seeds. Intervals use 1,000 family resamples, conditional on fitted models. Scenario mean weights comparable scenarios equally; the primary metric weights same-scenario, same-round comparisons by positive count. Fold sensitivity additionally requires the same fitted fold. Confirmation episodes are included in this pool; this is not an independent confirmation. Per-scenario values are within-round AUROCs. The source does not provide per-scenario confidence intervals; none are inferred here.

| Scenario | Steps / + / episodes | Pooled inner-selected | LOSO inner-selected | Pooled layer 32 | LOSO layer 32 |
|---|---|---|---|---|---|
| Deploy token | 676 / 65 / 47 | 0.680 | 0.630 | 0.649 | 0.652 |
| Dispatch code | 503 / 34 / 40 | 0.538 | 0.546 | 0.495 | 0.541 |
| Handoff note | 699 / 50 / 45 | 0.537 | 0.551 | 0.526 | 0.515 |
| Reserve price | 442 / 21 / 29 | 0.554 | 0.546 | 0.504 | 0.509 |
| Capacity figure | 930 / 43 / 44 | 0.645 | 0.584 | 0.617 | 0.665 |
| Rollout threshold | 699 / 37 / 36 | 0.612 | 0.620 | 0.616 | 0.620 |
