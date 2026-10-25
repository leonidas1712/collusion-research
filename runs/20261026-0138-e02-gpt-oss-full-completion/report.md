# Full gpt-oss replay completion

Replayed and verified all 6,985 saved target requests from the 360-episode frozen collection. The A100 app is stopped. No request was removed for prompt-token mismatch, missing exposure, pre-ask timing or intermediate tool position. Eligibility is applied only in the step table.

Cache: `runs/20261025-2305-e05-gpt-oss-full-data`. Per-shard activation paths: `runs/20261025-2251-e02-gpt-oss-full-plan/completed-shards.json`. Local download inventory and file hashes: `runs/20261025-2255-e02-gpt-oss-full-download`.

Each NPZ contains last-prompt residuals [24,2880] and returned reasoning-body residuals [24,n_reasoning,2880], plus exact input IDs, reasoning positions and layer IDs. All 6,985 input-token arrays, hashes, shapes and finite values passed independent CPU checks. The full run saved 83,747 reasoning-token positions. The E05 feature tensor contains only last-prompt vectors, with shape [6985,24,2880].

| Provider | Segment | Tokens | Mean NLL | Top-5 fraction |
|---|---|---:|---:|---:|
| AkashML | all | 383371 | 0.41432 | 0.98961 |
| AkashML | reasoning | 76980 | 0.69122 | 0.97706 |
| AkashML | answer | 231353 | 0.26901 | 0.99315 |
| DekaLLM | all | 21039 | 0.47272 | 0.98778 |
| DekaLLM | reasoning | 6767 | 0.68293 | 0.97370 |
| DekaLLM | answer | 10613 | 0.31983 | 0.99416 |

Metrics are token-weighted over all returned reply tokens. The all segment includes Harmony framing; reasoning and answer/tool-body segments are reported separately. Qwen’s earlier NLL~0.23/top-5~99.8% used the first64 reply tokens, so the measurements are not exactly equivalent.

| Provider | Requests | Exact prompt count | Within 1 token | Median absolute gap |
|---|---:|---:|---:|---:|
| AkashML | 6672 | 5661 | 6598 | 0.0 |
| DekaLLM | 313 | 1 | 18 | 21.0 |

AkashML uses the verified current-turn reasoning-retention renderer. DekaLLM uses drop-all prior reasoning; its provider prompt format remains approximate. The primary analysis retains all eligible requests and the saved prompt_token_match_within1 flag supports the predeclared mismatch sensitivity. Count agreement and likelihood agreement do not prove exact provider tokens. Served quantization fields are null. Replay expands the released MXFP4 checkpoint into bf16, with transformers5.20.2 and torch2.14.1.

A mid-turn AkashML prompt contains earlier reasoning from that tool-use turn, before the next reply. This differs from a monitor without private-reasoning access and from a feature taken before all reasoning in the turn. Reasoning-position probing remains optional; it is not used in the primary last-prompt feature.

## Time and cost

Completed shards processed 11,128,349 prompt+reply tokens in 158.51 minutes (1170.1 input tokens/s, including capture and artifact writes). Client wall time was 164.30 minutes, equivalent to 1128.8 unique input tokens/s including reloads, retries and other overhead. The full app billing snapshot is USD8.002761; billing can lag. The conservative shared total, including the preceding paired diagnostic and USD0.50 overhead reserve, is USD9.539242, below the USD20 cap. The watchdog carried earlier client costs forward and checked the projection after every shard. The GPU loaded cached weights and did not download a checkpoint. Modal automatically retried 2 worker preemptions within the same app. The interrupted attempts logged 45 completed requests before preemption, plus any unlogged in-flight work. Only successful completed shards enter the dataset; all app wall time and billed resources remain in cost accounting. Details are in preemptions.json.

## Data and analysis checks

Episode eligibility requires complete execution, exposure and a successfully written correct summary at least once. Steps are strictly after the read and before first public emission; returned private reasoning does not censor them. Channel publication remains the primary label. Pre-ask and post-ask rows are separate, and every raw capture is retained. The cache report records step and episode denominators, including the within-one-token sensitivity.

The dataset builder deliberately leaves kind null. Saved first-public-emission judgments are available separately at runs/20261025-2310-e05-gpt-oss-disclosure-kind-join and join by episode plus SHA256. They describe the first public emission, often a file write, not necessarily the later channel post. They do not alter primary labels or eligibility. Any earlier cache-report wording that labels were unavailable is superseded by this saved metadata join.

Outcome fitting is gated on a separate family-held-out token-exposure control at layer12 (AUROC>=0.95). Candidate layers were declared before fitting: [0,1,3,4,6,7,9,10,12,13,15,16,18,19,20,22,23]; fixed12 is secondary. This report contains no outcome-probe result.
