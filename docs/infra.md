# Infrastructure: how the pieces fit

2026-10-22. Conceptual design; nothing has been launched or tested yet. Details and sources are in [infra_lambda.md](infra_lambda.md) and [infra_modal.md](infra_modal.md).

## Recommendation

**One Lambda VM is home base for everything: generation, replay, activations, probes, steering and any fine-tuning. Modal is the backup, not a second pipeline.**

- **Why one machine:** the whole pipeline depends on generation and replay using the exact same weights, tokenizer and chat template. One machine and one disk make that easier, but not automatic: we still pin model revisions, hash the weight and template files, save each turn's token IDs, and run the HF fidelity check. vLLM may also need its own Python environment. Splitting across providers adds a copying step, two environments to keep matched, and Modal's GPU interruptions, for little gain at our scale.
- **Why vLLM on Lambda is enough:** one A6000 running vLLM can serve many episodes at once (the plan estimates hundreds of episodes in an hour or two). That is a planning assumption, not a measurement. The occupancy budget in infra_modal.md gives 0.4–2.6 GPU-hours for 300 short episodes, depending on throughput. The first pilot measures it.
- **When to use Modal:**
  - Lambda has no capacity in our region.
  - We need many GPUs in parallel for a short burst.
  - We want a disposable hosted notebook.

  Modal's vLLM server can take token IDs in and return them, so it can do the generation stage if needed.

## The picture

```
 laptop: user + coding agents ──ssh (+ tunnels: Jupyter 8888, vLLM 8000)──┐
                                                                         ▼
 ┌────────────────────── Lambda VM, 1x A6000 48 GB ($1.09/hr) ──────────────────────┐
 │  local SSD (fast, wiped on terminate): copy of model weights, scratch             │
 │                                                                                   │
 │  1. GENERATE   vLLM (localhost:8000)  ◄── episode runner ──► persuader API (Claude │
 │                token IDs in/out          (mock tools, board)  or GPT, from .env)  │
 │  2. REPLAY     HF transformers + PyTorch hooks → activations at chosen layers     │
 │  3. ANALYSE    probes, AUROC, per-turn plots (Jupyter / analysis/ scripts)         │
 │  3b. INTERVENE live HF generate with hooks (steering, ablation)                   │
 │  (optional)    LoRA fine-tune with PEFT/TRL → new model id, new runs              │
 │                                                                                   │
 │  /lambda/nfs/collusion  ← persistent, region-locked, attached at launch           │
 │     hf_cache/  repo/  runs/<run-id>/  .env                                        │
 └───────────────────────────────────────────────────────────────────────────────────┘
          backup only: Modal (vLLM endpoint for burst generation, hosted notebooks)
```

## "Launch model X, run it on Y, give me activations"

The goal is one reliable command, where a new model is a config entry rather than new code.

**Model config:** HuggingFace id, **pinned revision**, bf16 (never 4-bit for interpretability work, because quantizing changes the activations), chat-template options (`enable_thinking: false`), layers to save, and the GPU memory needed.

**Experiment config:** what to run it on. That might be a dataset of prompts, a scenario that generates multi-turn agent episodes, or a set of existing transcripts. It also says which positions to read (the last token before each tool call, the peer-message tokens, turn starts) and the seeds.

**Run:** `run <model> <experiment>` makes `runs/<date>-<name>-<git-hash>/` with the config, episode logs (exact token IDs per turn), activations (one file per episode), and derived results and plots. The four stages are separate commands, so any one can be re-run from saved outputs:

| Stage | Reads | Writes | Tool |
|---|---|---|---|
| Generate | model + scenario | episodes with exact prompt and generated token IDs per turn | vLLM (we apply the chat template ourselves and send IDs) |
| Replay | saved token IDs | activations + fidelity check | HF + forward hooks; works on any HF model |
| Analyse | activations + labels | probes, metrics, figures | numpy / sklearn / torch |
| Intervene | model + a direction | new episodes | HF generate with hooks (live, slower than vLLM) |

Transcripts from other models (for example, frontier-model episodes) enter at the replay stage: tokenize them with our model's template, then replay. The plan's side note says which positions are valid to read in that case.

## Which card

| Model size | Card | $/hr |
|---|---|---|
| ≤ 9B (Qwen3-8B, Qwen3.5-9B, Gemma 4, Granite 8B) | A6000 48 GB | 1.09 |
| ~20B (gpt-oss-20b, unpacked to bf16, ~42 GB) | H100 80 GB | 3.29–4.29 |
| ~32B (NARCBench's Qwen3-32B, ~64 GB) | H100 80 GB (tight) or 2x A6000 | 3.29+ / 2.18 |
| 70B | 2–4x H100 | out of scope |

$400 is about 365 A6000-hours. The brief's weekend estimate of ~25–30 GPU-hours costs about $30–35 on an A6000.

## Daily routine

1. **Launch** an A6000 in the filesystem's region, with the filesystem attached. It can't be added later.
2. **Set up:** a setup script points the HF cache at the filesystem, installs the locked Python environment, and starts Jupyter on localhost.
3. **Connect:** SSH with tunnels; run long jobs in tmux.
4. **Save as you go:** everything is written under `runs/` on the filesystem. Code is pushed to git.
5. **Terminate** when done. There is no pause, and an idle machine still bills. An idle watchdog on the box guards against forgetting.

## Gotchas we already know

- **Lambda:**
  - The filesystem is tied to one region and attaches at launch only.
  - Terminating wipes the local disk. Shutting down from inside the VM keeps billing.
  - Only port 22 is open, so use tunnels.
  - The GH200 is cheap but has an ARM CPU, so avoid it.
- **vLLM vs HF:** vLLM takes most of the GPU memory by default. Run generation and replay one after the other, or cap vLLM's memory share.
- **Token IDs:** save each turn's own prompt IDs. Rebuilding a transcript from text can change the tokens (the Qwen3 template drops earlier thinking blocks).
- **Modal (if used):**
  - GPU jobs can be interrupted and re-run, so episodes need unique attempt IDs.
  - Modal storage can't be mounted on Lambda; results have to be copied across.
  - Modal's fine-tuning example defaults to 4-bit, which conflicts with our bf16 interpretability setup.

## To settle in the first spikes (S0, S2, S5, S6)

- Which Lambda region has A6000 and H100 capacity. The filesystem has to live there.
- How fast weights load from the filesystem compared with the local SSD.
- The CUDA and PyTorch versions installed, and whether vLLM needs its own environment.
- Whether vLLM's returned token IDs match what we sent, and whether HF replay gives high probability to the generated tokens.
- The actual filesystem price, and Lambda account limits for new users.
