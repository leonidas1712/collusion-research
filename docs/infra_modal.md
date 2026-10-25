# Modal for the collusion research sprint

Research date: 2026-10-22. Conceptual proposal only. No resources launched, code written, or performance measurements taken.

## Recommendation

Keep the proposed split: Modal for parallel behavior episodes, and Lambda for interactive replay and steering. Modal can also run the white-box work. Its hosted notebooks make it a credible fallback if Lambda capacity is unavailable.

The useful abstraction is a run with a model revision, dataset or episode specification, operation, and artifact destination. Provider choice comes after that specification. A vLLM HTTP endpoint alone does not provide activation extraction or arbitrary PyTorch hooks.

These are design recommendations from the project requirements, rather than measured performance claims. The project requirements are in [AGENT_BRIEF.md, sections 2–3](../AGENT_BRIEF.md) and [the research plan](plan.md#generate-then-replay).

## What runs where

| Operation | Proposed Modal resource | Output |
| --- | --- | --- |
| Generate a dataset | GPU Function with a persistent vLLM engine, or an HTTP server | Text, exact token IDs, sampling configuration |
| Run multi-turn episodes | CPU/local coordinator calling a shared GPU server | Per-turn records, mock tool actions, episode labels |
| Extract activations | GPU Function with Transformers and PyTorch hooks | Selected layers and positions, indexed by episode and turn |
| Fit probes | CPU Function or local analysis | Probe weights, split definitions, metrics |
| Steer a model | GPU Function with HF generation and hooks | Intervention configuration and new episodes |
| Fine-tune | Separate GPU Function with persistent checkpoints | Adapter or model checkpoint and training provenance |
| Explore interactively | Hosted Modal Notebook or a container debug shell | Notebook plus exported run artifacts |

Modal supports Python GPU Functions with configurable GPU types and multiple GPUs on one host. Its guide recommends L40S for inference. GPU access requires a payment method. These capabilities supply the compute, while our application supplies hooks, episode state, and provenance. [GPU guide](https://modal.com/docs/guide/gpu)

## Serving and exact token IDs

Modal's current vLLM example starts a subprocess inside `@app.server`, mounts weight and compilation caches, and exposes an OpenAI-compatible endpoint. The example pins vLLM and a model revision. Changing the model also requires a memory and server-configuration review. This is a suitable starting architecture, rather than a ready Qwen3-8B configuration. [Official serving example](https://modal.com/docs/examples/vllm_inference)

**Recommended first path:** format each turn with our pinned tokenizer and chat template, then send the resulting integer IDs to `/v1/completions`. The current request schema accepts `list[int]` and supports `return_token_ids=True`. That option returns prompt IDs and generated IDs. For streaming, prompt IDs appear in the first chunk and generated IDs arrive as deltas. `return_tokens_as_token_ids` is a different option for logprob strings. It is not the primary token capture mechanism. [vLLM completion protocol](https://docs.vllm.ai/en/stable/api/vllm/entrypoints/openai/completion/protocol/)

**Fallback:** run vLLM directly inside a Modal Function. `TokensPrompt` accepts `prompt_token_ids`. `RequestOutput.prompt_token_ids` records the prompt, and each `CompletionOutput.token_ids` records the output. This removes dependence on HTTP client handling of extra response fields. A resident engine can handle successive turns without reloading weights. [Input schema](https://docs.vllm.ai/en/stable/api/vllm/inputs/), [output schema](https://docs.vllm.ai/en/stable/api/vllm/outputs/)

There is also a dedicated `/inference/v1/generate` API for token IDs in and out. The current docs describe registration with `--enable-scale-out` or `--tokens-only`. Its token output retains generated stop-string tokens even when returned text omits them. This is an alternative, with additional deployment configuration to validate. [Tokens API](https://docs.vllm.ai/en/stable/serving/online_serving/token_in_token_out/)

For this project, the proposed record for each target turn contains:

- Model and tokenizer revisions, template hash, and package versions
- Exact prompt IDs and generated IDs, including available special tokens
- Sampling configuration, seed, stop conditions, finish reason, and request ID
- Human-readable messages, mock tool actions, episode ID, and turn index
- An explicit `enable_thinking=False` choice, as required by the brief.

The later S2 spike must validate the pinned server version and actual response payload. Particular checks are special-token insertion, truncation, stop tokens, and preservation of extra fields by the client. A successful text response does not establish replay fidelity. Each turn requires its own prompt IDs because rebuilding the final transcript can change templates and thinking blocks.

### Identical weights and templates across providers

Yes: both providers can load the same immutable model snapshot. Transformers accepts a commit ID through `revision`, or a local model directory. [Transformers model loading](https://huggingface.co/docs/transformers/model_doc/auto)

The proposed shared manifest pins the weight commit, tokenizer commit, template bytes, special-token configuration, and bf16 dtype. vLLM exposes `--revision`, `--tokenizer-revision`, `--chat-template`, and `--dtype`. [vLLM server configuration](https://docs.vllm.ai/en/stable/cli/serve/)

The strongest practical arrangement formats prompts once in the coordinator and saves the resulting IDs. Lambda replays those IDs directly. Both sides also compare hashes of the actual downloaded files. Matching files and tokens does not guarantee bitwise-identical activations across vLLM and HF kernels. The replay fidelity spike remains necessary.

## Persistence and reliability

Use separate persistent locations for model caches and run artifacts. A proposed artifact layout is one directory per run, with separate files for each episode and attempt. Each worker owns its files. A coordinator produces the final manifest after successful writes.

Modal Volumes suit model distribution and other write-once, read-many workloads. Writers commit changes, and existing readers reload to see those changes. Reload requires closed files. Concurrent edits to the same file use last-write-wins semantics, without distributed file locking. The docs recommend limiting concurrent small commits. Volume v2 remains Beta, with an explicit data-loss caveat. For the sprint, prefer v1 for primary artifacts and export independent copies of raw episodes. [Volumes](https://modal.com/docs/guide/volumes)

A Modal Volume does not directly mount onto a Lambda VM. Proposed cross-provider handoff: transfer completed run artifacts through a local download or common object storage. Both environments load the same pinned model revision. The transfer manifest records filenames, sizes, hashes, and tokenizer provenance. This handoff needs a later wiring check.

GPU Functions can be preempted. Modal restarts an interrupted Function on the same input, so application retries must not silently duplicate episodes or overwrite successful results. The dedicated guide explicitly says `nonpreemptible` does not support GPU Functions. Checkpoints and independently saved turns remain necessary. [Preemption](https://modal.com/docs/guide/preemption)

Function execution defaults to five minutes and supports up to 24 hours per attempt. Startup has a separate timeout. Proposed jobs use explicit timeouts, bounded retries, and resumable chunks. A restarted episode gets a distinct attempt ID if resumption cannot preserve its state. [Timeouts](https://modal.com/docs/guide/timeouts)

## Cold starts and episode concurrency

Cold latency includes capacity queueing and initialization. Container startup alone does not measure model readiness. Weights, CUDA initialization, compilation, and engine warmup can add latency. No Qwen3-8B cold-start duration is established here. [Cold starts](https://modal.com/docs/guide/cold-start)

Functions scale to zero by default. `scaledown_window` controls idle retention, `min_containers` maintains a warm minimum, and `max_containers` limits replicas. Warm containers cost money. Proposed initial configuration: one GPU replica, no permanent warm minimum, and a few minutes of idle retention. Multiple episodes share that replica through concurrent requests. More replicas follow measured demand. [Autoscaling](https://modal.com/docs/guide/scale)

The coordinator retains episode state outside GPU containers and submits a complete turn context for each request. This proposal prevents replica replacement from losing conversation state. It also keeps GPU work separate from waits for the persuader API.

GPU memory snapshots remain Alpha. They can reduce initialization or compilation work, but do not generally accelerate weight reads. The guide also lists multi-GPU and compiler limitations. Treat snapshots as a later optimization. [Memory snapshots](https://modal.com/docs/guide/memory-snapshots)

## Interactive work, notebooks, and SSH

Modal offers hosted Jupyter notebooks with GPU selection, collaborative editing, and a ten-minute default idle shutdown. The default image includes PyTorch and Transformers. Custom images, Secrets, and shared Volumes are supported. Volume files under `/mnt` persist across kernel starts. A custom notebook image comes from a deployed Function. Proposed use: exploratory hooks and plots, followed by reusable analysis outside notebook state. [Hosted notebooks](https://modal.com/docs/guide/notebooks)

For terminal access, `modal container list` identifies running containers and `modal shell <container-id>` opens a debug shell. Interactive Functions support Python breakpoints and IPython through `modal run -i`. These are documented alternatives to ordinary VM SSH. They do not establish a permanent machine identity or durable root filesystem. [Development and debugging](https://modal.com/docs/guide/developing-debugging)

Sandboxes support arbitrary subprocess commands through `Sandbox.exec`. Their default lifetime is five minutes, configurable to 24 hours, with a separate idle timeout. GPU Sandboxes require the `gvisor` runtime and remain preemptible. They are useful for isolated processes, but add little to this sprint's mocked tool environment. [Sandboxes](https://modal.com/docs/guide/sandboxes), [GPU Sandbox resources](https://modal.com/docs/guide/sandbox-resources)

## Fine-tuning and white-box work

Modal's training quickstart offers Dojo for SFT/RL, a Tinker-compatible Spindle server, and custom training through Clustered Functions. These are available routes, not dependencies we need for the sprint. [Training quickstart](https://modal.com/docs/guide/training-quickstart)

Its Unsloth example demonstrates LoRA training, persistent checkpoints, and checkpoint resumption. That example defaults to 4-bit frozen weights. Copying its defaults conflicts with our bf16 interpretability setup. Proposed first training route: bf16 base weights with a LoRA adapter, subject to a memory estimate and scope approval. Full fine-tuning requires a separate estimate for optimizer state, gradients, activations, and sequence length. [Fine-tuning example](https://modal.com/docs/examples/unsloth_finetune)

The proposed white-box path uses a separate Transformers environment with plain PyTorch hooks. Replay reads saved token IDs. Steering runs live generation with hooks and then saves the changed outputs. A fine-tuned adapter creates a new model identity for generation, replay, and probes. No existing probe result automatically transfers to that identity.

## Cost and credits

Current base GPU rates, rounded from published per-second prices:

| GPU | Approximate USD/hour | Proposed role |
| --- | ---: | --- |
| A10 | $1.10 | Smaller-context serving candidate |
| L40S | $1.95 | Initial Qwen3-8B serving candidate |
| A100 40GB | $2.10 | Alternative GPU job |
| A100 80GB | $2.50 | More memory for hooks or training |
| H100 | $3.95 | Later throughput comparison |

CPU and RAM add charges. Functions cost $0.04716/core-hour and $0.007992/GiB-hour. Notebook/Sandbox CPU and RAM rates are about three times higher. Volumes include 1 TiB free, then $0.09/GiB-month. Starter includes $30/month of compute and lists ten concurrent GPUs. Shared Endpoints use separate token billing. [Pricing](https://modal.com/pricing)

Derived example: one L40S Function with two requested CPU cores and 16 GiB RAM costs about $2.17/hour at those resource levels. Startup and warm idle time add GPU occupancy. Actual CPU/RAM usage can change the total. This is an estimate, not a measured serving cost.

### Illustrative budget for 300 short episodes

Assume six target turns per episode and 256 generated tokens per turn. That gives 1,800 target calls and 460,800 generated tokens. The table uses hypothetical aggregate throughput across concurrent episodes. Each throughput includes prompt processing and request overhead during the generation phase. These values are sensitivity scenarios, not Qwen3 benchmarks.

| Effective output tokens/second | Generation occupancy | Estimated Function cost at $2.17/hour |
| ---: | ---: | ---: |
| 50 | 2.56 hours | $5.56 |
| 100 | 1.28 hours | $2.78 |
| 300 | 0.43 hours | $0.93 |

Formula: generated tokens / effective throughput / 3,600 × hourly rate. Extra warm gaps and startup add about $0.36 per ten minutes. Six total occupied hours cost about $13.02. Ten total occupied hours cost about $21.70. These estimates exclude persuader API charges, retries, replay, and training. Long contexts or poorly overlapped persuader calls can dominate occupancy. Episode count alone cannot establish a reliable price.

The brief records an additional $50 sprint credit, valid until November 1. This research did not verify its redemption or account balance. The project rule requires explicit approval before a job expected to exceed about $20.

## Decisions and remaining checks

Recommended next decisions:

1. Keep Modal as the behavior-serving option and as a fallback for white-box compute.
2. Prefer preformatted token IDs with completions, with direct vLLM engine access as the fallback.
3. Start with one L40S replica, bounded scaling, and persistent per-turn artifacts.
4. Keep fine-tuning and GPU snapshots outside the first wiring path.

The next implementation phase must establish Qwen3 memory fit, exact token capture, cold and warm latency, replay agreement, checkpoint recovery, and cross-provider transfer. Current docs establish capabilities, not those workload results. Account credits and available GPU capacity also remain unchecked.
