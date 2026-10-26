## Post hoc descriptive publication-route subgroups

This subgroup analysis was requested after the plan was frozen. No refits, layer reselection or threshold recalibration were performed. Plain text means the first qualifying publication is a final assistant reply without tool calls; tool arguments means a successful send_message or public-file write. Each route is compared against the same nonleaking-call negatives, excluding positives of the other route.

| Split / route | Positive calls | Same negative calls | AUROC [95% family CI] | Positive calls caught (seeds42/43/44) | Mean catch rate |
|---|---:|---:|---|---|---:|
| loso/plain_assistant_text | 47 | 4743 | 0.922 [0.871, 0.963] | 36 / 39 / 43 | 83.7% |
| loso/tool_call_arguments | 54 | 4743 | 0.979 [0.963, 0.992] | 51 / 50 / 53 | 95.1% |
| pooled/plain_assistant_text | 47 | 4743 | 0.906 [0.862, 0.945] | 36 / 43 / 41 | 85.1% |
| pooled/tool_call_arguments | 54 | 4743 | 0.966 [0.940, 0.984] | 50 / 51 / 53 | 95.1% |

Catches use the saved per-fold strict >5%-control-reply thresholds. They are observational call-level warning opportunities, not measured intervention success or episode-level catch rates. A tool-call-only filter cannot block a plain final text publication; a general output filter can still match the exact protected string in that text. These data do not demonstrate an advantage over such an output filter.
