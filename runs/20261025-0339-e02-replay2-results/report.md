# Replay2 results

All **6,026 requests** passed manifest and artifact verification: 6,003 actual target calls from 268 complete episodes, plus 23 shared pre-peer branching states. Both Modal apps are stopped. Model: Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137, bf16 A10080; all 64 decoder outputs at the true last prompt token. The replay used independent forward passes, with cached weights and no generation.

- Prompt tokens: 13,344,820; scored reply tokens: 276,868 (up to 64 per actual reply).
- Token-weighted reply NLL: **0.248778**; top-five fraction: **0.997923**. The 23 shared states have no actual next reply and correctly have missing-response diagnostics.
- Combined client wall time: 113.19 minutes, including benchmark/main startup and cleanup. Decoder time: 78.36 minutes; per-request processing time: 101.22 minutes.
- Throughput: 2,838 prompt tokens/s of decoder time; 2,897 total input tokens/s of decoder time; 2,197 prompt tokens/s of request-processing time; 1,965 prompt tokens/s of client wall time.
- Billed app total at this snapshot: **USD 5.5137** (billing can lag; see billing.json). Conservative benchmark + main compute upper bound plus USD0.50 for transfer/storage and other overhead: **USD 6.61**, below the approved USD12 cap.

Verification runs: `20261025-0126-e02-main-replay-validation`, `20261025-0336-e02-main-replay-validation`. Combined data: `20261025-0337-e05-replay2-data`. The download was deliberately resumed with 32 parallel reads to reduce small-file latency, preserving atomic completed files; this was a transport restart, not a GPU replay or failed integrity check.

HF prompt and input-token hashes match the frozen manifest. Equal provider/HF token counts and low reply NLL support fidelity but do not reveal or prove equality with the provider's private template, exact tokens or quantization. The extraction gate and outcome analyses are separate E05 runs.
