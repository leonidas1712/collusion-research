#!/usr/bin/env python3
"""Project combined E08 benchmark and full-run spend from measured benchmark timing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark_run", type=Path)
    parser.add_argument("--plan", type=Path, default=Path("experiments/E08-policy-counterfactual/plan.json"))
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    summary = json.loads((args.benchmark_run / "gpu_summary.json").read_text())
    rate = plan["benchmark"]["projection_rate_usd_per_hour"]
    safety = plan["benchmark"]["projection_safety_multiplier"]
    benchmark_cost = summary["wall_seconds"] * rate / 3600
    estimates = plan["estimated_tokens"]
    all_tokens = estimates.get("all_three_conditions_using_original_counts", estimates.get("all_three_conditions"))
    benchmark_tokens = estimates.get("benchmark_three_conditions_using_original_counts", estimates.get("benchmark_three_conditions"))
    token_scale = all_tokens / benchmark_tokens
    nonload = max(0.0, summary["wall_seconds"] - summary["model_load_seconds"])
    projected_full_wall = summary["model_load_seconds"] + nonload * token_scale
    conservative_full_wall = safety * projected_full_wall
    full_cost = conservative_full_wall * rate / 3600
    combined = benchmark_cost + full_cost
    projection = {
        "benchmark_run": args.benchmark_run.name,
        "rate_usd_per_hour": rate,
        "safety_multiplier": safety,
        "benchmark_wall_seconds": summary["wall_seconds"],
        "benchmark_estimated_cost_usd": benchmark_cost,
        "token_scale": token_scale,
        "projected_full_wall_seconds_before_safety": projected_full_wall,
        "projected_full_wall_seconds_with_safety": conservative_full_wall,
        "projected_full_cost_usd": full_cost,
        "projected_combined_cost_usd": combined,
        "cap_usd": plan["budget"]["gpu_usd_max"],
        "may_launch_full": combined <= plan["budget"]["stop_if_projected_over_usd"],
    }
    (args.benchmark_run / "cost_projection.json").write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n")
    print(json.dumps(projection, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
