#!/usr/bin/env bash
# Pilot grid: 6 scenarios x 4 cells on one target model (peer: deepseek-v4-flash).
# Usage: pilot_grid.sh MODEL PROVIDER QUANT TAG
#   e.g. pilot_grid.sh qwen/qwen3-32b DeepInfra fp8 qwen32
# Cells: rule+ask x5, rule+control x3, alone x2, no-rule+ask x3, matched families starting at 201.
# Runs cells one after another (provider rate limits); each cell is its own run folder.
set -u
MODEL=$1 PROVIDER=$2 QUANT=$3 TAG=$4
cd "$(dirname "$0")/../.."
H=experiments/E01-behaviour-pilot/harness.py

run() {  # scenario episodes rounds
  uv run python $H --scenario "$1" --episodes "$2" --rounds "$3" --family-start 201 --parallelism 3 \
    --target-model "$MODEL" --target-provider "$PROVIDER" --target-quantization "$QUANT" \
    --recruiter-model deepseek/deepseek-v4-flash 2>&1 | grep -E '^\[run\]|"episode_id"' | cut -c1-140 | sed "s/^/[$TAG] /"
}

for fam in poster-approval minimum-price release-date front-door-sign disable-failing-test; do
  run "${fam}_explicit_recruiting" 5 20
  run "${fam}_explicit_control" 3 20
  run "${fam}_explicit_alone" 2 20
  run "${fam}_none_recruiting" 3 20
done
run deploy-token_explicit_related_recruiting_required-access 5 20
run deploy-token_explicit_related_control_required-access 3 20
run deploy-token_explicit_alone_required-access 2 20
run deploy-token_none_related_recruiting_required-access 3 20
echo "[$TAG] done"
