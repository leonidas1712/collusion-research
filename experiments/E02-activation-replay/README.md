# E02: replay target inputs and collect activations

**Question:** can we turn saved E01 requests into indexed, reproducible residual-stream measurements for the later probe experiment?

**Status:** CPU validation in progress. This folder does not generate responses, call OpenRouter, rent GPUs, or change E01. A replay rebuilds inputs with the selected Hugging Face template; it cannot recover the provider's unknown exact input tokens.

## Run

From the repository root, with `uv` installed:

```bash
experiments/E02-activation-replay/run.sh replay \
  runs/20261024-0126-e01-harness-9a4c \
  --model ibm-granite/granite-4.2-8b \
  --revision a7042144125ce5ae64f89610e8289647fc000b9a
```

The entry point creates its own `.venv` on first use from `requirements-lock.txt`. It leaves the root E01 environment alone. Default inference is bf16, `device_map="auto"`, SDPA, evaluation mode, no gradients and no KV cache. The base decoder performs exactly one forward pass per saved target API attempt; no generation or vocabulary logits are needed. Input tensors go to the input-embedding device. Accelerate dispatches the remaining layers.

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

For Nemo, use `--model mistralai/Mistral-Nemo-Instruct-2407 --source-model mistralai/mistral-nemo`. Its template may require tool-call IDs to be exactly nine alphanumeric characters; malformed IDs cause a visible template error rather than a silent rewrite. Other models must expose decoder blocks through a supported path, or `--layers-path` must identify them. Remote model code is disabled.

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

The local prompt count divided by provider `usage.prompt_tokens` is reported per request and as min/median/max. Equal lengths do not imply identical token IDs. Different models/templates naturally have different counts; the random Qwen test is not a Granite fidelity check. Provider template/version, token IDs, hidden additions and precision are unknown. No likelihood or token-agreement claim is made. The pinned [Granite model files](https://huggingface.co/ibm-granite/granite-4.2-8b/tree/a7042144125ce5ae64f89610e8289647fc000b9a) and each run's rendered prompts make this reconstruction inspectable.

## Tests and descriptive direction stub

```bash
experiments/E02-activation-replay/run.sh test
experiments/E02-activation-replay/run.sh directions runs/<E02-run-id> --group objective_success
```

The stub takes the first eligible pre-leak, first-step, first-attempt vector per episode, calculates mean(true) − mean(false) at each layer, and saves a new lineage-tracked E02 run. Both boolean groups must exist, otherwise it fails clearly. It has no held-out split, performance metric or scientific claim. It must not be presented as a validated probe; differences can reflect conditions, wording or families. The default can group deliberate and incidental leaks together because it uses the exact publication label.
