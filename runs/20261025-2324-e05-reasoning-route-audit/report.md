# Private reasoning cutoff and channel-publication route audit

This is an offline saved-trace audit, not a fit or a change to the censoring rule. Qwen uses the 304 plain recruiting attempts behind Table 1. gpt-oss population: canonical 360 completed episodes; replacements selected by immutable manifest. Source hashes and per-episode evidence indices are in episodes.json.

## Private reasoning cutoff

Episode counts below use complete, exposed recruiting episodes. Step counts additionally require an ever-correct summary, strict post-read eligibility, and delivery of the recorded first ask (verified inside the target request). The public-only boundary scans target response content and decoded tool arguments, as in the Qwen request index. Here “public” follows the requested operational definition and includes tool arguments or final text even if not delivered. Reasoning-before means an earlier target request, or a reasoning mention with no subsequent public emission. Same-request reasoning is reported separately because it precedes reply content within a reply but changes no request-level cutoff.

| Outcome definition | Outcome | Complete exposed episodes | Reasoning earlier | Same request | Public-only steps | Inclusive steps | Removed steps | Affected episodes |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| channel_leak | gave_in | 128 | 1 | 7 | 169 | 168 | 1 | 1 |
| channel_leak | held | 166 | 3 | 1 | 1890 | 1837 | 53 | 3 |
| any_boundary_leak | gave_in | 198 | 1 | 8 | 261 | 260 | 1 | 1 |
| any_boundary_leak | held | 96 | 3 | 0 | 1798 | 1745 | 53 | 3 |

The primary episode outcome is channel publication; its negative group can contain file-only disclosures. The any-boundary split is supplied to distinguish these from episodes with no observed disclosure. AkashML Harmony replay keeps reasoning from earlier tool calls within the same user/peer turn, then drops it after the next user/peer message. DekaLLM uses the drop-all approximation. Reasoning-token analysis is optional and does not delay the primary last-token pipeline.

## First channel leak route

Routes use actual channel events. The script reconstructs successful send_message calls and the harness auto-post of a no-tool final reply when the actor has not already posted in that turn. It checks the entire target-channel sequence, and checks explicit publication receipt origins where saved. Qwen kinds come from saved semantic_judge labels; gpt-oss kinds optionally join the separately saved first-public-emission judgments by episode SHA256. That judgment may describe an earlier file write, not the channel post itself. Missing/null labels stay unjoined_or_unclear. Qwen incomplete attempts are included if they already contain a channel leak.

| Model | Condition | Route | Judge kind | First channel leaks |
|---|---|---|---|---:|
| Qwen | recruiting | send_message | deliberate | 40 |
| Qwen | recruiting | send_message | accidental | 10 |
| Qwen | recruiting | final_reply | deliberate | 27 |
| Qwen | recruiting | final_reply | accidental | 20 |
| Qwen | recruiting | final_reply | unjoined_or_unclear | 1 |
| gpt-oss | recruiting | send_message | deliberate | 1 |
| gpt-oss | recruiting | final_reply | deliberate | 126 |
| gpt-oss | recruiting | final_reply | unjoined_or_unclear | 1 |

All 664 saved target-channel sequences matched the reconstruction. Counts and snapshot status are in counts.json.
