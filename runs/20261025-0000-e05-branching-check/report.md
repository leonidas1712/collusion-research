# Frozen v1 probe scores versus branching outcomes

Run `20261025-0000-e05-branching-check`. Parents: `20261024-1937-e05-probe-core`, `20261024-2001-e01-branching-scaleup`. CPU only; no model inference or refitting.

Of 34 recruiting branch points, **34** match a replayed first target request in their parent branch round; **23** have an eligible frozen OOF probe score. All 170 continuation files are complete (five per point), and outcomes agree with the saved summaries.

| Score timing | Scored points | Parent episodes | Families | Spearman ρ | 95% family-bootstrap CI |
|---|---:|---:|---:|---:|---:|
| First parent request at round t | 23 | 20 | 20 | 0.527 | [0.178, 0.772] |
| Last scored parent request before t | 23 | 20 | 20 | 0.149 | [-0.299, 0.550] |

Unscored points: 6 from invalid episodes and 5 from valid episodes before token exposure. All 11 unscored requests lack token exposure; eligibility remains frozen.

Primary per-seed Spearman: [0.406884123400437, 0.6500016079218599, 0.11818211053124726]. Pre-branch sensitivity: [0.21554165873079859, 0.04164512466339189, 0.051212247896873814].

Scores are the arithmetic mean of the three frozen inner-selected logistic OOF logits. No layer, seed or score transformation was selected using branch outcomes. Confidence intervals resample whole families (including repeated early/late points) 2,000 times. Five reruns yield coarse fractions; these intervals condition on the observed fractions and do not separately model binomial uncertainty. No IID p-value is claimed.

## Timing and matching caveat

Branches restart before the peer speaks in round t. The primary saved target prompt already contains the original peer message from that round. Only 0/170 rerun target requests exactly match that full original request. Removing the respective newly delivered peer messages reproduces the same target history in all reruns. Thus the primary correlation is a parent-step association, not a clean estimate from an identical pre-branch target input. The sensitivity uses the latest eligible earlier target call; that is strictly before branching, but it is still not an activation at the exact reconstructed checkpoint.

Exact episode/request joins and SHA256 checks link every matched parent score to its replayed input. All points without finite frozen scores remain listed in points.json and metrics.json; no score was imputed and no new probe was fit. Parent outcome and early/late phase influenced point selection, so this is a selected-sample exploratory association. Multiple points may share a parent episode/family. The three-round outcome differs from the eventual-publication label used to train the probe.

![Branching association](branching-spearman.png)

Artifacts: points.json (all joins, exclusions, rerun counts and scores), metrics.json, PNG/SVG plot. The original v1 observation/reporting/mock-tool limitations still apply. The other APA-59 analyses remain pending v2.
