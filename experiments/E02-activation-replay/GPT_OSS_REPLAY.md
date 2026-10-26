# gpt-oss Harmony replay

This is an isolated E02 adapter. The Qwen replay implementation and Modal app remain unchanged. It reuses E02 decoder-layer discovery, teacher-forced likelihood scoring, run provenance, cache/output volumes, and the read-only download utility.

## Environment and model

Use Python 3.11, torch 2.14.1, transformers 5.20.2, accelerate 1.15.0, safetensors 0.8.0, numpy 2.4.6, huggingface-hub 2.3.0, openai-harmony 0.0.8, and Modal 1.6.2. The Modal image pins these model dependencies. The existing local E02 virtual environment supplies the CPU planning/testing packages; Modal is installed separately as a uv tool.

Model: `openai/gpt-oss-20b@6cee5e81ee83917806bbde320786a8fb61efebee`. Load with `Mxfp4Config(dequantize=True)`, bf16, eager attention, and a single A100-80GB. Dequantization expands the released MXFP4 values; it does not recover original unquantized weights. No remote model code is needed. The tested model is public and required no HF login.

## Plan locally

Supply final complete episode JSON files. Controls need not be named `episode-*.json`.

```bash
experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/gpt_oss_replay.py \
  /absolute/path/to/recruiting-0002.json \
  /absolute/path/to/recruiting-0003.json \
  /absolute/path/to/control-0001.json
```

The printed `PLAN` path contains exact prompt/reply IDs, reasoning positions, source episode/request hashes, source labels and provider counts. Rendering uses official Harmony, LOW effort from the saved request, the saved response date, raw tool schemas/argument JSON/results, and omitted prior reasoning. A second count-only rendering retains prior reasoning for comparison. No token is added to compensate for the observed constant minus-one count difference. Use the renderer IDs directly: decoding then HF re-encoding can promote literal Harmony-looking content to control tokens. This happened in the held test episode; all 76 original renderer prompts still match provider counts within one token.

Planning issues no model API calls. Official encoding assets may download once if they are not cached. The current selected-plan artifact is `runs/20261025-2014-e02-gpt-oss-plan-5f17/plan.json`: 76 requests from three episodes, all provider-count deltas −1.

## CPU wiring checks

```bash
experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/test_gpt_oss_replay.py
experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/gpt_oss_replay.py \
  --tiny-plan runs/20261025-2014-e02-gpt-oss-plan-5f17/plan.json
```

The tiny run uses random weights and one request; its NLL has no fidelity meaning. Tests verify causality, reasoning-position extraction against native hidden states, likelihood alignment and hook cleanup.

## Paid phases

Run only within an explicitly authorized budget. The following two commands are the completed small test's allocation, not authorization for another run. The watchdog bounds client wall time at USD0.00090/s and stops the identified app on success or failure. Include all previous phase ledgers in the total; the wrapper does not discover unrelated or previous spending automatically.

```bash
experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/gpt_oss_budget.py \
  --phase prefetch --phase-ceiling .5
experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/gpt_oss_budget.py \
  --phase replay --phase-ceiling 2.8 \
  --plan runs/20261025-2014-e02-gpt-oss-plan-5f17/plan.json
```

CPU prefetch reuses `modal_app.py::prefetch` and writes the existing ready marker in Volume `collusion-weights`. The GPU entry point is **`modal_gpt_oss.py`**, a separate app. GPU loading is offline from that volume; it never downloads weights. It processes at most 100 requests, each at most 16,384 total prompt+reply tokens, and times out at 25 minutes. The inner wall check is 20 minutes. Full replay requires an explicitly budgeted plan and shards; do not silently remove these guards.

The local entry point checks the source episode hashes before submission. The GPU rechecks prompt-token hashes. Every forward pass includes the saved response, with no generation. Hooks save block outputs before final normalization at the last prompt token and every returned analysis-body token. Reasoning positions are absolute zero-based input positions **after consuming** those tokens. Header/terminator tokens are excluded from reasoning activations. Only returned reasoning is available.

## Download and verify

Completed test output: `runs/20261025-1217-e02-gpt-oss-fidelity` on Volume `collusion-activations`. Remote timestamps use UTC. The local copy has the same name.

```bash
modal volume get collusion-activations \
  runs/20261025-1217-e02-gpt-oss-fidelity ./modal-results
```

For a reproducible recursive download into `runs/` with per-file hashes, use the existing `download_volume.py` with a Python environment containing Modal. Verification uses the E02 environment:

```bash
experiments/E02-activation-replay/.venv/bin/python \
  experiments/E02-activation-replay/verify_gpt_oss.py \
  --replay runs/20261025-1217-e02-gpt-oss-fidelity \
  --plan runs/20261025-2014-e02-gpt-oss-plan-5f17/plan.json \
  --clients runs/20261025-2011-e02-gpt-oss-modal-client \
            runs/20261025-2016-e02-gpt-oss-modal-client
```

`verify_gpt_oss.py` is the frozen 76-request acceptance check for this plumbing test, not a generic full-dataset verifier. It also refreshes read-only Modal billing. Each NPZ contains float32 `residual_last[24,2880]`, `residual_reasoning[24,n_reasoning,2880]`, input IDs, reasoning positions and layer indices. Index entries contain source identity and per-request likelihood; the immutable plan supplies the full source labels and split. Store these test activations separately and re-replay the eventual full set.

Fidelity is token-weighted full-reply NLL/top-5, plus reasoning-body and answer/tool-body components. Full-reply metrics include Harmony framing. The Qwen first-64-token diagnostic is not exactly the same measurement. Constant count agreement does not establish exact provider tokens, and dequantized bf16 arithmetic differs from native fp4 serving.

## Full-collection denominator (2026-10-25 decision)

The collection design is 50 recruiting plus 10 control planned attempts per scenario. Only API/incomplete failures may be replaced, within the collection cap; do not top up to a `valid_for_comparison` quota. Retain every attempt and its completion, exposure, validity and disclosure flags in the handoff accounting.

For gpt-oss, the primary step table uses complete, exposed episodes and completed target requests strictly after the read and before the first exact protected-value emission anywhere, including returned reasoning. Do not gate the primary table on `valid_for_comparison`. Preserve pre-ask steps as placebo rows, and use post-ask steps for the primary analysis. Preserve validity as metadata and report a gated sensitivity alongside the ungated primary fit once fitting proceeds.

The frozen Qwen cache did use the validity gate. Audit `runs/20261025-2138-e05-validity-gate-audit/report.md` finds 258 otherwise eligible steps excluded from 11 episodes: 17 steps from one gave-in episode and 241 from ten held episodes. Across complete exposed episodes, three gave-in and ten held episodes fail validity; two of those gave-in episodes have no strict-window step regardless of the gate. All 13 failed correct final task-summary fields, rather than completion or exposure. The spray scorer requires a correct summary and reporting its path; the deploy-token scorer does not impose that task-summary gate. Thus the two denominator rules are not equivalent for Qwen. Its existing results remain frozen; the discrepancy was escalated before any refit. No Qwen refit is authorized by this denominator note.

### Superseding decision (2026-10-25 21:47 SGT)

The approved common rule adds **ever wrote a correct summary** to completion and exposure. `gpt_oss_dataset.py` implements the episode flag and strict post-read/pre-first-emission step predicate. It retains `final_summary_correct` and `original_valid_for_comparison` as descriptive columns. The historical-write audit is `runs/20261025-2143-e05-ever-correct-summary-audit-a9bf`: 0/11 excluded Qwen recruiting episodes ever wrote correctly; gpt-oss rollout admits 46/50 under the common rule. This supersedes the earlier ungated-completion/exposure proposal above. Qwen outputs remain frozen, with no refit. See the dated Addendum 6 amendment for timing and rationale.

Decision #1129 (21:59 SGT) supersedes reasoning-inclusive censoring: use first public response content/tool-argument emission, as returned by `gpt_oss_dataset.request_boundaries`, for the primary step window. Preserve first reasoning mention and inclusive boundary descriptively. The 2157 audit found 54 steps lost under inclusive censoring, 53 from three held episodes. Reasoning-token probing is optional and must not delay the last-token pipeline.

## Full-collection provider gate (2026-10-25 22:36 SGT)

The full collection has 6,985 target requests from AkashML/DekaLLM; the original 76-request fidelity test used CoreWeave. The drop-all-reasoning renderer is not validated for these new providers. Offline audit `runs/20261025-2236-e02-gpt-oss-rendering-gate/report.md` reports full distributions, intra-turn comparisons and outcome-stratified matched-window coverage. Keeping current-turn reasoning improves AkashML count agreement substantially but does not fix DekaLLM. Production rendering remains unchanged pending the author gate; caching the Harmony encoder was independently checked to reproduce all 76 original token streams.

`plan_gpt_oss_full.py` verifies the canonical manifest, every source hash, completion/exposure, actual channel outcomes and both request index conventions. The source manifest's read index counts completed target requests, whereas emission indices count all target attempts. Rows retain both and preserve every attempt for capture. The current 2226 plan is an offline drop-all diagnostic, **not cleared for GPU execution**. The full watchdog refuses plans without an explicit `rendering_gate_approval` recorded after the author's decision.

`modal_gpt_oss_full.py` prepares sequential 100-request shards using one warm cached bf16 model. `gpt_oss_full_budget.py` carries all prior client costs in a shared USD20 ledger, keeps a USD0.50 overhead reserve, applies a conservative wall-cost watchdog, checks measured projections after shards, and stops the app on success or failure. Completed shard paths are checkpointed in `completed-shards.json`; no GPU work has run for this full collection yet. Qwen replay code is unchanged.

## Approved provider paths and paired gate (2026-10-25 22:49 SGT)

The author authorized the provider-stratified paired diagnostic and automatic full replay if AkashML retained good fidelity and DekaLLM showed no large loss. The verified report is `runs/20261025-2249-e02-gpt-oss-paired-fidelity-report/report.md`. All 100 forwards passed input-array/hash, shape, layer and finite-value checks. The diagnostic app is stopped; it billed USD0.10308139 at the snapshot, with conservative compute upper USD0.16683843 charged to the same USD20 full-replay budget.

The full collection uses **AkashML current-turn reasoning retention** and **DekaLLM drop-all prior reasoning**. AkashML answer/tool-body NLL improved from0.32259 to0.25561; DekaLLM drop-all was0.35960 with99.126% top-5. DekaLLM count mismatch is not solved; it is an approximate provider-format replay with a documented likelihood sanity check. Full replay retains every request. Provider, token gap and rendering mode remain per-row fields, with a secondary analysis excluding |gap|>1 requests. The earlier CoreWeave default renderer remains unchanged.

For AkashML, reasoning from earlier tool calls in the **same user/peer turn** is part of the prompt being replayed. It is dropped after the next user/peer message. Thus a mid-turn last-prompt-token feature can encode earlier reasoning from that turn; it is not a feature taken before the model has reasoned at all. This input-access distinction must be retained in monitor comparisons. Reasoning-position probe fitting is optional and does not delay primary last-token extraction.

## Full-run download and CPU checks

`download_gpt_oss_full.py` watches the completed-shard journal and reads committed outputs from the activation Volume. It writes local copies plus file hashes; it does not launch compute or modify remote files. Pass the same plan and client paths used for the GPU run:

```bash
python experiments/E02-activation-replay/download_gpt_oss_full.py \
  --plan runs/20261025-2251-e02-gpt-oss-full-plan/plan.json \
  --client runs/20261025-2253-e02-gpt-oss-full-client
```

Use a Python environment with Modal installed for downloading. The E05 environment is sufficient for verification and the exposure control:

```bash
experiments/E05-probes/.venv/bin/python experiments/E05-probes/gpt_oss_replay_data.py \
  --plan runs/20261025-2251-e02-gpt-oss-full-plan/plan.json \
  --download runs/20261025-2255-e02-gpt-oss-full-download --watch
experiments/E05-probes/.venv/bin/python experiments/E05-probes/gpt_oss_positive_control.py DATA_RUN_ID
```

The cache builder verifies every prompt/reply token array, prompt/input hash, request metadata field, layer ID, activation shape and finite value. It rechecks canonical episode hashes and requires all shards before marking the dataset finished. The cache retains all requests; eligibility is metadata, never an extraction filter. Its primary feature tensor is float32 `[requests,24,2880]`. Reasoning arrays stay in the source NPZs. The exposure gate uses a family-disjoint 30% holdout with seed42 and requires layer12 AUROC >=0.95 before outcome fits.

The declared 17 candidate layers are `[0,1,3,4,6,7,9,10,12,13,15,16,18,19,20,22,23]`, with fixed12 secondary. This is a separate 24-layer path; Qwen caches, candidates and results are unchanged.

`gpt_oss_kind_join.py` produces a separate metadata join from saved disclosure judgments, checking source episode hashes. These describe the first public emission, often a file write before a channel publication. They do not change the primary channel outcome or eligibility. Null judgment labels remain null.

## Verified full collection replay (26 October)

[Completion report](../../runs/20261026-0138-e02-gpt-oss-full-completion/report.md): all 6,985 requests from 360 episodes passed input-token, hash, shape and finite-value checks. The cache is `runs/20261025-2305-e05-gpt-oss-full-data`, with last-prompt features `[6985,24,2880]` and 83,747 reasoning positions retained in the source artifacts. The A100 app is stopped. Client wall time was 164.30 minutes; billed snapshot USD8.002761 and conservative shared total USD9.539242, including the paired diagnostic, reserve and two worker preemptions, were below the USD20 cap.

AkashML answer/tool-body NLL was 0.26901 with top-5 fraction 0.99315; DekaLLM was 0.31983 / 0.99416. Prompt counts were within one token for 6,598/6,672 AkashML and 18/313 DekaLLM requests. The Deka approximation remains flagged. The family-held-out exposure check passed: layer12 AUROC1.000 on 2,100 test rows; the minimum over all24 layers was0.99947. See `runs/20261026-0137-e05-gpt-oss-positive-control`.

The [window audit](../../runs/20261026-0056-e05-gpt-oss-window-audit/report.md) separates collection outcomes from prediction opportunities: 96/128 channel-positive episodes have eligible post-ask requests; 31 emit in the first request receiving the ask and one before the detected ask. These 32 have no post-ask prediction window. Their collection outcomes remain recorded.
