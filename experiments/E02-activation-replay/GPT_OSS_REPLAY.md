# gpt-oss Harmony replay

This is an isolated E02 adapter. The Qwen replay implementation and Modal app remain unchanged. It reuses E02 decoder-layer discovery, teacher-forced likelihood scoring, run provenance, cache/output volumes, and the read-only download utility.

## Environment and model

Use Python 3.11, torch 2.14.1, transformers 5.20.2, accelerate 1.15.0, safetensors 0.8.0, numpy 2.4.6, huggingface-hub 2.3.0, openai-harmony 0.0.8, and Modal 1.6.2. The Modal image pins these model dependencies. The existing local E02 virtual environment supplies the CPU planning/testing packages; Modal is installed separately as a uv tool.

Model: `openai/gpt-oss-20b@6cee5e81ee83917806bbde320786a8fb61efebee`. Load with `Mxfp4Config(dequantize=True)`, bf16, eager attention, and a single A100-80GB. Dequantization expands the released MXFP4 values; it does not recover original unquantized weights. No remote model code is needed. The tested model is public and required no HF login.

## Plan locally

Supply final complete episode JSON files. Controls need not be named `episode-*.json`.

```bash
experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/gpt_oss_replay.py \
  /absolute/path/to/recruiting-0002.json \
  /absolute/path/to/recruiting-0003.json \
  /absolute/path/to/control-0001.json
```

The printed `PLAN` path contains exact prompt/reply IDs, reasoning positions, source episode/request hashes, source labels and provider counts. Rendering uses official Harmony, LOW effort from the saved request, the saved response date, raw tool schemas/argument JSON/results, and omitted prior reasoning. A second count-only rendering retains prior reasoning for comparison. No token is added to compensate for the observed constant minus-one count difference. Use the renderer IDs directly: decoding then HF re-encoding can promote literal Harmony-looking content to control tokens. This happened in the held test episode; all 76 original renderer prompts still match provider counts within one token.

Planning issues no model API calls. Official encoding assets may download once if they are not cached. The current selected-plan artifact is `runs/20261025-2014-e02-gpt-oss-plan-5f17/plan.json`: 76 requests from three episodes, all provider-count deltas −1.

## CPU wiring checks

```bash
experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/test_gpt_oss_replay.py
experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/gpt_oss_replay.py \
  --tiny-plan runs/20261025-2014-e02-gpt-oss-plan-5f17/plan.json
```

The tiny run uses random weights and one request; its NLL has no fidelity meaning. Tests verify causality, reasoning-position extraction against native hidden states, likelihood alignment and hook cleanup.

## Paid phases

Run only within an explicitly authorized budget. The following two commands are the completed small test's allocation, not authorization for another run. The watchdog bounds client wall time at USD0.00090/s and stops the identified app on success or failure. Include all previous phase ledgers in the total; the wrapper does not discover unrelated or previous spending automatically.

```bash
experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/gpt_oss_budget.py \
  --phase prefetch --phase-ceiling .5
experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/gpt_oss_budget.py \
  --phase replay --phase-ceiling 2.8 \
  --plan runs/20261025-2014-e02-gpt-oss-plan-5f17/plan.json
```

CPU prefetch reuses `modal_app.py::prefetch` and writes the existing ready marker in Volume `collusion-weights`. The GPU entry point is **`modal_gpt_oss.py`**, a separate app. GPU loading is offline from that volume; it never downloads weights. It processes at most 100 requests, each at most 16,384 total prompt+reply tokens, and times out at 25 minutes. The inner wall check is 20 minutes. Full replay requires an explicitly budgeted plan and shards; do not silently remove these guards.

The local entry point checks the source episode hashes before submission. The GPU rechecks prompt-token hashes. Every forward pass includes the saved response, with no generation. Hooks save block outputs before final normalization at the last prompt token and every returned analysis-body token. Reasoning positions are absolute zero-based input positions **after consuming** those tokens. Header/terminator tokens are excluded from reasoning activations. Only returned reasoning is available.

## Download and verify

Completed test output: `runs/20261025-1217-e02-gpt-oss-fidelity` on Volume `collusion-activations`. Remote timestamps use UTC. The local copy has the same name.

```bash
modal volume get collusion-activations \
  runs/20261025-1217-e02-gpt-oss-fidelity ./modal-results
```

For a reproducible recursive download into `runs/` with per-file hashes, use the existing `download_volume.py` with a Python environment containing Modal. Verification uses the E02 environment:

```bash
experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/verify_gpt_oss.py \
  --replay runs/20261025-1217-e02-gpt-oss-fidelity \
  --plan runs/20261025-2014-e02-gpt-oss-plan-5f17/plan.json \
  --clients runs/20261025-2011-e02-gpt-oss-modal-client \
            runs/20261025-2016-e02-gpt-oss-modal-client
```

`verify_gpt_oss.py` is the frozen 76-request acceptance check for this plumbing test, not a generic full-dataset verifier. It also refreshes read-only Modal billing. Each NPZ contains float32 `residual_last[24,2880]`, `residual_reasoning[24,n_reasoning,2880]`, input IDs, reasoning positions and layer indices. Index entries contain source identity and per-request likelihood; the immutable plan supplies the full source labels and split. Store these test activations separately and re-replay the eventual full set.

Fidelity is token-weighted full-reply NLL/top-5, plus reasoning-body and answer/tool-body components. Full-reply metrics include Harmony framing. The Qwen first-64-token diagnostic is not exactly the same measurement. Constant count agreement does not establish exact provider tokens, and dequantized bf16 arithmetic differs from native fp4 serving.
