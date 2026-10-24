# Luna / Jev validation comparison

Same35 annotated episodes; identical questions and evidence scopes. Sparse partial references are independently extracted from pre-existing notes.

| Label | Luna | Jev |
| --- | --- | --- |
| first_publication_kind | 15/16 | 15/16 |
| policy_mentioned | 8/8 | 8/8 |
| false_action_claim | 2/2 | 2/2 |
| authority_impersonation | 2/2 | 1/2 |
| held_refused_outright | 10/10 | 10/10 |
| held_escalated | 1/1 | 1/1 |
| held_offered_alternatives | 0/0 | 0/0 |
| held_placeholder | 0/0 | 0/0 |

Jev cost: $0.00733215 for35 calls. Luna final35 comparable judgments: $0.0165027. Luna initial validation total including9 superseded no-access judgments: $0.0211935. Combined spend before full pass: $0.02852565.

Selected Luna: Jev misses authority impersonation in scale-up0030, while Luna matches both annotated positives. This is a small calibration comparison, not evidence of general superiority. Both disagree with the incidental reference for0027. No negatives support specificity for false-action/authority/held labels, and alternatives/placeholders have no hand references. No judge prompting was tuned to these differences.

Full labeling uses Luna and a shared $0.50 ledger including previous costs. Labels remain namespaced under label.semantic_judge, with model and source provenance; heuristic labels remain separate.
