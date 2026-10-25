# Main dataset replay plan — 2026-10-24

**Completed:** see [main replay results](MAIN_REPLAY_RESULTS.md). The estimates below are retained as the approval record.

**Proposal: 143 complete episodes, 3,034 target requests, 6,883,492 prompt tokens. Replay Qwen3-32B bf16 independently at each request’s true last prompt token on one A100-80GB. With default first-64-reply-token fidelity, estimated time: 45–117 minutes; compute cost: USD 2.20–6.24. Propose a USD 9 cap, subject to approval. No GPU, Modal, or model API calls were made for this plan.**

This supersedes the first-request-per-round proposal: every target request is replayed, not only the first in each round. Pinned model revision: 9216db5781bf21249d130ec9da846c4624c16137.

## Frozen scope

The [step manifest](../../runs/20261024-1803-e02-step-prefix-plan/steps.jsonl) and [summary](../../runs/20261024-1803-e02-step-prefix-plan/summary.json) are the approval target. The [30 source run IDs](../../runs/20261024-1753-e02-main-replay-plan/run_ids.json) cover overnight 0504/0650, scale-up 1631/1633 and tactics 1653–1745, including recruiting, control and alone. Only final, complete, non-fake Qwen3-32B deploy-token consequence_logged episodes qualify. Seven partial files are excluded.

Retain every target API request **through and including the request that produces the first forbidden action**, then exclude subsequent requests. Keep every request of nonviolating episodes. There are 38 action-producing rows, flagged acts_this_step. The selected input has not yet observed its own output.

The boundary includes target channel publication and successful writing of the full protected token to another file. Two episodes need the file-write boundary: scale-up recruiting episode 30 writes at round 14 before channel disclosure at 15; T7 recruiting episode 1 writes at round 8 without a channel leak. A channel-only cutoff would be wrong.

Rows record episode/request/prompt/token hashes, source, round, step, attempt, condition, family, tactic, action index, eventual violation, acts_this_step, before_first_action, first_request_in_turn, request errors, comparison validity and request-specific token exposure. Labels remain available through the [hashed episode snapshot](../../runs/20261024-1753-e02-main-replay-plan/episodes.json).

## Counts

| Cohort | Condition | Episodes | Requests | Prompt tokens |
| --- | --- | ---: | ---: | ---: |
| overnight | alone | 4 | 12 | 7,142 |
| overnight | recruiting | 13 | 237 | 562,157 |
| scaleup | alone | 6 | 18 | 10,697 |
| scaleup | control | 15 | 357 | 531,853 |
| scaleup | recruiting | 40 | 932 | 2,398,849 |
| tactics | control | 13 | 320 | 488,801 |
| tactics | recruiting | 52 | 1,158 | 2,883,993 |
| **Total** | | **143** | **3,034** | **6,883,492** |

There are 38 violating episodes contributing 500 rows (including 38 acts-this-step rows), and 105 nonviolating episodes contributing 2,534. The source corpus has 3,147 target requests before selection. All 143 episodes contribute.

- 2,225 selected rows are first requests in their target turn.
- 545 selected inputs do not yet contain the protected token.
- Twelve never-read recruiting episodes contribute 289 rows flagged invalid for the exposed-resistance comparison; they remain in the inventory.
- Six identical retry inputs remain explicit. Deduplication could save six forwards / 8,008 tokens; the estimate does not require it.
- Prompt lengths range from 510 to 7,024 tokens. The benchmark maximum was 6,141, so its measured 62.16 GiB CUDA peak does not guarantee memory use at the new maximum. Do not truncate.

Later steps can contain a decision already verbalised in earlier target output. This tokenizer plan does not infer that semantic flag; analysis must annotate it and report the subset without visible decisions. Rows are correlated within episodes and families.

## Prefix audit

Across all 143 episodes, **2,998 of 3,004 adjacent request pairs fail exact prefix equality**. The other six are identical retries; zero are strict extensions. All 2,169 across-round pairs fail.

The thinking-disabled Qwen generation prompt ends with a four-token empty-thinking block. It disappears when the assistant reply becomes history. Overnight-alone episode 1 request 0 has 510 tokens, request 1 has 606, and they diverge at token 506. A final-transcript forward therefore cannot recover the earlier true last-prompt-token states.

Removing those four tokens restores 3,003 of 3,004 adjacent prefixes and covers 3,033 of 3,034 selected positions in final transcripts. One extra whitespace/tokenization mismatch occurs in T5 run 1735, episode 1, requests 2→3: the old assistant-header newline becomes three newlines in history, diverging five tokens from the old end. See [examples](../../runs/20261024-1803-e02-step-prefix-plan/prefix_examples.json) and [all pairs](../../runs/20261024-1803-e02-step-prefix-plan/prefix_pairs.jsonl).

Final transcripts total only 494,518 tokens, but that is **not a valid cost basis for the requested exact readout**. A suffix-trimmed readout changes the measurement position. It is optional future work requiring an activation/fidelity comparison on a few steps and handling of the whitespace exception. No such model comparison was run here. Exact cache branching is also untested and outside this proposal.

## Fidelity verification added

The runner now verifies the exact request manifest before loading weights, captures the true prompt endpoint in a single prompt-plus-reply forward, and scores up to the first 64 saved reply tokens by default. The [offline preflight](../../runs/20261024-1814-e02-fidelity-plan/summary.json) finds **144,949 extra reply tokens (2.106%)**, giving **7,028,441 combined tokens**. All 3,028 requests with saved replies are scoreable; six failed API attempts have no reply and remain explicitly unscored. One reply requires separately tokenizing its suffix to preserve the original prompt IDs across a BPE boundary; this adapter is flagged.

Token-linear added decoder time is 54.5 seconds, about USD 0.05 at the saved capped rate. For head projection and other overhead, the old two-pass benchmark leaves 12.44 seconds after subtracting two measured prompt decoder passes. Applying that residual per call to 3,034 calls adds a conservative **12.6-minute allowance**. It is an empirical planning allowance, not a measured bound for the new implementation. The resulting estimate is **44.9–117.0 minutes / USD 2.20–6.24**, up to about **USD 0.72 more** than the activation-only estimate. Keep the proposed USD 9 cap; it now provides about 44% margin above the upper estimate, rather than 50%.

The 160-minute A100 function, manifest selection and activations-only override are implemented. The prepared command and local positive-control command are in the [README](README.md#main-dataset-verified-manifest-replay). The exposure probe uses a fixed last layer, train-only scaling and an episode-held-out split; its near-perfect AUROC target is a diagnostic, not proof of exact provider replay. This exact USD 9-capped run was then approved; client 20261024-1818-e02-main-modal-client submitted it. Results are pending.

## Activation-only reference estimate

The [saved benchmark](MODAL_BENCHMARK.md) measured 2,661.49 prompt tokens/s for activation capture and 101.4167 seconds for 50 long requests. The lower estimate divides new tokens by throughput; the upper applies the measured per-call time to all 3,034 requests. Both add 54 seconds for cached loading/startup.

Result: **44.0–103.5 minutes and USD 2.16–5.52**, using saved benchmark resource rates of USD 2.9452/hour (A100, four CPUs, 32 GiB host RAM) to USD 3.2012/hour (64 GiB host-memory cap). These are planning extrapolations, not confidence bounds; verify rates before a future launch.

Fifty percent headroom on the conservative compute estimate gives USD 8.26; round the requested allowance to **USD 9**. These original estimates exclude fidelity. The revised proposal above includes bounded per-step fidelity, all 64 layers, cached weights and no GPU download. Full unbounded reply scoring is not proposed.

The runner now implements hash-checked manifest selection, an activation-only Modal option and an A100-specific full-run function with a budget-derived timeout (at most 160 minutes at the saved capped rate leaves a small margin below USD 9). The existing 20-minute benchmark entry point cannot run this plan. Monitor progress and stop if the allowance is threatened. A generic max-requests limit is not equivalent to the manifest. Changed sources require hash verification or replanning. This document does not authorise GPU work.

## Layers and storage

Saved vectors are float32, despite bf16 computation, with width 5,120.

| Layers | Fixed indices | Raw vectors | Reduction |
| --- | --- | ---: | ---: |
| **64** | 0–63 | **3.977 GB / 3.704 GiB** | — |
| 16 | 3,7,11,…,63 | 0.994 GB | 75% |
| 8 | 7,15,23,…,63 | 0.497 GB | 87.5% |

Input IDs add about 55.1 MB uncompressed, plus text/index/provenance. The benchmark NPZ vectors compressed to about 47% of raw size; that ratio is not guaranteed. At the saved USD 0.09/GiB-month rate, uncompressed all-layer vectors cost about USD 0.33/month.

**Recommend all 64 layers.** Storage is modest and permits validation-only layer selection without another replay. Saving fewer layers reduces storage and some hook/transfer overhead, but every model layer still executes, so compute does not fall proportionally. Do not choose layers using test outcomes.

## Local reproduction

Run check_prefixes.py with positional input 20261024-1753-e02-main-replay-plan using the E02 virtualenv Python. It uses only the cached pinned tokenizer, checks episode hashes and records all comparisons. Run unittest discovery for test_plan_main.py and test_check_prefixes.py in the E02 directory. Tests cover inclusive action selection, generation-suffix divergence, earlier round selection, file-write boundaries and source scope. Earlier first-request-only artifacts remain immutable but are superseded.
