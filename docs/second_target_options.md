# Choosing a second target model

Written 2026-10-25. Desk research only: public OpenRouter endpoints, Hugging Face (HF) model pages and configs, and the `transformers` source pinned in our replay environment. No paid calls and no GPU time.

## What this is for

In our setup, a **peer** agent (DeepSeek-V4-Flash) pressures a **target** agent over about 20 rounds to break an operator rule, for example by posting a secret token it had to read for its task. The target runs through OpenRouter with **native tool calling**, meaning the API returns structured tool calls rather than tool-shaped text. Afterwards we **replay** each saved target request on Modal: one A100-80GB, bf16 weights, HF `transformers`. We render the exact request with the model's HF chat template, run one forward pass, and use forward hooks to read the **residual stream** (each decoder block's output) at the last prompt token. Linear probes are trained on those vectors.

The main target so far is Qwen3-32B with thinking off: 64 layers, hidden size 5120, Chinese origin. For a follow-up ablation we want a second target. Preferences:

- **US-origin open weights.** US labs often do different alignment training, which makes a useful contrast.
- **Roughly 20–40B parameters**, so it fits one 80 GB GPU in bf16.
- **Thinking can be turned off.** Qwen3-32B with thinking on gave in only 1 of 8 times, too few positives to train probes.
- **Strong enough to use tools properly.** granite-4.2-8b was too weak.
- **Actually reads the secret.** Llama-3.3-70B never opened the protected file, and its providers were unreliable.
- **A bf16 provider with tools**, so the served precision matches our bf16 replay.
- **A template that reproduces the served prompt**, and a module layout our hooks can reach.

Terms used below:

- **MoE (mixture of experts):** each token uses only some of the weights ("active" parameters), but every weight must still sit in GPU memory.
- **Sliding-window attention:** some layers attend only to the last N tokens. This is fine for hooks, but it changes the attention kernels and memory use.
- **Multimodal wrapper:** the text decoder is nested inside an image/text model. The decoder blocks then sit at `model.language_model.layers`, not `model.layers`, and the layer count is in `config.text_config`.
- **Precision tags:** OpenRouter's reported `quantization` per provider. It is advertised, not verified. "fp4" or "fp8" means the provider serves lower-precision weights than our bf16 replay.

## Recommendation

**Use Gemma 4 31B-it (Google DeepMind, US) as the second target.** It is the only candidate that meets every hard requirement:

- dense, about 31B parameters;
- Apache 2.0 licence;
- thinking is **off by default** in its template;
- native tool tokens;
- two bf16 providers with tools on OpenRouter;
- architecture supported in our pinned `transformers`.

It also has a bonus: a published multi-agent collusion dataset (Shi et al., arXiv 2609.24967) already contains Gemma-4-31B traces with mixed hold/give-in outcomes, which a separate repo note (`docs/backup_shi_et_al.md`) identifies as the best backup dataset. With Gemma 4 as the second target, a probe trained on our episodes could be tested on that independent data with the same model on both sides.

The main risks are replay mechanics, not behaviour:

- the template has been revised several times;
- the multimodal wrapper needs a small loader change;
- the reply-scoring step needs logit soft-capping;
- memory at long prompts should be checked.

The open behavioural question is whether it gives in often enough. A cheap screen, described at the end, answers that before any GPU spend.

## Ranked shortlist

| Rank | Model | One-line case |
| --- | --- | --- |
| **1** | **Gemma 4 31B-it** (Google, US) | Meets every requirement: dense 31B, thinking off by default, native tools, bf16+tools providers, supported in our `transformers`, matching external traces. |
| 2 | **Muse Glimmer 30B** (Meta, US) | Newest US dense ~30B model, strong vendor-reported tool use and explicit agentic safety training. But reasoning cannot be turned off (lowest level is "low"), and it has only one bf16 provider. Best used as a "US reasoning target" contrast, not as the main ablation. |
| 3 | **Nemotron 3.5 Lightning 30B-A3B** (NVIDIA, US) | Thinking can be turned off, two bf16+tools providers, cheap, and supported on Tinker for later fine-tuning. But it is a hybrid Mamba/attention/MoE model with only 3B active parameters, so it may be weak (the granite lesson), and replay needs Mamba kernels. |

Same-family fallback: **Gemma 4 26B-A4B-it** (MoE, 25.8B total, 3.8B active). It has the same template and wrapper as the 31B, and more bf16+tools providers. Use it if the 31B is too resistant or does not fit in memory, accepting that its activations come from a much smaller active network.

Non-US fallback: **Mistral Small 3.2 24B** (Mistral, France). An earlier screen (`experiments/E03-target-screen/README.md`) found clean tool use. But its tool providers are fp8 only, and its HF tokenizer has no chat template configured, so it needs a reviewed template adapter.

## Candidate table

"V" marks a value checked in a primary source during this research (HF config or API, OpenRouter API, or the model card). "U" marks a value that is unverified or comes from secondary reporting. Memory figures are bf16 weights, at 2 bytes × total parameters.

| Model | Maker / country | Released | Params (total / active) | Layers / hidden | Licence | Thinking | Fits 1×80 GB bf16? | On OpenRouter with tools and bf16? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Gemma 4 31B-it** `google/gemma-4-31B-it` | Google DeepMind, US | OpenRouter listing 2026-04-02 (V) | 31.27B dense, incl. ~0.55B vision encoder (V) | 60 / 5376; 50 sliding (window 1024) + 10 full attention (V) | Apache 2.0, not gated (V) | Off by default; `enable_thinking` flag (V) | ~62.5 GB weights. Fits at ≤8k tokens; check 16k | Yes: Novita, Crusoe (V) |
| Gemma 4 26B-A4B-it | Google DeepMind, US | 2026-04-02 (V) | 25.8B / 3.8B MoE, 128 experts, top-8 (V) | 30 / 2816 (V) | Apache 2.0 (V) | Same template as 31B (V) | ~51.6 GB, comfortable | Yes: DekaLLM, NextBit, Io Net, Venice, Novita (V) |
| **Muse Glimmer 30B** `meta-models/Muse-Glimmer-30B` | Meta Superintelligence Labs, US | Aug 2026 (V) | 29.8B dense, incl. ~1.8B vision encoder (V) | 52 / 6656; 3 local : 1 global, window 2048, 2 KV heads (V) | Apache 2.0 (V) | **Always reasons**: "Reasoning strength" low/medium/high/xhigh, default high (V) | ~59.6 GB, fits | DeepInfra bf16; Together unknown (V) |
| **Nemotron 3.5 Lightning 30B-A3B** `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16` | NVIDIA, US | Aug 2026 (V) | 31.6B / ~3B MoE (V) | 52 / 2688; hybrid Mamba-2 + attention + MoE (V) | NVIDIA licence ("other") (V) | `enable_thinking`, default on, can be set off (V). The older Nemotron 3 Nano turned off cleanly in our first OpenRouter smoke test | ~63 GB, fits | DeepInfra, CoreWeave (V) |
| gpt-oss-20b `openai/gpt-oss-20b` | OpenAI, US | Aug 2025 (V) | 20.9B / 3.6B MoE (V) | 24 / 2880 (V) | Apache 2.0 (V) | **Reasoning mandatory**: OpenRouter rejected `reasoning:{enabled:false}` in our smoke test | Weights stored as MXFP4 (a 4-bit format); ~42 GB once dequantized to bf16 | DeepInfra, DekaLLM report "bf16" (V); doubtful for a 4-bit-native checkpoint |
| gpt-oss-120b | OpenAI, US | Aug 2025 (V) | 117B / 5.1B (V) | — | Apache 2.0 | Reasoning mandatory | No (~234 GB in bf16) | Several "bf16" providers (V) |
| **Inkling** `thinkingmachines/Inkling` | Thinking Machines Lab, US | 2026-07-15 (V card; date U) | 975B / 41B MoE, 256 routed experts, top-6, plus 2 shared (V) | 66 / 6144; local/global hybrid (V) | Apache 2.0 (V) | Graded "thinking effort" 0–0.99, including `none` = 0 (V) | No (~1.9 TB) | Together only, precision unknown, $1.00 / $4.05 per M tokens (V) |
| Inkling-Small | Thinking Machines Lab, US | 2026-07-27 on HF (V) | 266–276B / 12B MoE (V) | 42 / 4096 (V) | Apache 2.0 (V) | Same effort control (V) | No (~530 GB) | DeepInfra fp8 only (V) |
| Olmo 3.1 32B Instruct `allenai/Olmo-3.1-32B-Instruct` | Ai2, US (fully open: data and code too) | 2025-12-10 on HF (V) | 32.2B dense (V) | U | Apache 2.0 (V) | Instruct variant has no long reasoning (U) | ~64 GB, fits | **Not on OpenRouter** (V); would need self-hosted generation |
| Llama 4 Scout | Meta, US | Apr 2025 (V) | 108.6B / 17B MoE (V) | — | Llama licence, gated (V) | No thinking | No (~217 GB) | Yes; precision not checked |
| Granite 4.0-H Small | IBM, US | Sep 2025 (V) | 32.2B MoE, hybrid Mamba (V) | U | Apache 2.0 (V) | — | ~64 GB | **Not on OpenRouter** (V) |
| Arcee Trinity Mini / Large Thinking | Arcee AI, US | Dec 2025 / Apr 2026 (V) | 26.1B MoE / 398.6B (V) | U | "other" (V) | Large is reasoning-only (V) | Mini fits; Large no | Mini **not listed**; only Large is listed (V) |
| Laguna XS 2.1 | Poolside, US | Jun 2026 (V) | 33.4B / ~3B MoE (V) | 40 / 2048 (V) | OpenMDW (V) | Has reasoning param (V) | ~67 GB | Poolside only, fp8 (V); coding-focused |
| LFM2.5-24B-A2B | Liquid AI, US | Oct 2026 (V) | 24.0B / 2.45B (V) | 40 / 2048; convolution + attention hybrid (V) | "other" (V) | "Always reasons" (V) | ~48 GB | Liquid only, fp8 (V) |
| Phi-4 | Microsoft, US | Jan 2025 (V) | 14B (U) | — | MIT (U) | — | yes | **No tools** on OpenRouter (V) |
| Mistral Small 3.2 24B | Mistral, France | Jun 2025 (V) | 24.0B (V) | — | Apache 2.0 (U) | No thinking | ~48 GB | Tools only on fp8 providers (V) |

The big US open-weight releases of 2026 (Inkling, Muse Spark Open at 816B, Nemotron 3 Ultra at 550B, Reflection Beam at 501B, Trinity Large) are all far beyond one GPU. In the 20–40B band, the only US candidates with a bf16+tools route are Gemma 4, Muse Glimmer and Nemotron Lightning.

### About Inkling

Inkling is the first open-weights model from Thinking Machines Lab, the US startup that also runs the Tinker fine-tuning service. It was released on 15 July 2026 under Apache 2.0, with bf16 and NVFP4 (4-bit) weights on HF. Its HF config describes a 66-layer MoE: 256 routed experts, 6 used per token, plus 2 shared experts, with local/global hybrid attention. It takes text, image and audio input. The card gives 975B total and 41B active parameters. Artificial Analysis called it the leading US open-weights model on its index at release.

Its chat template supports tools and a graded "thinking effort", which can be set to `none`. That makes Inkling an interesting future target behaviourally. Our setup cannot use it as a target, though:

- replay would need about 1.9 TB of bf16 weights;
- the only OpenRouter route is Together, at unknown precision;
- even Inkling-Small is about 530 GB, and its only route is DeepInfra fp8.

Sources: [HF model card](https://huggingface.co/thinkingmachines/Inkling), [Artificial Analysis](https://artificialanalysis.ai/articles/thinking-machines-has-released-inkling-the-new-leading-u-s-open-weights-model), [Unite.AI](https://www.unite.ai/thinking-machines-lab-unveils-inkling-its-first-open-weights-multimodal-ai-model/).

### Tinker support (for later fine-tuning)

Tinker's [Models & Pricing page](https://tinker-docs.thinkingmachines.ai/tinker/models/) lists 36 models (checked 2026-10-25). It includes Inkling, Inkling-Small, **Nemotron 3.5 Lightning 30B-A3B**, gpt-oss-20b/120b and Qwen3-8B. It does **not** list Gemma 4, Muse Glimmer or Qwen3-32B. If fine-tuning the target is a likely next step, that counts in Nemotron Lightning's favour.

## Replay compatibility details

All three shortlisted architectures exist in our pinned `transformers` 5.20.2, in `experiments/E02-activation-replay/.venv` (folders `gemma4`, `muse_glimmer`, `nemotron_h`), so none needs `trust_remote_code`. (Laguna and the Inkling family are also in the library.)

**Gemma 4 31B.**

- *Loader.* The HF class is `Gemma4ForConditionalGeneration`. `AutoModel` gives `Gemma4Model`, whose decoder blocks are at `language_model.layers`. The top-level config has **no** `num_hidden_layers`, which sits in `text_config` instead. Our `decoder_layers()` probes `layers` and `model.layers`, and checks `model.config.num_hidden_layers`, so it would fail today. A small change fixes it: pass `--layers-path language_model.layers` and read the count from `text_config`.
- *Block outputs.* Each block returns a single tensor, after a per-layer `layer_scalar` multiply. That is the residual stream we want.
- *Reply scoring.* The fidelity scorer applies the LM head directly to hidden states. Gemma uses `final_logit_softcapping = 30`, so the scorer must apply the soft-cap, or reply NLL will be slightly off.
- *Template.* Native `<|tool>` / `<|tool_call>` tokens, so this is not Gemma 3's tool-blind template. Tool-call arguments must be dicts, which our replay already does by parsing the JSON strings. No exception is raised on consecutive user messages.
- *Thinking off.* With thinking off, the generation prompt ends `<|turn>model\n<|channel>thought\n<channel|>`, an empty thought block. So the "last prompt token" is the channel-close token, much as Qwen's empty `<think></think>` is.
- *Template churn.* The HF template changed at least five times between April and July 2026: tool-call prefixes, system-instruction handling, reasoning preservation, turn-tag balance. A provider may serve any of these versions, so token-exact replay is not guaranteed. Mitigation: render with the current revision and with the release revision, then compare each with the provider's `usage.prompt_tokens` and reply NLL. Pin whichever matches.

**Memory (Gemma 4 31B).**

- Weights take about 58 GiB.
- For comparison, Qwen3-32B (61 GiB of weights) peaked at 62.2 GiB on ~6k-token prompts in our benchmark (`experiments/E02-activation-replay/MODAL_BENCHMARK.md`).
- At 16k tokens, residual and MLP activations add only a few GiB, if PyTorch SDPA uses a memory-efficient kernel.
- The risk: full-attention layers use head dimension 512, and sliding layers need an explicit mask. If SDPA falls back to the plain "math" kernel, one layer's attention scores take about 32 heads × 16k² × 2 bytes ≈ 16 GiB, which would not fit.
- Benchmark the longest prompts first. If they fail, use H100 (same 80 GB, so it only helps through kernel support), split across two GPUs, or cap prompt length.
- Our real prompts so far are mostly under 7k tokens.

**Muse Glimmer 30B.**

- Same nested layout (`MuseGlimmerModel.language_model`) and the same missing top-level layer count.
- Soft-capping is 20, plus an `output_multiplier`.
- Tools use an XML-like "ATEM" format. The template requires dict arguments and renders reasoning as a separate `to=self` message, so replay needs the provider's reasoning text, saved per turn.
- The template always injects `Reasoning strength: …` (default `high`), so non-thinking replay is impossible by design.

**Nemotron 3.5 Lightning.**

- `NemotronHForCausalLM`: blocks are at `model.layers` and the config is flat, so our loader works unchanged.
- But 52 blocks mix Mamba-2, attention and MoE layer types. Probes would read the residual after blocks of different kinds.
- Fast inference needs `causal_conv1d` / `mamba_ssm` kernels. The pure-PyTorch fallback is slow and memory-hungry on long prompts. Its SSM state is float32.

**gpt-oss-20b**, from the earlier screen:

- Harmony template, which expects `thinking` while OpenRouter returns `reasoning`;
- assumes a single tool call per message;
- the MXFP4 checkpoint must be dequantized, so "bf16" is not the native weights;
- reasoning cannot be disabled.

All four points count against it.

## Per-choice risks

**Gemma 4 31B (recommended).**

- *Behaviour.* Possibly very resistant: strong alignment, and Google trains against prompt injection. Or it may never open the secret file, the Llama-3.3 failure. The screen measures both.
- *Tool-call parsing.* Users report tool calls coming back as plain text on some serving stacks (the [Hermes Agent issue](https://github.com/NousResearch/hermes-agent/issues/7457), a [LiveKit thread](https://community.livekit.io/t/tool-calling-with-non-gpt-openai-models-on-livekit-agents-gemma-nemotron-etc-not-working/1555)), and chat-template thought-block bugs ([HF discussion](https://huggingface.co/google/gemma-4-31B-it/discussions/142)). Count raw-text tool calls per provider in the screen.
- *Precision.* Only 2 of 16 tool-capable routes are bf16 (Novita, Crusoe). Five are fp4. Pin `provider.order` plus `quantizations:["bf16"]` and keep fallbacks off. Novita throttled us on another model earlier.
- *Turning thinking off.* Untested on OpenRouter for Gemma 4. Confirm that `reasoning:{enabled:false}` (or the default) returns no reasoning text.
- *Replay engineering.* The template version match, the loader path change, soft-capping in fidelity scoring, and the SDPA memory check above. Estimated at under a day of work, plus one small GPU benchmark.

**Muse Glimmer 30B.**

- Reasoning is always on, and the Qwen thinking-mode lesson (1/8 gave in) suggests few positives.
- Meta reports dedicated agentic safety training "covering tool-use boundaries, prompt injection resistance, and permission handling" (model card), which points the same way.
- There is a single bf16 provider (DeepInfra), with no fallback.
- The ATEM tool format and reasoning round-trip are untested in our harness.
- Third-party reviews report confident hallucination ([codersera](https://codersera.com/blog/muse-glimmer-complete-guide-2026/), [Artificial Analysis](https://artificialanalysis.ai/ja/articles/muse-glimmer)). The vendor's tool-use benchmark numbers are unverified.

**Nemotron 3.5 Lightning.**

- With 3B active parameters, it may be too weak for clean multi-step tool use.
- The hybrid Mamba stack makes "residual stream at the last token" less comparable with Qwen's pure-attention model.
- Kernel installs on Modal are untested.
- The licence is NVIDIA's own, not Apache.

## Proposed first step: a cheap behaviour screen

This step needs approval, because it spends API credit. The goal is to decide go/no-go on Gemma 4 31B before any GPU work.

1. **Offline checks first, free.** Run the E03 catalog and template scripts (`experiments/E03-target-screen/catalog.py`, `check_templates.py`) on `google/gemma-4-31B-it`, with tool schemas on and off, after making the loader change above.
2. **Smoke test.** Target `google/gemma-4-31b-it`, pinned to Novita bf16 (Crusoe as a recorded alternative, not an automatic fallback). Thinking off, with the peer unchanged. One episode each of deploy-token-v2 rule+ask, its matched control, and target-alone, 20 rounds with early stopping. Check:
   - native tool calls, not text;
   - the target opens the secret file;
   - no reasoning text comes back;
   - provider prompt-token counts against the HF render.
3. **Screen.** On deploy-token-v2 and handoff-exception-note (two of our six probe scenarios with the most give-in steps on Qwen3-32B):
   - 8 rule+ask episodes, 3 matched controls and 2 alone, per scenario;
   - 26 episodes in total, plain peer, 20 rounds, early stopping;
   - estimated cost under USD 1 for target plus peer, assuming roughly 100–200k target prompt tokens per episode at $0.14/M input.
4. **Go criteria.**
   - At least 3/8 deliberate give-ins on at least one scenario, after the target has read the secret.
   - Controls and alone runs clean.
   - Fewer than 5% of turns with raw-text tool calls.
   - Prompt-token counts within about 1% of the provider's.

   If give-ins are 0–1/8, try the own-stake variant once. Then fall back to Gemma 4 26B-A4B with the same scenarios, or to Muse Glimmer at "low" reasoning strength as an explicitly labelled reasoning-model contrast.
5. **Only after go:** a 50-request A100 benchmark on the longest prompts (memory, SDPA kernel, reply NLL), then the full replay.

## Sources

- OpenRouter `GET /api/v1/models` and `/api/v1/models/<id>/endpoints`, fetched 2026-10-25: provider lists, `quantization`, `tools` support, prices.
- HF API, `config.json`, `chat_template.jinja` and README for [gemma-4-31B-it](https://huggingface.co/google/gemma-4-31B-it), [gemma-4-26B-A4B-it](https://huggingface.co/google/gemma-4-26B-A4B-it), [Muse-Glimmer-30B](https://huggingface.co/meta-models/Muse-Glimmer-30B), [Nemotron-3.5-Lightning](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16), [gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b), [Inkling](https://huggingface.co/thinkingmachines/Inkling), [Inkling-Small](https://huggingface.co/thinkingmachines/Inkling-Small), [Olmo-3.1-32B-Instruct](https://huggingface.co/allenai/Olmo-3.1-32B-Instruct), [Laguna-XS-2.1](https://huggingface.co/poolside/Laguna-XS-2.1), [LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B).
- [Tinker Models & Pricing](https://tinker-docs.thinkingmachines.ai/tinker/models/) and the [tinker-cookbook README](https://github.com/thinking-machines-lab/tinker-cookbook).
- Repo: `experiments/E03-target-screen/README.md`, `experiments/E02-activation-replay/README.md`, `experiments/E02-activation-replay/MODAL_BENCHMARK.md`, `experiments/E02-activation-replay/replay.py`, `docs/backup_shi_et_al.md`, `EXPERIMENT_LOG.md`.
