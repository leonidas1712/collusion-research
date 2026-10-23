# Replay fidelity

Model: ibm-granite/granite-4.2-8b@a7042144125ce5ae64f89610e8289647fc000b9a. Tiny random weights: True.
Template SHA256: f0ba43f79b3cabca5e5a7584c77aec92f49feae45cdf7779c87d9fc54cd90258. See selected_chat_template.jinja, tokenizer/, prompts/, provenance.json and NPZ input_ids.

HF/provider prompt-token ratios: n=51, min/median/max=1.0/1.0/1.0. These are diagnostics, not token equality or likelihood checks.

OpenAI tool argument JSON strings are parsed to objects for HF templates; whitespace and JSON key serialization can change. Source requests remain untouched and hashed. Tool IDs, tool results and other fields are retained; the model template may ignore fields. Reasoning mode is explicitly supplied from each saved request (missing enabled defaults to false), or overridden by --thinking. Provider reasoning_details may not be rendered by HF. Templates can trim whitespace, merge tool results, insert tool instructions, or drop prior thinking. The provider's tokenizer revision, private template, exact token IDs, quantization and hidden prompts are unavailable. Equal counts do not establish equal tokens. Cross-model or random-weight replay is wiring only. No provider outputs are regenerated and no claims of exact provider replay are made.

Each API attempt is a separate row, including retries; do not treat retries or tool steps as independent episodes. before_first_leak includes the call that emits the first leak because its input precedes that output. Subsequent calls in that same round are excluded. Unknown leak locations are null; no-leak episodes are true through their observed horizon, not forever. before_first_leak_round is the stricter round-only flag. Labels are copied from the immutable source, not recomputed with a changing E01 scorer.
