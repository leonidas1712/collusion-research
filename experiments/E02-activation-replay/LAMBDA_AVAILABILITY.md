# Lambda capacity check — 2026-10-24 03:01 SGT

**Live inventory is blocked, not empty.** All four requested GET endpoints returned HTTP 403. A diagnostic read identified Cloudflare error 1010, `browser_signature_banned`, with `retryable=false`. No further requests were made after identifying that block. API-key validity cannot be inferred from this edge-layer response.

The key was loaded from `.env` in code and sent only as a Bearer header to `https://cloud.lambda.ai/api/v1`. No credential was printed or stored in the report. No instance, filesystem or key was created, changed or deleted; no GPU was rented.

## Capacity and account state

| Requested endpoint | Result | What remains unknown |
| --- | --- | --- |
| `GET instance-types` | HTTP 403 | Available types, capacity regions, account-specific prices |
| `GET instances` | HTTP 403 | Whether any instance is running |
| `GET file-systems` | HTTP 403 | Whether persistent storage exists and in which regions |
| `GET ssh-keys` | HTTP 403 | SSH key names |

Recorded check: [20261024-0301-e02-lambda-inventory](../../runs/20261024-0301-e02-lambda-inventory/inventory.json). The follow-up diagnostic classified the 403 as Cloudflare 1010; the initial run records HTTP status only. The read-only helper is [lambda_inventory.py](lambda_inventory.py), now stopping immediately on an explicitly non-retryable response. Do not rerun until access is resolved.

The current [API docs](https://docs.lambda.ai/api/cloud) confirm the base URL and Bearer authentication. `/file-systems` remains documented as a deprecated path; `/filesystems` is the current path. The [console documentation](https://docs.lambda.ai/public-cloud/console/) describes the account views Leo can inspect while API access is blocked. No console inspection was performed here.

## Public list prices, not confirmed available capacity

All regions and live availability below are **unknown**. Prices are USD per whole instance-hour, excluding tax, from the [current Lambda pricing page](https://lambda.ai/pricing), checked 2026-10-24. They are not successful authenticated API quotes.

| Type | VRAM | Public USD/hour | Capacity regions | Suitability |
| --- | --- | ---: | --- | --- |
| 1× A6000 | 48 GB | 1.09 | Unknown | Granite 8B; insufficient for either full bf16 Qwen target |
| 1× A100 PCIe or SXM | 40 GB | 1.99 | Unknown | Granite; insufficient for full bf16 Qwen targets |
| 1× A100 | 80 GB | Not listed in current 1× table | Unknown | Memory candidate if API confirms a single-card offering; do not reuse 8× per-GPU price |
| 1× H100 PCIe | 80 GB | 3.29 | Unknown | Preferred initial Qwen replay candidate |
| 1× H100 SXM | 80 GB | 4.29 | Unknown | Alternative; measure whether speed offsets price |
| 2× H100 SXM | 2×80 GB | 8.38 total (2×4.19) | Unknown | Memory fallback; E02 layer dispatch is not automatic 2× throughput |
| 1× GH200 | 96 GB | 2.29 | Unknown | ARM CPU; avoid for this unvalidated software environment |

GH200's ARM architecture is documented in Lambda's [on-demand overview](https://docs.lambda.ai/public-cloud/on-demand/). The pricing page lists A100 80GB in the 8× table only; this does not establish a 1× offering.

## E02 recommendation

Once capacity is verified and Leo approves a launch, start with **one H100 80GB**, preferably the PCIe option at the listed USD 3.29/hour. Qwen3-32B weights are about 65.5 GB decimal (61.0 GiB); Qwen3-30B-A3B weights are about 61.1 GB (56.9 GiB). All MoE experts need memory. Remaining VRAM must accommodate attention workspaces, intermediate activations and framework allocations. E02 uses one full-prompt forward at a time, no KV cache or generation, and saves only last-token layer outputs. Long prompts can still exceed memory; a pilot must verify the longest prompts and confirm that `device_map=auto` has not silently offloaded layers to CPU/disk.

An available 1× A100 80GB would be a viable memory alternative, but its offering, price and relative runtime were not verified. Use an A6000 for Granite-only work. Use 2× H100 only if single-card memory fails and the extra cost is approved; current layer-wise dispatch does not imply parallel throughput. Choose persistent storage in the eventual compute region after checking existing storage. Nothing about storage presence was established today.

E03's Qwen API episodes used fp8 serving. Replaying them with bf16 weights is a precision mismatch, even with a compatible template; capacity does not resolve the fidelity question.

## Rough runtime and cost planning

These are **assumed timing ranges, not GPU benchmarks or quotes**. For 300 episodes × 20 actual target API calls = 6,000 forwards, replay hours equal `6000 × mean_seconds_per_call / 3600`. Each forward recomputes the complete growing prompt; saving only the last token does not avoid that work. If “20” means dialogue rounds rather than actual target requests, tool steps/retries make the workload larger.

Assume typical full prompts of 2k–8k tokens with some longer tails. Existing CPU wiring inputs reached 17k tokens. The unbatched HF implementation and per-layer CPU copies can materially affect throughput. Budget ranges deliberately include uncertainty:

| Workload | Assumed mean seconds/call | Forward GPU-hours | Including 0.5–1.5 hours setup/load/checks | Compute cost at public list rate |
| --- | ---: | ---: | ---: | ---: |
| Qwen3-32B, 1× H100 PCIe | 2–8 | 3.3–13.3 | 3.8–14.8 | USD 12.5–48.7 |
| Qwen3-A3B, 1× H100 PCIe | 1–6 | 1.7–10 | 2.2–11.5 | USD 7.2–37.8 |
| Granite 8B, 1× A6000 | 1–6 | 1.7–10 | 2.2–11.5 | USD 2.4–12.5 |

MoE active parameters reduce arithmetic but do not ensure the HF expert kernels realize proportional speedups. Long contexts, CPU offload or poor kernels can exceed these ranges. Storage, tax and any idle rental time are additional. On two GPUs, GPU-hours are twice instance wall-hours; no two-GPU speedup estimate is established.

Before authorizing a full batch, benchmark 50–100 representative saved requests including the longest contexts on an approved machine; record peak VRAM, device map, prompt lengths and per-forward timings. Extrapolate by prompt-length bins across the actual request manifest, adding startup and I/O time. For Qwen32, 6,000 × 64 layers × 5,120 width × 4 bytes is about 7.9 GB of uncompressed last-token vectors, plus token IDs, prompts and indexes. Weight cache and retained source runs require additional storage.

**Next dependency:** Leo or Lambda support must resolve API access, or supply the read-only inventory from the console. This check cannot name a currently available region or assert that the account is empty.
