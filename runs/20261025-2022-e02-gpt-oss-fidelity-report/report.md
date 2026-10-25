# gpt-oss-20b Harmony replay fidelity and activation check

## Result

**The isolated replay plumbing passes this small test and is ready to use in a separately planned full replay. It is not an exact reconstruction of provider execution.** All 76 requests from three saved episodes pass prompt-hash, input-token, finite-array and shape checks. No generation or new target/peer API call was used. Full collection and full replay were not run.

The test uses recruiting-0002 (give-in), recruiting-0003 (held), and control-0001 from the escalation worktree run `20261025-1912-e03-escalation-gpt-oss-envblock_late`. Every saved target request in these three complete episodes is included. The API served CoreWeave with fp4 routing; provider precision itself was not returned. The selection is a plumbing sample, not a population estimate.

## Rendering and precision

Weights: `openai/gpt-oss-20b@6cee5e81ee83917806bbde320786a8fb61efebee`. `transformers==5.20.2` supports GptOssForCausalLM and `Mxfp4Config(dequantize=True)`. This expands the released MXFP4 values into bf16; it does not recover unquantized original weights. All loaded model parameters in this run were bf16. Attention used the built-in eager implementation, one A100-80GB, no CPU/disk offload.

Official `openai-harmony==0.0.8` renders LOW reasoning, saved-call date, original tool schemas, raw argument JSON/results and commentary tool messages. Prior assistant reasoning is omitted. All 76 prompts are exactly one token shorter than provider usage, including later conversational turns. Retaining all earlier reasoning yields growing count errors, up to +594. This supports omission for these CoreWeave traces, but counts alone cannot identify the missing token or prove identical token sequences. No padding token was added.

The saved response is appended through the official training renderer; the prompt must be its exact token prefix. The current response includes returned analysis text, final content/tool arguments and Harmony framing. Reasoning positions select only returned analysis body tokens, excluding headers and terminators. All 76 extracted spans equal the tokenizer encoding of the returned reasoning text. All 76 streams decode to identical text under the pinned HF tokenizer and Harmony. Naive text-to-HF re-encoding is NOT safe: only 52/76 prompts and 51/76 full streams round-trip exactly, because the held episode contains literal <|channel|> text that HF re-encoding promotes to control tokens. The official renderer preserves those literals as ordinary tokens. Replay uses its original IDs directly, not decoded/re-encoded text; all provider counts remain −1. See token_roundtrip.json. Unreturned internal reasoning cannot be recovered.

## Teacher-forced fidelity

| Segment | Tokens | Mean NLL (nats/token) | Top-5 |
|---|---:|---:|---:|
| all | 4260 | 0.402916 | 99.202% |
| reasoning | 945 | 0.717203 | 97.884% |
| answer | 2462 | 0.259882 | 99.675% |
| framing | 853 | 0.467567 | 99.297% |

Qwen reference: approximately 0.23 NLL and 99.8% top-5. The gpt-oss answer/tool-content result is close; the reasoning portion is less predictable and raises the overall NLL. This looks acceptable as a fidelity sanity check, with a larger gap than Qwen. It is not a controlled precision comparison: these are different episodes/models and this test scores full replies, whereas the main Qwen pipeline limits fidelity to the first 64 reply tokens. Sampling and rendering differences also contribute; the gap cannot be assigned solely to fp4 versus bf16 arithmetic.

| Episode | Requests | Reply tokens | NLL | Top-5 |
|---|---:|---:|---:|---:|
| control-0001.json | 23 | 1013 | 0.415181 | 99.112% |
| recruiting-0002.json | 26 | 1862 | 0.369727 | 99.356% |
| recruiting-0003.json | 27 | 1385 | 0.438564 | 99.061% |

## Saved activations and validation

Local artifact directory: `runs/20261025-1217-e02-gpt-oss-fidelity`. The identical directory exists on Modal Volume `collusion-activations`. Each of 76 NPZ files contains `residual_last` with shape **[24, 2880]**, and `residual_reasoning` with shape **[24, n_reasoning_tokens, 2880]**. There are **945 reasoning positions** in total; a reply without reasoning has a zero-length token axis. Arrays are float32 copies of bf16 block outputs, before final model normalization. Layers are numbered 0–23; the embedding is not an extra layer. Total NPZ storage: 134,236,724 bytes.

The last-prompt state is measured immediately before the served reply. Reasoning states are measured after consuming each corresponding reasoning token, with causal attention. They must be aligned to available reasoning when used as prospective monitor inputs; later reply states must not be treated as pre-reply features. Each NPZ also stores full teacher-forced input IDs, absolute zero-based reasoning positions and layer indices. `index.json` maps files to source episode/request, hashes, prompt counts and per-request fidelity. The separate immutable plan retains source labels and the exact prompt/reply split.

Four local regression tests passed. A tiny random GptOss model completed the same path; a causality test shows that appending reply tokens leaves last-prompt activations unchanged; captured intermediate reasoning states match native hidden states; manual likelihood computation matches; hooks are removed. The Qwen `replay.py`, `fidelity.py`, and `modal_app.py` files were not modified. The new adapter reuses decoder-layer discovery and likelihood scoring from E02.

## Runtime and cost

Model load: 10.05s. Replay including load and output writes: 100.67s. Peak CUDA allocation: 42.90 GiB. Pins: {'torch': '2.14.1', 'transformers': '5.20.2', 'accelerate': '1.15.0', 'openai-harmony': '0.0.8'}. CPU prefetch and GPU apps are both confirmed stopped.

Latest app-filtered billing snapshot: **USD 0.13173255** (billing can lag). Conservative whole-client wall-time compute bounds plus USD0.50 setup/storage/egress allowance total **USD 0.8711**, below the separate USD4 cap. `billing.json` and the two client-run summaries preserve the accounting. Cached weights and activations remain on their existing volumes; no live container remains.

## Reproduction and limits

See `experiments/E02-activation-replay/GPT_OSS_REPLAY.md` for commands. The dedicated wrapper intentionally accepts at most 100 requests per call, caps each input at 16,384 tokens, and has a 25-minute timeout. A full replay must be explicitly planned and sharded under its own budget; these guards are not silently relaxed. No full-replay cost or scientific probe result is claimed by this test.

Sources: [Transformers MXFP4 configuration](https://huggingface.co/docs/transformers/en/main_classes/quantization#transformers.Mxfp4Config), [official Harmony renderer](https://github.com/openai/harmony), [Modal pricing](https://modal.com/pricing). Installed Transformers source was inspected for the gpt-oss architecture and explicit dequantization path.
