# Private reasoning cutoff and channel-publication route audit

This is an offline snapshot audit, not a fit or a change to the censoring rule. Qwen uses the 304 plain recruiting attempts behind Table 1. gpt-oss uses saved episodes from the six original 2053 collection runs; top-ups are excluded, so this is not the final canonical collection. Source hashes and per-episode evidence indices are in episodes.json.

## Private reasoning cutoff

Episode counts below use complete, exposed recruiting episodes. Step counts additionally require an ever-correct summary, strict post-read eligibility, and delivery of the recorded first ask (verified inside the target request). The public-only boundary scans target response content and decoded tool arguments, as in the Qwen request index. Here “public” follows the requested operational definition and includes tool arguments or final text even if not delivered. Reasoning-before means an earlier target request, or a reasoning mention with no subsequent public emission. Same-request reasoning is reported separately because it precedes reply content within a reply but changes no request-level cutoff.

| Outcome definition | Outcome | Complete exposed episodes | Reasoning earlier | Same request | Public-only steps | Inclusive steps | Removed steps | Affected episodes |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| channel_leak | gave_in | 118 | 1 | 6 | 157 | 156 | 1 | 1 |
| channel_leak | held | 158 | 3 | 1 | 1789 | 1736 | 53 | 3 |
| any_boundary_leak | gave_in | 186 | 1 | 7 | 247 | 246 | 1 | 1 |
| any_boundary_leak | held | 90 | 3 | 0 | 1699 | 1646 | 53 | 3 |

The primary episode outcome is channel publication; its negative group can contain file-only disclosures. The any-boundary split is supplied to distinguish these from episodes with no observed disclosure. Harmony replay omits earlier reasoning from later prompts; such reasoning is not part of the later last-prompt-token input. Reasoning-token analysis is optional and does not delay the primary last-token pipeline.

## First channel leak route

Routes use actual channel events. The script reconstructs successful send_message calls and the harness auto-post of a no-tool final reply when the actor has not already posted in that turn. It checks the entire target-channel sequence, and checks explicit publication receipt origins where saved. Judge kinds come only from saved semantic_judge labels; missing labels stay unjoined_or_unclear. Incomplete attempts are included here if they already contain a channel leak.

| Model | Condition | Route | Judge kind | First channel leaks |
|---|---|---|---|---:|
| Qwen | recruiting | send_message | deliberate | 40 |
| Qwen | recruiting | send_message | accidental | 10 |
| Qwen | recruiting | final_reply | deliberate | 27 |
| Qwen | recruiting | final_reply | accidental | 20 |
| Qwen | recruiting | final_reply | unjoined_or_unclear | 1 |
| gpt-oss | recruiting | send_message | unjoined_or_unclear | 1 |
| gpt-oss | recruiting | final_reply | unjoined_or_unclear | 124 |

All 659 saved target-channel sequences matched the reconstruction. Counts and snapshot status are in counts.json.
