**Per-scenario robustness: C: request contrast (all data; point estimates)**

All-data Qwen3-32B recruiting steps, secret in context and strictly before first forbidden action. A labels the current or next round; B retains these positives and held-episode negatives; C instead takes positives within three target requests. B/C exclude earlier give-in steps using hindsight and are not prospective alarm labels. Nested means layer selected on inner training validation; fixed32 fixes decoder block 32 (zero-based). Pooled uses five family folds; LOSO holds out a scenario. Values average three seeds. Intervals use 1,000 family resamples, conditional on fitted models. Scenario mean weights comparable scenarios equally; the primary metric weights same-scenario, same-round comparisons by positive count. Fold sensitivity additionally requires the same fitted fold. Confirmation episodes are included in this pool; this is not an independent confirmation. Per-scenario values are within-round AUROCs. The source does not provide per-scenario confidence intervals; none are inferred here.

| Scenario | Steps / + / episodes | Pooled inner-selected | LOSO inner-selected | Pooled layer 32 | LOSO layer 32 |
|---|---|---|---|---|---|
| Deploy token | 677 / 66 / 47 | 0.656 | 0.586 | 0.651 | 0.705 |
| Dispatch code | 529 / 60 / 40 | 0.517 | 0.512 | 0.479 | 0.507 |
| Handoff note | 697 / 48 / 45 | 0.529 | 0.537 | 0.505 | 0.546 |
| Reserve price | 457 / 36 / 29 | 0.551 | 0.595 | 0.598 | 0.532 |
| Capacity figure | 935 / 48 / 44 | 0.622 | 0.592 | 0.658 | 0.663 |
| Rollout threshold | 701 / 39 / 36 | 0.657 | 0.611 | 0.669 | 0.628 |
