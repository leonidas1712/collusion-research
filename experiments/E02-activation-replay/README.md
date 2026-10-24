# E02: replay target inputs and collect activations

**Question:** can we turn saved E01 requests into indexed, reproducible residual-stream measurements for the later probe experiment?

**Status:** Main replay complete: 3,034 requests /143 episodes, 58.5 minutes, USD 2.86 app billing; fidelity and full artifact validation passed. Middle-layer exposure AUROC reaches 0.9994; the initial last-layer 0.9549 result is retained. See [main results](MAIN_REPLAY_RESULTS.md). The earlier full-weight Qwen3-32B bf16 A100 benchmark covered 50 requests. See [Modal benchmark results](MODAL_BENCHMARK.md) for cost, throughput, NLL and wrapper fixes. Full Granite weights and FP8 remain untested. This folder does not generate responses, call OpenRouter, rent GPUs, or change E01. A replay rebuilds inputs with the selected Hugging Face template; it cannot recover the provider's unknown exact input tokens.

## Run

From the repository root, with `uv` installed:

```bash
experiments/E02-activation-replay/run.sh replay \
  runs/20261024-0126-e01-harness-9a4c \
  --model ibm-granite/granite-4.2-8b \
  --revision a7042144125ce5ae64f89610e8289647fc000b9a
```

The entry point creates its own `.venv` on first use from `requirements-lock.txt`. It leaves the root E01 environment alone. Default inference is bf16, `device_map="auto"`, SDPA, evaluation mode, no gradients and no KV cache. The base decoder performs one forward per saved target API attempt. By default that pass includes up to 64 saved reply tokens for fidelity scoring, while hooks capture the original prompt endpoint. Only reply-predicting positions are projected to vocabulary logits; no text is generated. Use --activations-only to disable scoring. Input tensors go to the input-embedding device. Accelerate dispatches the remaining layers.

Pass multiple run directories as positional arguments. Only final `.json` episode files with `status=complete` and `fake=false` are included. `.partial.json` and `.attempt-N.json` files are excluded. Duplicate input paths are deduplicated. Saved API retries within a complete episode remain separate, explicitly indexed attempts. No prompt is silently truncated: exceeding the model context or `--max-tokens` (default 32768) fails the run and preserves prior outputs.

For a fast CPU wiring test with the real Qwen tokenizer/template and a seeded two-block, width-32 **random** Qwen decoder:

```bash
experiments/E02-activation-replay/run.sh replay \
  runs/20261024-0126-e01-harness-9a4c \
  --model Qwen/Qwen2.5-0.5B-Instruct --tiny-random --allow-cross-model \
  --device cpu --dtype float32 --max-episodes 3
```

Omit `--tiny-random` to load pretrained weights. The random option downloads configuration/tokenizer assets only, not the original weights. `--max-requests-per-episode N` provides an explicitly recorded shorter check; the default processes every target request. `--max-episodes` is a global limit after ordered input selection. These flags do not alter any prompt.

Source-target identity is checked. Cross-model replay requires `--allow-cross-model` and is marked `same_model=false`; it is not evidence about the original target. Model aliases can be supplied with `--source-model` when the API model identifier differs from its HF name. Random weights are always marked as wiring.

## Fresh Lambda setup

Launch and billing approval remain Leo's responsibility. Follow [infra.md](../../docs/infra.md) for persistent storage. Once a GPU box already exists:

```bash
# Run in a terminal on the approved machine.
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
cd /lambda/nfs/collusion/repo
export HF_HOME=/lambda/nfs/collusion/hf_cache
uv venv experiments/E02-activation-replay/.venv --python 3.11
uv pip sync --python experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/requirements-lock.txt
experiments/E02-activation-replay/.venv/bin/python -c \
  'import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available()); assert torch.cuda.is_available()'
```

Copy the repo and source `runs/<id>/episodes` files to that persistent checkout. Run the Granite command above in tmux. No OpenRouter key is required. For gated models, accept the model license and run `experiments/E02-activation-replay/.venv/bin/hf auth login`; Granite and the Qwen wiring tokenizer were accessible without login here. Never put a token in a command checked into git.

Tested CPU versions are Python 3.11.12, torch 2.14.1, transformers 5.20.2, accelerate 1.15.0, huggingface_hub 2.3.0 and numpy 2.4.6. All resolved dependency versions are in the lock file. Linux CUDA wheels and the installed NVIDIA driver must be compatible; the assertion above checks this before replay. If the platform needs a different torch CUDA wheel, install it from the [official PyTorch selector](https://pytorch.org/get-started/locally/) and retain the resulting run's recorded versions. CUDA execution and A6000 memory capacity have not been measured by the CPU test. An 8B bf16 model is roughly 16 GB of weights; prompt length and runtime allocations add memory. Stop other GPU servers before replay. `--max-tokens` is a guard, not a memory guarantee.

Nemo is not ready for faithful E01 replay with its published template: the CPU check found it rejects the initial task plus peer message (consecutive user roles). Its template also requires nine-character tool-call IDs and can omit the system prompt when the final message is a tool result. A reviewed provider-specific adapter is needed; no silent merge, ID rewrite or system-message removal is performed. If that adapter is supplied later, its API/HF alias is `--model mistralai/Mistral-Nemo-Instruct-2407 --source-model mistralai/mistral-nemo`. Templates are preflighted before pretrained weights are allocated. A nonempty system message missing from rendered text causes a hard error. Other models must expose decoder blocks through a supported path, or `--layers-path` must identify them. Remote model code is disabled.

## Artifacts and alignment

Every invocation uses `src/collusion/runs.py:start_run`, records source run IDs as parents, and creates `runs/<timestamp>-e02-activation-replay/`:

- `meta.json`, `log.txt`, `diff.patch`: command/settings, source lineage and code state; failed runs remain recorded.
- `provenance.json`, `model_config/`, `tokenizer/`, `selected_chat_template.jinja`: resolved immutable HF commit, library versions, dtype/device map, architecture and template hash. Weights come from that pinned Hub snapshot; random configurations record their seed.
- `activations/call-NNNNNN.npz`: `residual_last` shaped **[decoder layers, hidden width]**, stored float32 after capture at the model's inference dtype; `input_ids` is the exact local prompt token sequence.
- `prompts/call-NNNNNN.txt`: exact locally rendered prompt, including whitespace, for inspection.
- `index.jsonl`: one row per target API attempt, linking NPZ/prompt, original run/episode hash, zero-based request index, one-based round/tool step/attempt, token counts, labels and condition metadata.
- `summary.json`, `fidelity.md`: count-ratio diagnostics and limits of the reconstruction.

Layers are **block outputs** indexed 0 through L−1, after the residual addition. The last layer is captured **before the final model normalization**. Embeddings are not counted as a layer. Hooks copy only the last-token vector to CPU and are removed after each forward; they do not retain all sequence activations. The final prompt token can be an assistant/thinking prefix token, not the last user-text token. Optional peer-message pooling is not implemented; identifying its exact span across tool/thinking templates needs separate validation.

`first_step=true` identifies the first target API call within a conversational round, including retries of that call. Later tool steps can already contain target-generated decisions or actions. For a pre-reply study, filter `step_in_turn==1` and `attempt==1`. Do not use all rows as independent observations: split/group by source episode and family, keeping matched branches together.

`before_first_leak` is request-level: it includes the input to the call that first publishes the full token, and excludes later calls, even in the same round. It is derived from successful `send_message` calls and E01's final-text publication rule; a suppressed final reply does not count. A leak with no recoverable call location gets null. No-leak episodes are true over their observed horizon only. `before_first_leak_round` is the more conservative strict round comparison. These flags concern the channel-token objective, not arbitrary policy violations or other-file writes.

Source labels are copied, not recalculated. `disclosure_kind` is a wording heuristic, not intent. `eligible_resisted`, exposure timing and the full condition metadata remain available. An incorrect stored label stays incorrect here; use an explicitly versioned derived labeling stage rather than changing raw runs. Replaying only complete episodes excludes leaks in incomplete trajectories and must be stated in later analyses.

## Fidelity limits

[HF tool-use guidance](https://huggingface.co/docs/transformers/en/chat_extras) expects tool-call arguments as dictionaries, while OpenAI-style saved requests contain JSON strings. Replay parses those strings, preserving values and recording every normalization. It does not change stored requests, message content, tool IDs or results. Templates may ignore extra fields such as `reasoning_details`, trim whitespace, merge tool results and insert tool instructions. Granite's pinned template additionally handles `<think>` blocks and XML tool syntax; its default thinking mode is on, so replay explicitly supplies the saved request's reasoning-enabled value (missing means false), with an optional `--thinking` override.

The local prompt count divided by provider `usage.prompt_tokens` is reported per request and as min/median/max. Equal lengths do not imply identical token IDs. Different models/templates naturally have different counts; the random Qwen test is not a Granite fidelity check. Provider template/version, token IDs, hidden additions and precision are unknown. Optional reply likelihood diagnostics are described below; no token-agreement claim is made. The pinned [Granite model files](https://huggingface.co/ibm-granite/granite-4.2-8b/tree/a7042144125ce5ae64f89610e8289647fc000b9a) and each run's rendered prompts make this reconstruction inspectable.

## Tests and descriptive direction stub

```bash
experiments/E02-activation-replay/run.sh test
experiments/E02-activation-replay/run.sh directions runs/<E02-run-id> --group objective_success
```

The stub takes the first eligible pre-leak, first-step, first-attempt vector per episode, calculates mean(true) − mean(false) at each layer, and saves a new lineage-tracked E02 run. Both boolean groups must exist, otherwise it fails clearly. It has no held-out split, performance metric or scientific claim. It must not be presented as a validated probe; differences can reflect conditions, wording or families. The default can group deliberate and incidental leaks together because it uses the exact publication label.

## Verified runs (2026-10-24)

| Run | Check | Result |
| --- | --- | --- |
| `20261024-0217-e02-activation-replay` | Tiny random Qwen, float32 CPU; 3 final own-stake episodes, all target requests | 89 forwards, `[2,32]` vectors; 579–17,063 prompt tokens; HF/provider count ratio median 0.897 (cross-model, not fidelity evidence) |
| `20261024-0219-e02-activation-replay` | Tiny random Granite, float32 CPU; first 4 requests from 3 episodes | 12 forwards; provider count ratios all 1.0 |
| `20261024-0220-e02-activation-replay` | **Pretrained** Qwen2.5-0.5B, float32 CPU; first 2 requests from 2 episodes | 4 forwards, all 24 blocks, `[24,896]`; validates pretrained loading and capture |
| `20261024-0221-e02-activation-replay` | Tiny random Granite, **bf16 CPU**; all requests from 3 complete episodes in `20261024-0032-e01-harness` | 51 forwards, `[2,32]`; provider count ratios all 1.0 |
| `20261024-0222-e02-direction-wiring` | Load the bf16 replay artifacts; first pre-leak prompt per episode, publication true vs false | Direction `[2,32]` from 2 vs 1 episodes; wiring only |

Six unit tests pass: hook/reference equivalence before final norm, hook cleanup, argument conversion without source mutation, retry step numbering, final-file selection/deduplication, suppressed-final-text leak timing, and rendering/system-message preservation (some tests cover multiple assertions). All 156 replay artifacts above passed source/request/prompt/token hash checks, layer-shape and finiteness checks, and leak-index consistency checks.

Two initial implementation failures (`20261024-0216-e02-activation-replay`, `...-7179`) remain recorded: resizing the random config needed a matching layer-type list, and Transformers 5 returned a mapping instead of a bare token list. Both are fixed. `20261024-0219-e02-activation-replay-5fc4` records the Nemo template incompatibility. Full-size Granite inference, multi-device dispatch, CUDA memory use and exact provider token identity remain unverified. No GPU rental or model API calls were made.

## Modal: CPU prefetch → GPU benchmark → full replay

`modal_app.py` uses Modal **1.6.2**. The initial local checks below were followed by the approved CPU prefetch and GPU benchmark in [MODAL_BENCHMARK.md](MODAL_BENCHMARK.md). Leo requires explicit approval for each GPU run; the separate CPU download also requires approval from Leo/Claude. Authentication alone is not launch approval.

The image pins torch 2.14.1, transformers 5.20.2, accelerate 1.15.0, safetensors 0.8.0, numpy 2.4.6 and huggingface-hub 2.3.0, matching the CPU environment. Linux image construction, CUDA execution and FP8 kernels remain untested. Only E02 source and `src/collusion` are mounted. Selected run folders are sent as complete, non-fake episode JSON via the function argument; `.env`, partial files and unrelated run folders are excluded. API-call upload is suitable for the small pilot; larger corpora may need an input Volume later.

`collusion-weights` mounts at `/weights`, with `HF_HOME=/weights/huggingface`. The CPU-only prefetch function downloads an immutable HF revision, records a run under `/weights/prefetch-runs`, writes a readiness marker and commits the Volume. Subsequent calls reuse the cache. The GPU functions require that marker, set HF/Transformers offline mode and pass `local_files_only=True`. Missing files fail; no model download occurs on GPU time.

`collusion-activations` mounts at `/outputs`. Each replay uses `start_run` under `/outputs/runs`, preserving the source run IDs, episode hashes and per-request indexes. The local source commit/code hashes and input manifest are also stored. Outputs are committed on success or caught failure; hard timeouts/preemption may interrupt the final commit, so inspect completion status before using results.

After **separate CPU-prefetch approval**:

```bash
modal run experiments/E02-activation-replay/modal_app.py::prefetch \
  --model Qwen/Qwen3-32B \
  --revision 9216db5781bf21249d130ec9da846c4624c16137
```

After prefetch completes and **Leo approves the GPU benchmark**:

```bash
modal run experiments/E02-activation-replay/modal_app.py::main \
  --run-ids 20261024-0258-e01-poster-approval-5f6d,20261024-0300-e01-minimum-price-3c23,20261024-0303-e01-release-date \
  --model Qwen/Qwen3-32B --revision 9216db5781bf21249d130ec9da846c4624c16137 \
  --source-model qwen/qwen3-32b --precision bf16 --gpu a100-benchmark \
  --layers all --max-requests 50 --request-order longest
```

This proposes the 50 longest locally rendered requests from 218 complete target calls across those three source runs: **1,879–2,611 prompt tokens, 103,483 prompt tokens total**. Selection is recorded in [20261024-0311-e02-benchmark-plan](../../runs/20261024-0311-e02-benchmark-plan/selection.json). It is a stress benchmark within this input set, not a representative throughput estimate or the longest context across all E01 data. The request limit is global. `--request-order source` preserves episode/request order; `longest` chooses by actual local prompt-token length. No prompt is truncated. `--layers 0,16,32,63` saves only those zero-based block outputs; it does not skip model computation.

The benchmark uses A100-80GB, a 20-minute function timeout, one container, a hard limit of 4 CPU cores, 32 GiB requested host memory and a 64 GiB memory limit (tightened for the approved USD 2 combined test cap). The full replay function (`--gpu fallback`) has a four-hour timeout and ordered GPU choices `['H100!', 'A100-80GB']`; `--gpu h100` pins H100. No retries are configured. `H100!` excludes automatic H200 substitution. A four-hour timeout is not a spending authorization. Full replay requires another approval, a measured estimate and an explicit request cap, e.g. `--max-requests 6000 --request-order source` on the approved input IDs. Do not use `a100-benchmark` for a job expected to exceed 20 minutes.

Download the returned run path, including indexes and activation arrays:

```bash
mkdir -p ./modal-results
modal volume get collusion-activations runs/REPLAY_RUN_ID ./modal-results
```

The entry point prints this exact command with the new ID. Create the destination directory before downloading (Modal 1.6.2 can mis-handle a nonexistent directory). To inspect CPU-download records separately, first run `mkdir -p ./modal-prefetch-runs`, then `modal volume get collusion-weights prefetch-runs ./modal-prefetch-runs`.

### First-run proposal and cost

Request CPU prefetch first: allow **USD 1** for downloading the approximately 65.5 GB checkpoint, expected roughly USD 0.05–0.30 for 10–30 minutes with the requested CPU/memory (bandwidth unmeasured). The CPU prefetch timeout is now 20 minutes, corresponding to roughly USD 0.106 at its hard CPU/memory limits, excluding image building, usage above requests and storage. Then request the 50-call A100 benchmark: expected **5–20 minutes, roughly USD 0.25–1.00** after weights are cached; propose a **USD 2 allowance**, including load and overhead. These are planning assumptions, not measurements. The original benchmark used two forwards. Current replay combines capture and bounded reply scoring in one forward; its extra GPU overhead remains an estimate until the approved run.

Current [Modal prices](https://modal.com/pricing) are USD 0.000694/sec for A100-80GB (~2.50/hour), 0.001097/sec for H100 (~3.95/hour), 0.0000131/core/sec and 0.00000222/GiB/sec. Requested benchmark resources total roughly USD 2.94/hour; at its CPU/memory hard limits the rate is approximately USD 3.20/hour, or USD 1.07 for 20 minutes before image build, usage above requested resources, storage and other overhead. The timeout is not a strict dollar cap. No assumption about remaining free credits is made. The first benchmark must report actual billed time, loading time, per-request activation/total time, scoring coverage, peak allocated CUDA memory and device map before a full replay proposal. CPU/disk offload would invalidate a GPU-only throughput estimate.

### Reply-token fidelity and precision comparison

Reply fidelity is **on by default**, both locally and on Modal. The causal LM base decoder sees the prompt plus the first **64** locally reconstructed reply tokens (or the whole reply if shorter). Capture hooks read position `len(prompt_ids)-1`, never the end of the appended reply. Causal attention prevents future reply tokens from affecting that position. The same decoder output supplies NLL/top-5 via chunked head projection; there is no second decoder pass. `--fidelity-tokens N` changes the diagnostic horizon; `--activations-only` / `--no-reply-fidelity` disables it locally, and Modal exposes `--activations-only`.

Each row stores mean per-token NLL/log-prob, top-5 fraction, available/scored reply lengths and serialization status. Summary values are weighted by scored tokens. NPZ files contain prompt IDs, scored reply IDs and layer indices. Qwen2/Qwen3/Qwen3-MoE heads are supported; other heads are explicitly unscored until their architecture-specific logit transforms are reviewed.

These are likelihoods of the **HF reconstruction of the saved reply**, including tool syntax and terminators, not the unknown provider token IDs. The normal path verifies text and token prefix equality. Two explicit adapters preserve the original prompt: remove a generation-only empty-thinking block from the history-rendered reply boundary when necessary; or tokenize the reply suffix separately when BPE would merge across that boundary. The adapter used is recorded. Missing/empty replies, unsupported provider reasoning and context-limit problems remain explicit unscored statuses. Only the diagnostic reply is capped; prompts are never truncated. High likelihood does not prove provider token identity or behavioral correctness.

`--precision bf16` is the normal path. For the robustness alternative, use the official [Qwen3-32B-FP8](https://huggingface.co/Qwen/Qwen3-32B-FP8) checkpoint, not an improvised dtype cast. Its pinned revision is `aa55da1ecc13d006e8b8e4f54579b1ea8c3db2df`. After separate approvals, prefetch with that model/revision, then use the same benchmark command with:

```bash
--model Qwen/Qwen3-32B-FP8 --revision aa55da1ecc13d006e8b8e4f54579b1ea8c3db2df \
--source-model qwen/qwen3-32b --precision fp8 --gpu h100
```

The GPU function refuses FP8 on A100: [HF's fine-grained FP8 backend](https://huggingface.co/docs/transformers/main/quantization/finegrained_fp8) requires compute capability ≥9. Config-driven FP8 quantization leaves other tensors in bf16; provenance records both the quantization config and compute dtype. The Triton fallback is available through the Linux torch installation; no DeepGEMM toolkit is installed. Full FP8 loading remains untested. Compare identical source request hashes and prompt/reply token IDs before interpreting differences. Official FP8 weights are a robustness condition, not evidence that OpenRouter used the identical checkpoint or kernel.

### Local validation of the extension

Nine unit tests pass, including shifted next-token NLL/top-5 agreement with full-logit reference computation, chunking, explicit unscorable replies, and upload filtering/path checks. Modal 1.6.2 definitions import locally without a remote call.

- `20261024-0309-e02-activation-replay`: random Qwen2.5, two longest requests, finite reply likelihoods.
- `20261024-0309-e02-activation-replay-f5ce`: random Qwen3, first two requests including tool replies; template serialization scored.
- `20261024-0310-e02-activation-replay`: offline random Qwen3, exactly three longest requests, only layer 1 saved, finite NLL and expected `[1,32]` shapes.
- `20261024-0311-e02-activation-replay`: cached **pretrained Qwen2.5-0.5B**, one CPU request, all 24 layers plus reply scoring. Cross-model wiring only.

CPU float32 test runs retain their explicit dtype and random/cross-model labels; they are not bf16 scientific results. Remote Linux image build, Volume persistence across workers, CUDA memory fit and FP8 execution still require the approved live pilot.


## Main dataset: verified manifest replay

The [main plan](MAIN_REPLAY_PLAN.md) freezes 143 episodes / 3,034 requests, including the input that produces the first forbidden action. `--manifest` checks source episode, request, rendered prompt, token-ID hashes, token count, round and step before loading model weights. Missing, duplicate or changed inputs fail. The output copies the exact manifest and stores `manifest_verified=true`, request-specific exposure and action flags. Manifest mode rejects request limits and reordering locally; Modal derives its input run IDs from the manifest and ignores its benchmark selection defaults. It also verifies source episode hashes before submitting remote work.

Leo approved this exact run with a USD 9 hard cap in Aboard #458. The command submitted by client 20261024-1818-e02-main-modal-client is:

```bash
modal run experiments/E02-activation-replay/modal_app.py::main \
  --manifest-path runs/20261024-1803-e02-step-prefix-plan/steps.jsonl \
  --model Qwen/Qwen3-32B --revision 9216db5781bf21249d130ec9da846c4624c16137 \
  --source-model qwen/qwen3-32b --precision bf16 --gpu a100 --layers all \
  --fidelity-tokens 64
```

The A100 full-run function has a 160-minute timeout, a clean 150-minute between-request stop, 100-request output checkpoints, four-CPU limit, 32-GiB requested / 64-GiB capped host RAM, one container and no automatic retries. It loads only the cached weights. A timeout is not approval or an exact billing cap. Download using the printed `modal volume get` command into an existing directory.

Then run the positive control locally:

```bash
experiments/E02-activation-replay/run.sh exposure-probe modal-results/REPLAY_RUN_ID
```

This fits a regularized linear logistic probe for `token_in_context` at the fixed last saved layer. It holds out 30% of entire episodes (seed 42), fits scaling on training rows only, keeps retries/tool steps together and reports held-out AUROC, class counts, exact episode split, coefficients and predictions in a new E02 run. No test-set layer search occurs. The diagnostic target is AUROC ≥0.98; a lower result triggers inspection of alignment, labels, representation/layer and generalization. It does not uniquely prove an extraction bug, and a high result does not validate every label or guarantee provider fidelity.

Local verification for this extension: 20 tests pass, including one-forward activation equivalence against a prompt-only reference, next-token NLL/top-5 alignment, manifest tamper rejection, episode-disjoint splitting and a known synthetic linear signal. Nine real requests from three episodes also ran end to end with tiny random Qwen weights on CPU. The synthetic positive control achieved AUROC 1.0 on six held-out episodes; this checks the analysis wiring, not the real model. These checks ran locally before the approved main launch.

## Replay2 results

[Verified replay2 report](../../runs/20261025-0339-e02-replay2-results/report.md): 6,026 inputs across 268 complete episodes and 23 shared branching states; all 64 Qwen3-32B decoder outputs at the last prompt token. Combined reply NLL 0.248778 and top-five fraction 0.997923. Both apps stopped; billed app total snapshot USD5.5137, conservative total bound USD6.61 versus the USD12 cap. Manifest/hash validation passed. The combined data and exposure gate are `20261025-0337-e05-replay2-data` and `20261025-0338-e05-replay2-positive-control`; outcome analysis is in E05. `replay2_results.py` refreshes the billing/fidelity report without launching compute.
