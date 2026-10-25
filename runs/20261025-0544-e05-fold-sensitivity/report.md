# Frozen-score fold sensitivity (post hoc)

No refits or GPU work. Original scenario × round estimates remain predeclared. The sensitivity adds fitted fold to each stratum, separately for each seed, then averages the three seed AUROCs. Only eligible recruiting rows enter ranking. Strata without both labels are omitted; per-seed positive coverage is in metrics.json. Differences can reflect changed comparable rows as well as cross-fold score shifts. No new confidence intervals are estimated.

| Analysis | Method | Predeclared | Post hoc fold × scenario × round |
|---|---|---:|---:|
| pooled | nested | 0.521728 | 0.551985 |
| pooled | fixed32 | 0.575645 | 0.615842 |
| pooled | band26_30 | 0.550236 | 0.585857 |
| pooled | dom32 | 0.457036 | 0.511617 |
| pooled | mlp | unavailable | unavailable |
| pooled | turn | 0.500000 | 0.500000 |
| pooled | length | 0.484427 | 0.531489 |
| pooled | scenario_only | 0.316270 | 0.500000 |
| pooled | scenario_round | 0.292789 | 0.500000 |
| pooled | metadata_base | 0.280042 | 0.463870 |
| pooled | metadata_probe | 0.367509 | 0.545139 |
| pooled | shuffled32 | 0.471711 | 0.518698 |
| loso | nested | 0.551399 | 0.551399 |
| loso | fixed32 | 0.546971 | 0.546971 |
| loso | band26_30 | 0.539294 | 0.539294 |
| loso | dom32 | 0.451730 | 0.451730 |
| loso | mlp | 0.519470 | 0.519470 |
| loso | turn | 0.500000 | 0.500000 |
| loso | length | 0.484427 | 0.484427 |
| loso | scenario_only | 0.500000 | 0.500000 |
| loso | scenario_round | 0.500000 | 0.500000 |
| loso | metadata_base | 0.480931 | 0.480931 |
| loso | metadata_probe | 0.544064 | 0.544064 |
| loso | shuffled32 | unavailable | unavailable |
| v2 | nested | 0.631838 | 0.679153 |
| v2 | fixed32 | 0.662859 | 0.697619 |
| v2 | band26_30 | 0.633599 | 0.668162 |
| v2 | dom32 | 0.638386 | 0.668818 |
| v2 | mlp | 0.635163 | 0.678973 |
| v2 | turn | 0.500000 | 0.500000 |
| v2 | length | 0.491632 | 0.518973 |
| v2 | scenario_only | 0.445878 | 0.500000 |
| v2 | scenario_round | 0.368166 | 0.500000 |
| v2 | metadata_base | 0.348095 | 0.405382 |
| v2 | metadata_probe | 0.514998 | 0.579065 |
| v2 | shuffled32 | 0.373489 | 0.400493 |

Pooled MLP was not fitted in the original recipe. Its saved v2 and LOSO scores are included; no new fit was made. Shuffled32 uses its saved shuffled labels, as in the original null analysis.

## E06 score export

`probe_scores.csv` contains the inner-selected (nested) logistic probe, one row per `(row_id, analysis, seed)`: 29,214 records. `row_id` and `step_id` both use E06’s `episode::request_idx=N` identifier; `row` is the original integer E05 index. Pooled and LOSO each have 4,184 rows × 3 seeds; v2 has 1,370 × 3. Scores are untransformed saved decision scores. Control and alone rows are included for alarm evaluation; filter `condition == recruiting` for headline ranking. Fold labels are analysis- and seed-specific.

All source episode/request/hash identities match the pre-exported E06 fold table; pooled and LOSO eligible indices match exactly. CSV keys, finite scores, fold assignments and round-trip hashes are checked. For calibration, use the original fit split/calibration files: this export contains OOF scores, not training-fold calibration predictions. Existing frozen threshold arrays remain in the source predictions.npz files.

Sources: `20261025-0337-e05-replay2-data`, `20261025-0340-e05-replay2-fits`, `20261025-0240-e05-replay2-folds`.

Independent validation: all 4,184 E06 main step IDs match the pooled export exactly; every exported request hash matches the E06 step table. All post-hoc scores also match an independent per-stratum sklearn AUROC calculation to 1e-12.
