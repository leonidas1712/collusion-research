# Offline Harmony prompt-count audit

**No tested rendering reproduces all six provider counts exactly.** The official renderer gets within one token on every request when prior reasoning is omitted. That satisfies the original approximate 1% token-count criterion, but does not establish exact provider token identity or justify an unverified activation-replay adapter.

## Inputs and method

Six saved CoreWeave gpt-oss-20b requests from `runs/20261025-1739-e03-gpt-oss-smoke` cover one alone episode each of deploy-token-v2 and handoff-exception-note. Each has a read-file call, a write-file call and a final reply. All three requests belong to target round 1. This analysis made no model calls and used no GPU.

Rendering uses `openai-harmony==0.0.8`, `HARMONY_GPT_OSS`, structured SystemContent and DeveloperContent, the original function schemas, and reasoning effort LOW. The closest configuration uses the saved-call date 2026-10-25, preserves raw argument JSON and raw tool-result text, places tool calls/results on commentary, marks call content as JSON, and omits previous assistant reasoning. The renderer adds the assistant completion prefix itself. There is no added padding, fitted token offset or edited scenario text.

## Counts

| Episode / request | Provider | Harmony, drop reasoning | Difference | Harmony, keep reasoning | Difference |
|---|---:|---:|---:|---:|---:|
| deploy-token-v2-0001.json / 0 | 317 | 316 | -1 | 316 | -1 |
| deploy-token-v2-0001.json / 1 | 400 | 399 | -1 | 413 | +13 |
| deploy-token-v2-0001.json / 2 | 462 | 461 | -1 | 539 | +77 |
| handoff-exception-note-0001.json / 0 | 312 | 311 | -1 | 311 | -1 |
| handoff-exception-note-0001.json / 1 | 396 | 395 | -1 | 411 | +15 |
| handoff-exception-note-0001.json / 2 | 460 | 459 | -1 | 492 | +32 |

Dropping reasoning gives a constant −1 token difference (0.22–0.32%). Retaining the returned reasoning gives differences of −1, +13, +77, −1, +15 and +32 tokens. Under otherwise identical serialization, this favors omission of previous reasoning from the served prompt. It is evidence from counts, not direct observation of provider input tokens. The remaining token could reflect a provider prefix, whitespace, preamble or usage accounting; its identity is unresolved. No arbitrary token was appended to claim a match.

The exploratory matrix contains 48 combinations: date absent/present; reasoning dropped/kept; raw/compact/spaced argument JSON; commentary+JSON or analysis tool headers; raw or JSON-quoted result text. These are serialization diagnostics, not 48 equally valid deployment recommendations. None matches all six counts. The highest exact-match count is two; its errors are −1, 0, +3, −1, 0, +3 and it normalizes argument spacing. The raw-argument configuration minimizes aggregate absolute error at six tokens. All matrix results and token hashes are in `variants.json`.

## What the reasoning test establishes

The API history retains both reasoning and reasoning_details. The count comparison above tests omission versus inclusion of the plain reasoning text during tool steps within one target turn. There is no later user/peer turn in these alone traces, so whether CoreWeave drops reasoning across completed turns cannot be determined from these six requests.

A synthetic offline control separates renderer policy from provider behavior: a prior analysis message followed by a final reply and a new user message loses its analysis marker with the official renderer default auto_drop_analysis=True (21 tokens), and retains it with False (36 tokens). This demonstrates the library behavior only. The current vLLM source also explicitly removes analysis before the latest final response; its chat-input converter accepts the reasoning field. That is a public implementation example, not proof of CoreWeave’s serving stack or version.

## Validation, provenance and limits

All six canonical Harmony token sequences round-trip through the pinned HF tokenizer with exact token-ID equality (`token_roundtrip.json`). The mismatch is therefore not explained by a different vocabulary on these prompts. This does not prove equality with the provider’s unavailable token IDs. The local completed-turn control is in `completed_turn_control.json`; saved provider counts and request indices are in `requests.json`. No provider defaults were changed and no production replay adapter was installed.

Reproduce with `experiments/E02-activation-replay/.venv/bin/python experiments/E03-target-screen/harmony_audit.py runs/20261025-1739-e03-gpt-oss-smoke`. The environment needs openai-harmony==0.0.8 and the cached HF tokenizer at revision 6cee5e81ee83917806bbde320786a8fb61efebee. Tokenizer checks use local_files_only=True. The official encoding assets must already be cached for a network-disconnected rerun.

Sources: [official Harmony package](https://github.com/openai/harmony), [OpenAI format guide](https://developers.openai.com/cookbook/articles/openai-harmony), and [vLLM Harmony conversion source](https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/parser/harmony_utils.py), inspected 2026-10-25. The vLLM source was inspected as text and was not executed.

Conclusion: approximate count fidelity is recovered with official Harmony and reasoning omission; exact fidelity and provider behavior across completed turns remain unverified. No additional paid test is included.
