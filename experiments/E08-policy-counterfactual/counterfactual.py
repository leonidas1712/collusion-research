"""Pure helpers for E08 prompt edits, input packing, and frozen-probe scoring."""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
from pathlib import Path


CONDITIONS = ("FORBID", "PERMIT", "NEUTRAL_EDIT")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def digest(value: object) -> str:
    if not isinstance(value, bytes):
        value = canonical(value)
    return hashlib.sha256(value).hexdigest()


def edit_request(request: dict, scenario: str, condition: str, plan: dict) -> dict:
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    edited = copy.deepcopy(request)
    systems = [message for message in edited["messages"] if message.get("role") == "system"]
    if len(systems) != 1:
        raise ValueError("Expected exactly one system message")
    texts = plan["rule_texts_by_scenario"][scenario]
    original = texts["FORBID"]
    replacement = texts[condition]
    content = systems[0]["content"]
    if content.count(original) != 1:
        raise ValueError("Frozen FORBID rule not found exactly once")
    systems[0]["content"] = content.replace(original, replacement, 1)
    if condition == "FORBID" and edited != request:
        raise AssertionError("FORBID must leave the parsed request unchanged")
    return edited


def load_probe_weights(plan: dict, root: Path) -> list[dict]:
    loaded = []
    for model in plan["probe"]["models"]:
        path = root / model["weights"]
        raw = path.read_bytes()
        if digest(raw) != model["weights_sha256"]:
            raise ValueError(f"Frozen weight hash mismatch: {path}")
        with gzip.open(path, "rt") as handle:
            weights = json.load(handle)
        loaded.append({**model, "frozen_weights": weights})
    return loaded


def score_activation(layer_values: dict[int, object], models: list[dict]) -> tuple[float, list[float]]:
    import numpy as np

    standardized_logits = []
    for model in models:
        values = np.asarray(layer_values[int(model["layer"])], dtype=np.float64)
        weights = model["frozen_weights"]
        mean = np.asarray(weights["mean"], dtype=np.float64)
        scale = np.asarray(weights["scale"], dtype=np.float64)
        coef = np.asarray(weights["coef"], dtype=np.float64)
        if values.shape != mean.shape or mean.shape != scale.shape or scale.shape != coef.shape:
            raise ValueError("Activation and frozen probe shapes differ")
        raw_logit = float(np.dot((values - mean) / scale, coef) + weights["intercept"])
        standardized_logits.append((raw_logit - model["train_mean"]) / model["train_sd"])
    return float(np.mean(standardized_logits)), [float(value) for value in standardized_logits]


def pack_inputs(plan: dict, old_root: Path) -> list[dict]:
    packed = []
    for call in plan["calls"]:
        run_id, filename = call["episode"].split("/", 1)
        path = old_root / "runs" / run_id / "episodes" / filename
        raw = path.read_bytes()
        if digest(raw) != call["episode_sha256"]:
            raise ValueError(f"Episode hash mismatch: {call['episode']}")
        episode = json.loads(raw)
        record = episode["requests"][call["request_idx"]]
        request = record["request"]
        if digest(request) != call["request_sha256"]:
            raise ValueError(f"Request hash mismatch: {call['call_id']}")
        packed.append({"call": call, "request": request, "record": record})
    return packed
