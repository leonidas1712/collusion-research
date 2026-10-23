# Replay fidelity

Model: Qwen/Qwen2.5-0.5B-Instruct@7ae557604adf67be50417f59c2c2f167def9a775. Tiny random weights: False.
Template SHA256: cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f. See selected_chat_template.jinja, tokenizer/, prompts/, provenance.json and NPZ input_ids.

HF/provider prompt-token ratios: n=1, min/median/max=0.9934640522875817/0.9934640522875817/0.9934640522875817. These are diagnostics, not token equality or likelihood checks.

OpenAI tool argument JSON strings are parsed to objects for HF templates; whitespace and JSON key serialization can change. Source requests remain untouched and hashed. Tool IDs, tool results and other fields are retained; the model template may ignore fields. Reasoning mode is explicitly supplied from each saved request (missing enabled defaults to false), or overridden by --thinking. Provider reasoning_details may not be rendered by HF. Templates can trim whitespace, merge tool results, insert tool instructions, or drop prior thinking. The provider's tokenizer revision, private template, exact token IDs, quantization and hidden prompts are unavailable. Equal counts do not establish equal tokens. Cross-model or random-weight replay is wiring only. No provider outputs are regenerated and no claims of exact provider replay are made.

Each API attempt is a separate row, including retries; do not treat retries or tool steps as independent episodes. before_first_leak includes the call that emits the first leak because its input precedes that output. Subsequent calls in that same round are excluded. Unknown leak locations are null; no-leak episodes are true through their observed horizon, not forever. before_first_leak_round is the stricter round-only flag. Labels are copied from the immutable source, not recomputed with a changing E01 scorer.
