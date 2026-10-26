#!/usr/bin/env python3
"""Modal replay for the frozen optional gpt-oss E08 arm."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import modal


HERE = Path(__file__).resolve().parent if modal.is_local() else Path("/app/e08")
ROOT = HERE.parents[1] if modal.is_local() else Path("/app")
OLD_ROOT = Path("/Users/leo/collusion-research")
E02 = ROOT / "experiments/E02-activation-replay" if modal.is_local() else Path("/app/e02")
PLAN = HERE / "gpt_oss_plan.json"
CONDITIONS = ("FORBID", "PERMIT", "NEUTRAL_EDIT")

app = modal.App("collusion-e08-policy-counterfactual-gpt-oss")
weights_volume = modal.Volume.from_name("collusion-weights")
outputs_volume = modal.Volume.from_name("collusion-activations")
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.14.1",
        "transformers==5.20.2",
        "accelerate==1.15.0",
        "safetensors==0.8.0",
        "numpy==2.4.6",
        "huggingface-hub==2.3.0",
        "openai-harmony==0.0.8",
    )
    .env({"HF_HOME": "/weights/huggingface", "PYTHONPATH": "/app/src:/app/e02:/app/e08", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
)
if modal.is_local():
    image = image.add_local_dir(ROOT / "src/collusion", remote_path="/app/src/collusion", ignore=["__pycache__/**"])
    image = image.add_local_file(E02 / "gpt_oss_replay.py", "/app/e02/gpt_oss_replay.py")
    image = image.add_local_file(E02 / "replay.py", "/app/e02/replay.py")
    image = image.add_local_file(HERE / "counterfactual.py", "/app/e08/counterfactual.py")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pack_inputs(plan: dict) -> list[dict]:
    from counterfactual import digest

    shard_cache: dict[str, list[dict]] = {}
    packed = []
    for call in plan["calls"]:
        run_id, filename = call["episode"].split("/", 1)
        path = OLD_ROOT / "runs" / run_id / "episodes" / filename
        raw = path.read_bytes()
        if digest(raw) != call["episode_sha256"]:
            raise ValueError(f"Episode hash mismatch: {call['episode']}")
        episode = json.loads(raw)
        record = episode["requests"][call["request_idx"]]
        if digest(record["request"]) != call["request_sha256"]:
            raise ValueError(f"Request hash mismatch: {call['call_id']}")
        shard_path = call["replay_shard"]
        if shard_path not in shard_cache:
            shard_cache[shard_path] = json.loads(Path(shard_path).read_text())["rows"]
        replay = shard_cache[shard_path][call["replay_shard_index"]]
        if replay["row_id"] != call["call_id"] or replay["request_sha256"] != call["request_sha256"]:
            raise ValueError(f"Replay row mismatch: {call['call_id']}")
        packed.append({"call": call, "record": record, "episode_started_at": episode["started_at"], "replay": replay})
    return packed


def capture(model, layers, selected_layers: list[int], ids: list[int], prompt_length: int):
    import numpy as np
    import torch

    saved = {}
    handles = []
    for layer_index in selected_layers:
        def hook(index):
            def save(module, inputs, output):
                hidden = output[0] if isinstance(output, tuple) else output
                saved[index] = hidden[0, prompt_length - 1].detach().float().cpu().numpy().copy()
            return save
        handles.append(layers[layer_index].register_forward_hook(hook(layer_index)))
    try:
        tensor = torch.tensor([ids], device=model.get_input_embeddings().weight.device)
        with torch.inference_mode():
            model.base_model(input_ids=tensor, attention_mask=torch.ones_like(tensor), use_cache=False, return_dict=True)
        values = np.stack([saved[layer] for layer in selected_layers])
        if not np.isfinite(values).all():
            raise ValueError("Non-finite activation")
        return values
    finally:
        for handle in handles:
            handle.remove()


@app.function(
    image=image,
    gpu="A100-80GB",
    timeout=1800,
    cpu=(4, 4),
    memory=(32768, 65536),
    volumes={"/weights": weights_volume, "/outputs": outputs_volume},
)
def execute(plan: dict, payload: list[dict], probe_models: list[dict], provenance: dict, mode: str) -> dict:
    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM, Mxfp4Config

    from counterfactual import digest, edit_request, score_activation
    from gpt_oss_replay import render
    from replay import decoder_layers

    model_spec = plan["model"]
    model_id = model_spec["name"]
    revision = model_spec["revision"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Pinned model revision required")
    marker = Path("/weights/ready") / model_id.replace("/", "--") / f"{revision}.json"
    if not marker.is_file():
        raise FileNotFoundError(f"Cached model marker missing: {marker}")
    if mode == "benchmark":
        allowed = set(plan["benchmark"]["call_ids"])
        payload = [item for item in payload if item["call"]["call_id"] in allowed]
        if len(payload) != plan["benchmark"]["source_calls"]:
            raise ValueError("Benchmark subset differs from frozen plan")
    elif mode != "full" or len(payload) != plan["selection"]["source_calls"]:
        raise ValueError("Invalid mode or full payload")

    import collusion.runs as run_helpers

    run_helpers.RUNS = Path("/outputs/runs")
    run_helpers.INDEX = run_helpers.RUNS / "index.jsonl"
    run = run_helpers.start_run(
        "e08-policy-counterfactual-gpt-oss",
        experiment="E08",
        settings={"mode": mode, "plan_sha256": provenance["plan_sha256"], "conditions": list(CONDITIONS)},
        parents=["20261026-2222-e05-arxiv-gpt-fresh-percall"],
        model=model_id,
        tags=["prefill", "counterfactual", "gpt-oss", mode],
    )
    started = time.perf_counter()
    try:
        torch.set_num_threads(4)
        torch.manual_seed(0)
        rendered_inputs = []
        for item in payload:
            source = item["replay"]
            for condition in CONDITIONS:
                request = edit_request(item["record"]["request"], item["call"]["scenario"], condition, plan)
                if condition == "FORBID":
                    prompt_ids = source["prompt_ids"]
                    reply_ids = source["reply_ids"]
                else:
                    record = dict(item["record"])
                    record["request"] = request
                    response = record.get("response") or {}
                    created = response.get("created")
                    date = time.strftime("%Y-%m-%d", time.gmtime(created)) if created else item["episode_started_at"][:10]
                    rendered = render(record, date, history_reasoning=item["call"]["history_reasoning_mode"])
                    prompt_ids = rendered["prompt_ids"]
                    reply_ids = rendered["reply_ids"]
                    if reply_ids != source["reply_ids"]:
                        raise ValueError(f"Edited prompt changed fixed reply tokens: {item['call']['call_id']} {condition}")
                if len(prompt_ids) + len(reply_ids) > 16384:
                    raise ValueError(f"Context overflow: {item['call']['call_id']} {condition}")
                rendered_inputs.append((item, condition, request, prompt_ids, reply_ids))

        load_started = time.perf_counter()
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            local_files_only=True,
            quantization_config=Mxfp4Config(dequantize=True),
            dtype=torch.bfloat16,
            device_map={"": "cuda:0"},
            attn_implementation="eager",
        ).eval()
        model_load_seconds = time.perf_counter() - load_started
        _, layers = decoder_layers(model)
        selected_layers = [int(layer) for layer in model_spec["layers"]]
        torch.cuda.reset_peak_memory_stats()
        rows = []
        activation_seconds = 0.0
        forward_tokens = 0
        activation_dir = run.dir / "activations"
        activation_dir.mkdir(parents=True, exist_ok=True)
        for index, (item, condition, request, prompt_ids, reply_ids) in enumerate(rendered_inputs):
            if mode == "full" and time.perf_counter() - started > plan["benchmark"]["full_timeout_seconds"]:
                raise TimeoutError("Frozen full-run wall guard reached")
            forward_started = time.perf_counter()
            values = capture(model, layers, selected_layers, prompt_ids + reply_ids, len(prompt_ids))
            elapsed = time.perf_counter() - forward_started
            activation_seconds += elapsed
            forward_tokens += len(prompt_ids) + len(reply_ids)
            layer_values = {layer: values[offset] for offset, layer in enumerate(selected_layers)}
            score, seed_scores = score_activation(layer_values, probe_models)
            key = hashlib.sha256(f"{item['call']['call_id']}|{condition}".encode()).hexdigest()[:20]
            with (activation_dir / f"{key}.tmp").open("wb") as handle:
                np.savez_compressed(handle, residual_last=values.astype(np.float32), layer_indices=np.asarray(selected_layers), input_ids=np.asarray(prompt_ids), reply_ids=np.asarray(reply_ids))
            (activation_dir / f"{key}.tmp").replace(activation_dir / f"{key}.npz")
            rows.append({
                **item["call"],
                "condition": condition,
                "score": score,
                "seed42_score": seed_scores[0],
                "seed43_score": seed_scores[1],
                "seed44_score": seed_scores[2],
                "n_tokens": len(prompt_ids),
                "teacher_forced_reply_tokens": len(reply_ids),
                "input_ids_sha256": digest(prompt_ids),
                "edited_request_sha256": digest(request),
                "activation_seconds": elapsed,
                "activation_file": f"activations/{key}.npz",
            })
            if (index + 1) % 25 == 0:
                print(json.dumps({"completed": index + 1, "total": len(rendered_inputs), "forward_tokens": forward_tokens}), flush=True)
                outputs_volume.commit()

        with (run.dir / "scores.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        summary = {
            "mode": mode,
            "source_calls": len(payload),
            "forwards": len(rows),
            "forward_tokens": forward_tokens,
            "model_load_seconds": model_load_seconds,
            "activation_seconds": activation_seconds,
            "wall_seconds": time.perf_counter() - started,
            "peak_cuda_memory_bytes": torch.cuda.max_memory_allocated(),
            "selected_layers": selected_layers,
            "plan_sha256": provenance["plan_sha256"],
        }
        run_helpers.write_json_atomic(run.dir / "gpu_summary.json", summary)
        run_helpers.write_json_atomic(run.dir / "input_manifest.json", provenance)
        (run.dir / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
        run.result(**summary)
        run.finish()
        outputs_volume.commit()
        return {"path": str(run.dir.relative_to("/outputs")), "summary": summary}
    except BaseException as exc:
        run.finish("failed", str(exc))
        outputs_volume.commit()
        raise


def local_payload() -> tuple[dict, list[dict], list[dict], dict]:
    from counterfactual import load_probe_weights

    raw = PLAN.read_bytes()
    plan = json.loads(raw)
    payload = pack_inputs(plan)
    probe_models = load_probe_weights(plan, ROOT)
    provenance = {
        "plan_sha256": hashlib.sha256(raw).hexdigest(),
        "code_sha256": {name: file_sha(HERE / name) for name in ("make_gpt_oss_plan.py", "modal_gpt_oss.py", "counterfactual.py")},
        "source_requests": [{key: call[key] for key in ("call_id", "episode_sha256", "request_sha256")} for call in plan["calls"]],
    }
    return plan, payload, probe_models, provenance


@app.local_entrypoint()
def main(mode: str = "benchmark"):
    if mode not in ("benchmark", "full"):
        raise ValueError("mode must be benchmark or full")
    plan, payload, probe_models, provenance = local_payload()
    print(json.dumps(execute.remote(plan, payload, probe_models, provenance, mode), indent=2, sort_keys=True))
