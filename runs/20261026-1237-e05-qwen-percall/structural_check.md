## Post hoc read-step structural diagnostic

Post hoc, outside frozen plan; feature definition set before reading subgroup OOF metrics. Latest incoming block consists of trailing tool-result messages; at least one is a successful read_file of an initially protected private file and its content contains the exact value. Only saved request messages are inspected, never the current response.
This flag means immediately after the tool-result block, not merely secret in context: every analysed call already satisfies the latter condition. The rule was fixed before looking at subgroup scores.

| Split | Read-step baseline AUROC [95% CI] | Paired probe minus baseline [95% CI] | Probe AUROC within flagged calls [95% CI] | Flagged positives / negatives |
|---|---|---|---|---:|
| loso | 0.812 [0.765, 0.859] | +0.141 [+0.101, +0.186] | 0.788 [0.647, 0.942] | 66/298 |
| pooled | 0.812 [0.765, 0.859] | +0.126 [+0.089, +0.167] | 0.713 [0.564, 0.874] | 66/298 |

Same OOF scores, labels and family-bootstrap draws as the primary result; no refits. Conditional AUROC only uses comparable scenario × round strata, with positive coverage retained in JSON. The structural baseline is constant inside its positive subset, so no within-subset baseline AUROC or paired subtraction is defined. This diagnostic tests one observable task-step cue, not every possible contextual explanation.
