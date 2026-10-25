# Lambda Cloud: how it works and how we would use it

Research notes, 2026-10-22. Facts come from Lambda's docs and pricing pages (links at the end). Lines marked **(inference)** are our reasoning, not documented facts. Nothing here has been tested yet.

## The short version

Lambda gives you a whole Ubuntu VM with a GPU. You SSH in as `ubuntu`, and PyTorch, CUDA, Docker and JupyterLab are already installed. It is the "box I SSH into and do whatever I want" option.

Three rules shape everything:

1. **No pause.** An instance can only be launched, restarted or terminated. Billing runs per minute until you terminate it, even when it is idle. Shutting down from inside the OS does not stop billing.
2. **Terminate wipes the local disk.** Anything that must survive goes on a **persistent filesystem** (network storage). The filesystem lives in one region, and it can only be attached **when the instance is launched**, not afterwards.
3. **Only SSH (port 22) is open by default.** Jupyter, vLLM and other servers are reached through an SSH tunnel, without opening ports.

## Facts

### Instances

- **Default image:** "Lambda Stack" on Ubuntu (22.04 or 24.04). It includes the NVIDIA driver, CUDA, cuDNN, NCCL, PyTorch, JAX, Triton, Docker with the NVIDIA container toolkit, JupyterLab, tmux and git. The docs give no version numbers, so we check on first launch. Other images ("GPU Base", plain Ubuntu) can be chosen through the API. The docs don't mention custom images.
- **Launching:** through the web console or the Cloud API, using one SSH key and optional filesystems, a firewall ruleset and cloud-init `user_data`. Launching takes a few minutes. JupyterLab can take a few more minutes after the instance is up.
- **Capacity:** not guaranteed. Not every type is available in every region. The API's instance-types call lists `regions_with_capacity_available`. New accounts have an instance-count quota that rises as invoices are paid.
- **Billing:** hourly rate, charged per minute, from the moment the instance passes health checks until it is terminated. There is no stop or pause endpoint. A marketing page says "stop", but the docs and the API reference say restart and terminate only.

### Prices for one GPU (per hour, lambda.ai/pricing, read 2026-10-22)

| GPU | Memory | $/hr | Notes |
|---|---|---|---|
| Quadro RTX 6000 | 24 GB | 0.69 | Old (Turing); no bf16. Avoid. |
| **A6000** | **48 GB** | **1.09** | Cheapest card that fits an 8B model with room for long episodes. Also offered as 2x and 4x. |
| A10 | 24 GB | 1.29 | Too small for comfortable 8B work. |
| A100 40 GB (SXM or PCIe) | 40 GB | 1.99 | Faster than the A6000, with less memory. |
| GH200 | 96 GB | 2.29 | Cheap for its memory, but it has an **ARM CPU**, so Python and vLLM wheels can be a problem **(inference)**. Avoid for now. |
| H100 PCIe | 80 GB | 3.29 | For 20B–32B models. |
| H100 SXM | 80 GB | 4.29 | Also offered as 2x, 4x and 8x. |
| B200 | 180 GB | 6.99 | Not needed. |

- **Gaps in the price list:** there is no single A100 80 GB (only an 8x at $2.79 per GPU). The pages carry no "last updated" date, so check the console at launch.
- **What $400 buys:** about 365 A6000-hours, 200 A100-hours or 120 H100 PCIe hours.

### Persistent filesystems

- **Where it appears:** mounted at `/lambda/nfs/<name>`, with a symlink in `~`.
- **Region-locked:** the filesystem must be in the same region as the instance, and it can't be moved between regions.
- **When to attach:** at launch only. Forgetting it means terminating and launching again.
- **Size and price:** practically unlimited (Texas region: 10 TB). Billed per GiB used per month, charged hourly, for as long as it exists, mounted or not. The example rate in the docs is $0.20/GiB/month; the real price shows when you create it. 200 GB costs about $40/month at that rate. There are no ingress or egress fees.
- **Other access:** rsync, or an S3 adapter in some regions.
- **No speed figures in the docs.** It is network storage, so it is probably slower than the local SSD for loading model weights **(inference; measure in spike S5)**.
- **Gotcha:** deleting files in JupyterLab moves them to hidden `.Trash-*` folders, which still count as billed storage.

### Network and access

- **Connecting:** `ssh ubuntu@<ip>`. SSH keys are added to the account before launch.
- **Firewall:** only TCP 22 and ICMP are open by default. Per-instance rulesets must be attached at launch.
- **Recommended way to reach a service:** an SSH tunnel, `ssh -L 8888:127.0.0.1:8888 ubuntu@<ip>`.
- **JupyterLab:** opened from the console's "Cloud IDE" button, or from the `jupyter_url` field in the API.
- **API key:** has full account access (it can launch billable machines). It goes in `.env` only.

### Cloud API

- **Endpoints:** REST at `https://cloud.lambda.ai/api/v1/`, with a Bearer API key. The documented calls cover launching, restarting and terminating instances, listing and creating filesystems, firewall rules, SSH keys, regions, and instance types with live capacity.
- **Rate limits:** about one request per second; launches are limited to one every 12 seconds.
- **CLI:** no official command-line tool is documented. A small script around the API covers launching and terminating.

## How we would use it **(inference: our proposed design)**

### The picture

```
 laptop (user + coding agents)
   │  ssh / VS Code Remote / ssh -L tunnels for Jupyter (8888) and vLLM (8000)
   ▼
 Lambda VM, 1 GPU  ── local SSD (fast, wiped on terminate): copied model weights, scratch
   │
   └─ /lambda/nfs/collusion  (persistent, same region)
        repo/            git clone of this repo (code also lives on GitHub)
        venv/            uv environment (or rebuilt from uv.lock on each launch)
        hf_cache/        downloaded model weights (HF_HOME points here)
        runs/            episode logs, token IDs, activations, probes, figures
        .env             API keys (not in git)
```

### A session, start to finish

1. **Launch:** an A6000 (or A100) in the filesystem's region, through the console or one script call. A cloud-init or `setup.sh` script points `HF_HOME` at the filesystem, runs `uv sync`, and starts Jupyter bound to localhost.
2. **Connect:** SSH from the laptop with tunnels. Coding agents work on the box over SSH; tmux keeps long jobs alive if the connection drops.
3. **Work:** behaviour runs with vLLM, replay and activations with HuggingFace plus hooks, probes in Jupyter or scripts, steering with live HF generation. Every output is written under `runs/` on the filesystem.
4. **Finish:** commit and push code, then **terminate**. Nothing of value is on the local disk.

The main risk is forgetting to terminate: an idle A6000 left overnight costs about $13, and an H100 about $50. A watchdog on the box that terminates it after N idle hours, plus a daily check, removes most of that risk.

### "Run model X on data Y" as one reliable command

The goal is that a new open-weight model is a config entry, not new code:

```yaml
# configs/models/qwen3-8b.yaml
hf_id: Qwen/Qwen3-8B
revision: <pinned commit>        # pin it, so the weights and tokenizer can't change under us
dtype: bfloat16                  # no 4-bit for interpretability; quantizing changes activations
chat_template_kwargs: {enable_thinking: false}
layers_to_save: [8, 14, 20, 26, 32]
min_gpu_gb: 40
```

Every experiment then has the same three stages, each writing to `runs/<id>/`:

| Stage | Tool | Input → output | Notes |
|---|---|---|---|
| 1. Generate | vLLM (fast batched sampling) | scenario config → episode JSONL with exact prompt and generated token IDs per turn | We apply the chat template ourselves and send token IDs. |
| 2. Replay and extract | HF transformers + PyTorch forward hooks | token IDs → activations at chosen layers and positions (one file per episode) | Includes the fidelity check. Works on any HF model with no custom code. |
| 3. Analyse | numpy / sklearn / torch in Jupyter or `analysis/` scripts | activations + labels → probes, AUROC, per-turn plots | Runs on the CPU or the same GPU. |
| 3b. Intervene | HF `generate` with hooks (live) | model + direction → new episodes | Steering changes future tokens, so it can't use replay. Slower than vLLM. |

vLLM and HF can share one GPU, but it's simpler to run them one after the other: vLLM claims most of the GPU memory by default, so stop it (or cap its memory share) before loading the model in HF.

### Which GPU for which model (bf16, 2 bytes per parameter, rough)

| Model | Weights | Card | Why |
|---|---|---|---|
| Qwen3-8B, Qwen3.5-9B, Granite 8B, Gemma 4 small | ~16–18 GB | A6000 48 GB ($1.09) | Room for long contexts and an HF replay. The A100 40 GB is faster but tighter and dearer. |
| gpt-oss-20b (unpacked to bf16 for interpretability) | ~42 GB | H100 80 GB | As the plan states. |
| Qwen3-32B (a NARCBench model) | ~64 GB | H100 80 GB (tight) or 2x A6000 | Multi-GPU loading (`device_map="auto"`) works for replay. |
| 70B | ~140 GB | 2–4x H100 or 4x A6000 | Out of scope for the sprint. |

### Fine-tuning

The same box works for fine-tuning: LoRA on an 8B model fits in 48 GB, and full fine-tuning of an 8B model needs a multi-GPU node. We'd use standard HF tooling (PEFT, TRL), with checkpoints on the filesystem. Not needed for the sprint plan as written.

### Storage sizing

- **Weights:** about 16 GB per 8B model.
- **Activations:** 5 layers × 4096 values × 2 bytes ≈ 40 KB per saved position. 500 episodes × 12 turns × a few positions comes to under 1 GB.
- **Total:** a 200–300 GB filesystem is plenty. The full residual stream for every token would be about 300 KB per token, so we save only the positions we need.

## Open questions to settle by test (spikes S0 and S5)

- Which region currently has A6000, A100 and H100 capacity. Since the filesystem is region-locked, pick a region that has all three.
- How fast weights load from the filesystem compared with the local SSD. If the filesystem is slow, copy the weights to local disk at boot.
- Whether a uv environment on the filesystem works on a fresh instance with the same image, or whether rebuilding from `uv.lock` (about a minute) is simpler.
- CUDA and PyTorch versions in Lambda Stack, and whether vLLM wants its own PyTorch. If so, keep vLLM in a separate environment or a Docker container.
- The real filesystem price, and whether a 1x A100 80 GB is offered in the console.

## Sources

- [On-demand overview: images, root disks, regions, firewall default](https://docs.lambda.ai/public-cloud/on-demand/)
- [Creating and managing instances: no suspend, shutdown warning](https://docs.lambda.ai/public-cloud/on-demand/creating-managing-instances/)
- [Connecting: SSH, tunnels, JupyterLab](https://docs.lambda.ai/public-cloud/on-demand/connecting-instance/)
- [Filesystems](https://docs.lambda.ai/public-cloud/filesystems/)
- [Managing the system environment: venv, conda, Docker](https://docs.lambda.ai/public-cloud/on-demand/managing-system-environment/)
- [Importing and exporting data](https://docs.lambda.ai/public-cloud/importing-exporting-data/)
- [Billing](https://docs.lambda.ai/public-cloud/billing/)
- [Firewalls](https://docs.lambda.ai/public-cloud/firewalls/)
- [Cloud API](https://docs.lambda.ai/api/cloud)
- [Access and security](https://docs.lambda.ai/public-cloud/access-security/)
- [Pricing](https://lambda.ai/pricing) and [instances](https://lambda.ai/instances)
