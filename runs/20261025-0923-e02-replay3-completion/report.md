# Replay3 results

Replayed 3,112 target requests from 129 complete balanced-batch episodes through pinned Qwen3-32B bf16 on A100-80GB, saving all 64 decoder layers at the last prompt token. Both Modal apps are stopped.

- Integrity: every request, prompt, token and episode hash matched its frozen manifest; all arrays were finite and correctly shaped.
- Reply fidelity: token-weighted NLL 0.226818; top-five fraction 0.998183 over 152,965 scored tokens.
- Layer-32 exposure gate: family-held-out AUROC 1.000000, above the fixed 0.95 gate. No outcome or near-term probes were fitted or evaluated.
- New data: 2,220 eligible steps from 108 episodes. Cache: `runs/20261025-1026-e05-replay3-data`.
- Combined data: 9,138 rows, 6,404 eligible steps. Cache: `runs/20261025-1026-e05-replay3-data-1d95`. The old 6,026-row prefix is unchanged in metadata, order and features; new rows are appended and reindexed.
- Cost snapshot: USD 2.9434; conservative compute bound plus USD0.50 overhead: USD 3.78, below the USD7 cap. Billing can lag.

Plan: `runs/20261025-0838-e02-replay3-plan`. Benchmark validation: `runs/20261025-0853-e02-main-replay-validation`. Main validation: `runs/20261025-1026-e02-main-replay-validation`. Exposure gate: `runs/20261025-1026-e05-replay3-positive-control`. Prefix verification: `runs/20261025-1027-e05-replay3-prefix-validation`.

These are HF reconstructions, not proof of equality with the provider's private tokenization, template, kernels or quantization. Outcome analysis of the confirmation set is reserved for the frozen confirmatory plan.
