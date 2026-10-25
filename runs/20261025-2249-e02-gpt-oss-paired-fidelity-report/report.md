# Paired gpt-oss provider rendering fidelity check

The diagnostic used 50 requests selected by provider, tool-turn position and prompt-count gap, without outcome labels. Each was replayed with dropped prior reasoning and with current-turn reasoning retained, for 100 teacher-forced forwards. It is an engineering fidelity check, not a representative behaviour sample or outcome fit.

| Provider | History reasoning | Segment | Tokens | Mean NLL | Top-5 |
|---|---|---|---:|---:|---:|
| AkashML | drop_all | all | 2146 | 0.51364 | 97.950% |
| AkashML | drop_all | reasoning | 361 | 0.72575 | 96.399% |
| AkashML | drop_all | answer | 1436 | 0.32259 | 98.259% |
| AkashML | current_turn | all | 2146 | 0.42343 | 98.602% |
| AkashML | current_turn | reasoning | 361 | 0.60631 | 97.784% |
| AkashML | current_turn | answer | 1436 | 0.25561 | 98.816% |
| DekaLLM | drop_all | all | 998 | 0.49553 | 98.397% |
| DekaLLM | drop_all | reasoning | 208 | 0.80993 | 95.192% |
| DekaLLM | drop_all | answer | 572 | 0.35960 | 99.126% |
| DekaLLM | current_turn | all | 998 | 0.51910 | 98.297% |
| DekaLLM | current_turn | reasoning | 208 | 0.92092 | 95.192% |
| DekaLLM | current_turn | answer | 572 | 0.38002 | 98.951% |

AkashML current-turn answer/tool-body NLL is 0.25561, close to the earlier CoreWeave diagnostic’s 0.25988; top-5 is 98.816% versus 99.675%. The samples differ, so these are sanity comparisons, not a controlled equivalence test. DekaLLM drop-all answer/tool-body NLL is 0.35960 with 99.126% top-5; this does not indicate a large answer-fidelity loss. Current-turn retention improves AkashML and does not improve DekaLLM. Reasoning is less faithful than answer/tool bodies.

Decision under the conditional gate approved in Aboard #1182: proceed with AkashML current-turn and DekaLLM drop-all. DekaLLM prompt tokens remain approximate; likelihood agreement does not establish exact provider tokens. Provider quantization fields are null. Replay all requests and retain provider and absolute count gap; the primary analysis uses all eligible steps and a sensitivity excludes requests with |gap| > 1. The prior CoreWeave path and Qwen code remain unchanged.

All 100 input-token arrays, prompt/input hashes, layer IDs, reasoning positions and finite activation arrays were checked. Last-prompt arrays are [24,2880]; reasoning arrays are [24,n_reasoning,2880]. Artifacts: `20261025-1444-e02-gpt-oss-full-shard` locally and on the collusion-activations volume. Replay took 145.225 seconds. Billed snapshot USD0.10308139; conservative compute upper USD0.16683843, charged to the shared USD20 cap. The diagnostic app is stopped. Cached MXFP4 weights were expanded to bf16 using transformers5.20.2/torch2.14.1; no weights downloaded on GPU.
