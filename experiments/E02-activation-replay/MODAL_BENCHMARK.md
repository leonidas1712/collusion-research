# Approved Modal benchmark — 2026-10-24

**50/50 deploy-token requests replayed and scored on one NVIDIA A100 80GB PCIe, Qwen3-32B bf16, with all weights loaded offline from the cache Volume.** All apps are stopped. The CPU prefetch and this single GPU benchmark ran under a USD 2 combined cap. No full replay or FP8 run was performed.

| Measurement | Observed result |
| --- | ---: |
| Reported app-attributed cost, including failed CPU startups and image build | **USD 0.245373** |
| Successful CPU prefetch client wall time | 306.50 s (5m 06s); remote run 288 s |
| GPU client wall time | 269.16 s (4m 29s); remote replay 244 s |
| Model load time, from cached files | 23.73 s |
| Prompt-only activation capture, summed over requests | 101.42 s |
| Activation + fidelity + per-request artifact handling | 215.28 s |
| Prompt tokens | 269,919 |
| Activation-only throughput | **2,661.49 prompt tokens/s** |
| Effective throughput including fidelity | **1,253.82 prompt tokens/s** |
| Reply tokens scored | 3,114, across all 50 requests |
| Token-weighted mean NLL | **0.187151 nats/token** |
| Token-weighted mean log probability | −0.187151 nats/token |
| Token-weighted top-5 fraction | **0.998394 (99.8394%)** |
| Median per-request NLL | 0.165558 nats/token |
| Peak allocated CUDA memory | 66,742,587,904 bytes (~62.16 GiB) |
| Device map | `cuda:0`, no CPU/disk offload |
| HF/provider prompt token-count ratio | median 1.0; range 0.995351–1.0 |

Throughput uses prompt tokens as the numerator. The fidelity-inclusive figure does **not** count the second pass's repeated prompt tokens again. Client wall time includes startup/transfer/return handling and is not the same denominator as either throughput number. The CPU checkpoint download completed in approximately 287 seconds; no checkpoint download ran on the GPU.

Billing is the final refresh in [20261024-1558-e02-modal-billing-final/billing.json](../../runs/20261024-1558-e02-modal-billing-final/billing.json), unchanged from the initial metrics report. Modal billing can lag. The figure includes all four app IDs for this task, including both failed CPU attempts, and is before credits. Persistent Volume storage may be billed separately and continues while the requested cache is retained; it is not a new compute run. The observed execution leaves ample margin under USD 2 (a conservative compute allowance for all observed wall time is below USD 0.30). The roughly 61 GiB weight cache remains in `collusion-weights` for reuse; at USD 0.09/GiB-month, a full month would be about USD 5.5 before any applicable allowance. No further compute is authorized by this benchmark.

## Scope and evidence

The [frozen input plan](../../runs/20261024-1542-e02-deploy-benchmark-plan/selection.json) selects the 50 longest prompts among 727 eligible Qwen3-32B calls from existing, final, complete deploy-token episodes. Lengths are 4,789–6,141 tokens. The selected calls come from **six source episodes**, so this is a correlated stress sample, not 50 independent behavioral observations or a representative workload estimate.

- Model: `Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137`, bf16.
- Replay output: [20261024-0751-e02-activation-replay](../../runs/20261024-0751-e02-activation-replay/summary.json), persisted on `collusion-activations` and downloaded locally. Remote IDs use UTC; local client IDs use SGT.
- Metrics: [20261024-1556-e02-modal-benchmark-report/results.json](../../runs/20261024-1556-e02-modal-benchmark-report/results.json).
- Validation: [20261024-1556-e02-modal-benchmark-validation/meta.json](../../runs/20261024-1556-e02-modal-benchmark-validation/meta.json). All 50 source episode/request hashes match; selection exactly matches the plan; local tokenizer prompt IDs match saved arrays; every residual tensor is finite and shaped `[64,5120]`; all layer indices and reply-token counts match.
- Successful prefetch: [20261024-0745-e02-prefetch-3d82](../../runs/20261024-0745-e02-prefetch-3d82/meta.json), client `20261024-1545-e02-modal-prefetch-client-c064`, app `ap-k1SVCyNKcHLqp20FUpHSEb`.
- GPU client: `20261024-1551-e02-modal-benchmark-client`, app `ap-XQXRCWjz0CnOafhGp75ddU`.

The original replay summary's `episodes=47` counts eligible input episodes scanned, not selected episodes. Validation establishes that only six contributed requests. Future summaries now distinguish selected `episodes` from `episodes_available`; the recorded result is unchanged.

These fidelity scores are for the HF reconstruction of saved replies, including template terminators and tool-call serialization. Much of a tool reply is predictable syntax. The provider used fp8, while this replay used bf16; high agreement and nearly equal prompt counts do not establish exact provider tokens, exact activations or identical checkpoints. No new responses were generated.

## Failures found and fixed

1. Initial CPU startup assumed the module lived in the repository layout; Modal imported it from `/root`. App `ap-37VuTXFyRv9SgmjifTC1ZK` was stopped before any weight download. Local/remote source paths are now separated with `modal.is_local()`.
2. The next CPU attempt failed because `start_run` printed an external output path with an unconditional repository-relative conversion. App `ap-Ma5vy1jigQBem1w2n6omRo` ended before downloading. The shared helper now accepts external output directories; a local temporary-root check passed. Its prematurely created remote metadata says `finished` because the error occurred during startup and was caught by Modal; the client failure log, not that status, determines this attempt's outcome.
3. All GPU work completed, but the wrapper failed afterward while formatting the resolved Volume path relative to its symlink mount. The `finally` block committed the outputs, and all artifacts were recovered and validated. The client therefore records exit 1 while the replay itself records `finished`. Path conversion now resolves the mount before taking a relative path; a local symlink check passed. No second GPU run was needed or performed to recheck this return-only fix.
4. Modal 1.6.2's recursive CLI download failed when its destination directory did not yet exist. Creating the destination first worked; README commands now do that.

The benchmark proves full-weight CUDA forward execution, activation capture, reply scoring, offline cache loading and persistent artifact recovery. It does not yet prove that the corrected wrapper exits cleanly remotely, nor FP8 operation.

Download again, if needed:

```bash
mkdir -p ./modal-results
modal volume get collusion-activations runs/20261024-0751-e02-activation-replay ./modal-results
```
