# gpt-oss rendering gate: offline token-count audit

No GPU has been launched and no outcome fit was run. The original validated CoreWeave renderer drops all prior reasoning. This collection instead uses AkashML (6,672 requests) and DekaLLM (313). The alternative keeps only assistant reasoning after the most recent user/peer message, i.e. during the current tool-use turn. It is evaluated on copied inputs without changing saved episodes or the production rendering mode. All 6,985 target requests are included; gap = rendered minus provider prompt tokens.

## Gap size by provider and rendering

| Provider | Rendering | N | Within ±1 | Within ±5 | Within ±20 | Within ±50 | Beyond ±50 | Median absolute | P90 absolute |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AkashML | drop_all | 6672 | 4534 (68.0%) | 4577 (68.6%) | 5049 (75.7%) | 5778 (86.6%) | 894 | 0 | 62 |
| AkashML | current_turn | 6672 | 6598 (98.9%) | 6671 (100.0%) | 6672 (100.0%) | 6672 (100.0%) | 0 | 0 | 1 |
| DekaLLM | drop_all | 313 | 18 (5.8%) | 58 (18.5%) | 153 (48.9%) | 298 (95.2%) | 15 | 21 | 43 |
| DekaLLM | current_turn | 313 | 6 (1.9%) | 45 (14.4%) | 132 (42.2%) | 270 (86.3%) | 43 | 24 | 63.8 |

Threshold columns are cumulative. Exclusive bins and signed ranges are in distributions.json.

## Intra-turn concentration

Intra-turn means a tool-result message occurs after the latest user message in the exact saved target input.

| Provider | Request group | Rendering | N | Within ±1 | Median absolute | P90 absolute |
|---|---|---|---:|---:|---:|---:|
| AkashML | intra_turn | drop_all | 2100 | 4 (0.2%) | 43 | 105.1 |
| AkashML | intra_turn | current_turn | 2100 | 2068 (98.5%) | 0 | 1 |
| AkashML | not_intra_turn | drop_all | 4572 | 4530 (99.1%) | 0 | 1 |
| AkashML | not_intra_turn | current_turn | 4572 | 4530 (99.1%) | 0 | 1 |
| DekaLLM | intra_turn | drop_all | 123 | 18 (14.6%) | 21 | 43 |
| DekaLLM | intra_turn | current_turn | 123 | 6 (4.9%) | 35 | 75 |
| DekaLLM | not_intra_turn | drop_all | 190 | 0 (0.0%) | 21 | 43.2 |
| DekaLLM | not_intra_turn | current_turn | 190 | 0 (0.0%) | 21 | 43.2 |

## Recruiting episode impact

Primary outcomes are channel-positive versus channel-negative (the latter includes file-only leaks). The main table uses eligible post-ask requests. Episodes with zero eligible requests are reported separately and never counted as trivially matched. The JSON also gives the broader post-read/pre-public window including pre-ask requests.

| Outcome | Rendering | All episodes | Has eligible requests | Zero-window | Every eligible request within ±1 | At least one mismatch |
|---|---|---:|---:|---:|---:|---:|
| gave_in | drop_all | 128 | 96 | 32 | 61 | 35 |
| gave_in | current_turn | 128 | 96 | 32 | 88 | 8 |
| held | drop_all | 172 | 142 | 30 | 48 | 94 |
| held | current_turn | 172 | 142 | 30 | 119 | 23 |

## Proposed gate (requires author decision before GPU)

Do not select episodes by whether every request matches: this is a post-collection filter whose outcome mix is shown above. For AkashML, freeze current-turn reasoning retention as a separate provider path, based on this input-only audit, and retain the original CoreWeave path unchanged. DekaLLM remains unresolved: dropping all reasoning fits better than current-turn retention, and basic JSON tool-argument reserialization did not recover its counts (runs/20261025-2233-e02-gpt-oss-tool-format-audit). Do not silently treat it as token-exact.

Suggested next gate is a small paired teacher-forced fidelity diagnostic, charged to the existing USD20 replay cap, with requests selected by provider, intra-turn status and gap band without using outcomes. Compare AkashML current-turn versus drop-all and the best documented DekaLLM candidate; report answer/tool-body and reasoning NLL/top-5 separately. The author should decide whether approximate DekaLLM replay is acceptable before full collection replay. No token padding, prompt edits, outcome-based renderer selection, or new API calls are proposed.
