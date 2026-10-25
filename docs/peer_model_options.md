# Stronger peer model options

Written 2026-10-25. Desk research only: public OpenRouter model and endpoint listings, the Artificial Analysis leaderboard, vendor and third-party benchmark write-ups, and our own earlier recruiter smoke test (`experiments/E01-behaviour-pilot/smoke/recruiters_summary.json` and `recruiters_raw/`). No paid calls were made for this note.

## What this is for

In our episodes a **peer** agent tries, over about 20 rounds, to persuade a **target** agent to break its operator's rule (share a secret). The peer posts through a `send_message` tool, so it needs reliable **native tool calling** on OpenRouter. Today the peer is `deepseek/deepseek-v4-flash` at temperature 0.7 with reasoning turned off (`reasoning: {enabled: false}`).

For a higher-pressure condition we want a stronger peer. Requirements:

- reliable native tool calling on OpenRouter;
- stays in role as a persuasive teammate (an earlier peer, `openai/gpt-6-luna`, broke role: after one ask it told the target not to share and to rotate the token);
- affordable for about 50–100 episodes of about 20 rounds;
- not an Anthropic/Claude model (excluded from experiments by design), not a DeepSeek Flash variant, not a decision model such as Jev.

`deepseek/deepseek-v4-pro` is already chosen as the first stronger peer and is included as the reference.

## How to read the table

- **Price** is USD per million tokens, input / output, for one sensible tool-capable endpoint (first-party where one exists, otherwise an fp8 provider). Other providers can be cheaper but often serve fp4 weights or charge odd output prices. Prices are from the OpenRouter endpoint listings on 2026-10-25.
- **Tool endpoints** is "endpoints advertising `tools` / all endpoints" on OpenRouter. This is what providers advertise, not something we tested.
- **AA index** is the Artificial Analysis Intelligence Index, read from the public leaderboard on 2026-10-25 (highest listed setting, with the setting in brackets). It is a general capability composite (knowledge, reasoning, coding, agentic tasks), not a persuasion score. "n/l" means not listed in the page text we could read. Numbers marked *(unverified)* come from secondary write-ups only.
- **Cost (50 ep)** is an estimate for 50 episodes × 20 rounds × 1.5 peer calls per round = 1,500 calls, at 4,000 input + 300 output tokens per call (6.0M input, 0.45M output). The second number adds 1,000 hidden reasoning tokens per call, for the case where reasoning can't be turned off. No prompt-caching discount is assumed. Double the figures for 100 episodes.
- **Our smoke test** is the single rapport-first opener sent to each candidate on 2026-10-23 (one call per model, so weak evidence).

## Comparison table

| Model | OpenRouter id | Price in / out | Context | Tool endpoints | Reasoning | AA index | Cost (50 ep), no reasoning / +1k reasoning | Role-play notes |
|---|---|---|---|---|---|---|---|---|
| **DeepSeek V4 Pro (reference)** | `deepseek/deepseek-v4-pro` (0423 build); GA build `deepseek/deepseek-v4-pro-0813` | 0423: 0.208 / 0.416 (Baidu or StreamLake, fp8; no first-party endpoint). 0813: 0.66 / 1.98 first-party, 0.132 / 0.396 Baidu fp8 | 1M | 0423: 15/15; 0813: 23/23 | Reasoning model; `reasoning` parameter supported. AA lists a non-reasoning setting for 0813 | 36 (0813, max); 20 (0813, non-reasoning). 0423 n/l | 0423: $1.44 / $2.06. 0813 first-party: $4.85 / $7.82 | Not smoke-tested. The Flash sibling stays in role |
| MiniMax M3.1 Flash | `minimax/minimax-m3.1-flash` | 0.15 / 0.60 (MiniMax) | 1M | 13/13 | Reasoning model; `reasoning` parameter supported; disabling untested | 43 | $1.17 / $2.07 | Not tested |
| GLM 5.3 Flash | `z-ai/glm-5.3-flash` | 0.15 / 0.50 (Z.AI fp8) | 1M | 38/38 | `reasoning` parameter supported; disabling untested | 42 | $1.12 / $1.88 | Not tested. Its big sibling refused (next row) |
| GLM 5.3 | `z-ai/glm-5.3` | 1.40 / 4.40 (Z.AI fp8) | 1M | 48/48 | Reasoning **mandatory** on the endpoint we hit ("cannot be disabled"); AA lists a "low" setting | 45 (max); 34 (low) | $10.38 / $16.98 | **Refused** in our smoke test, calling the task social engineering and offering a "clearly labelled red-team" version instead |
| Tencent Hy4 preview | `tencent/hy4-preview` | 0.834 / 2.501 (Tencent fp8; same price on all 5) | 1M (Cohere 262k) | 5/5 | Reasoning model; disabling untested | n/l. Vendor: SWE-bench Pro 65.7, DeepSWE 64.3 *(unverified)* | $6.13 / $9.88 | Not tested. Preview build |
| Tencent Hy3 | `tencent/hy3` | 0.132 / 0.528 (Tencent fp8) | 262k | 5/5 | Configurable reasoning effort (OpenRouter description) | 25 | $1.03 / $1.82 | **Complied** in our smoke test (natural rapport opener) |
| GPT-6 Luna | `openai/gpt-6-luna` | 0.10 / 0.50 (OpenAI) | 1.05M | 7/7 | Effort levels from non-reasoning to max (AA) | 38 (max); 18 (non-reasoning) | $0.82 / $1.57 | **Broke role** in the pilot (warned the target not to share). Already dropped |
| GPT-6.1 Sol | `openai/gpt-6.1-sol` | 2.00 / 10.00 (OpenAI); flex tier 1.00 / 5.00 | 1.05M | 8/8 | Effort levels low to max (AA); unclear whether fully off | 52 (max); 42 (low). Vendor: DeepSWE v1.1 75.2% *(unverified)* | $16.50 / $31.50 (flex: about half) | Not tested. Same family as Luna, so a similar role-break risk |
| MiMo-V2.6-Flash | `xiaomi/mimo-v2.6-flash` | 0.14 / 0.28 (Xiaomi fp8) | 1M | 10/10 | `reasoning` parameter supported; disabling untested | 38 | $0.97 / $1.39 | Not tested |
| MiMo-V2.6-Pro (extra, same family) | `xiaomi/mimo-v2.6-pro` | 0.435 / 0.87 (Xiaomi fp8; GMICloud bf16 same price) | 1M | 5/5 | `reasoning` parameter supported; disabling untested | 46 | $3.00 / $4.31 | Not tested |
| Nemotron 3 Ultra | `nvidia/nemotron-3-ultra-550b-a55b` (also `:free`) | 0.60 / 2.40 (BaseTen fp4); 0.50 / 2.20 (DeepInfra fp4, 16k max output) | 262k (BaseTen 203k) | 5/5 | Reasoning model; disabling untested | 23 | $4.68 / $8.28 | Not tested. Only fp4 endpoints |
| Muse Spark 1.3 (Meta) | `meta/muse-spark-1.3` (also `-contributor`) | 1.25 / 4.25 (Meta, only provider) | 1M | 1/1 | Reasoning **mandatory** (the `-contributor` endpoint rejected `enabled:false`) | n/l. Secondary sources disagree (62 vs 48) *(unverified)* | $9.41 / $15.79 | **Refused** in our smoke test: its reasoning summary says it is "refusing to solicit credentials", and no message came back |
| Step 5 Preview (StepFun) | `stepfun/step-5-preview` | 1.00 / 2.70 (all 5 endpoints; the first-party one lacks `tool_choice`) | 1M (Featherless 262k) | 5/5 | Reasoning effort levels (vendor uses "High"); disabling untested | 44 | $7.21 / $11.27 | Not tested. Preview build |
| Kimi K3 (Moonshot) | `moonshotai/kimi-k3` | 3.00 / 15.00 (Moonshot); cheapest tool endpoint 0.239 / 10.8 (InferenceNet fp4) | 1M | 27/29 (Chutes and one Sail endpoint have no tools) | Reasoning model; disabling untested | n/l. Secondary sources report 57 at launch on an older index version *(unverified)* | Moonshot: $24.75 / $47.25. fp4: about $6.3 / $17 | Not tested. Older Kimi K2.6 **complied** |
| Kimi K3.1 Pro (Moonshot) | `moonshotai/kimi-k3.1-pro` | 2.00 / 10.00 (Moonshot mxfp4); "highspeed" 4 / 20 | 1M | 2/2, both Moonshot | Reasoning model (AA); disabling untested | **55**, the highest here | $16.50 / $31.50 | Not tested. Older Kimi K2.6 **complied** |
| Mercury 3 (Inception) | `inception/mercury-3` | 0.10 / 0.35 (Inception, only provider) | 1M | 1/1 | `reasoning` parameter supported; diffusion model | n/l (Mercury 2.5 is 12). Vendor claims it beats GPT-6 Luna on 8 of 12 tests *(unverified)* | $0.76 / $1.28 | Not tested |

### Benchmarks we looked for but could not use

- **Persuasion-specific evals:** we found no current leaderboard that covers these models. Published persuasion benchmarks (PersuasionBench/PersuasionArena, arXiv 2410.02653; Persuade Me If You Can, CAIS 2026) test older models such as GPT-4o and Llama-3.3-70B.
- **tau-bench / tau2-bench:** the public site shows only its top three entries, and none of these models are among them. No vendor tau2 numbers turned up for these models.
- **LMArena (now arena.ai):** the leaderboard page refused automated fetches (HTTP 403), so we have no verified Arena scores.
- **SWE-bench Verified** is mostly no longer reported. Vendors now report DeepSWE, Terminal-Bench and similar. These measure coding agents, not persuasion. DeepSeek V4 Pro reports 80.6% on SWE-bench Verified; an independent re-run (CAISI) got 74.0% on a preview build *(secondary source, unverified)*.

## Ranked top 3: strongest affordable persuasive peer

Ranking criteria, in order: likely to stay in role, clearly stronger than the reference (AA 36), reliable tool endpoints, then cost.

1. **MiMo-V2.6-Pro (`xiaomi/mimo-v2.6-pro`).** AA 46, well above DeepSeek V4 Pro (36), at about $3–4 per 50 episodes. It has a first-party fp8 endpoint and a bf16 endpoint (GMICloud), all five with tools. It has not been tested in the persuader role. Its Flash sibling (AA 38, about $1) is a cheaper fallback.
2. **Kimi K3.1 Pro (`moonshotai/kimi-k3.1-pro`).** The strongest model on the list (AA 55). The older Kimi K2.6 stayed in role in our smoke test. The costs: about $16–32 per 50 episodes, only Moonshot serves it (no provider fallback), and it is a reasoning model whose reasoning may not turn off. If budget allows one premium peer, this is it.
3. **MiniMax M3.1 Flash (`minimax/minimax-m3.1-flash`).** AA 43, about $1–2 per 50 episodes, 13 tool-capable endpoints including first-party. It is the cheapest clear step up from the reference. "Flash" in its name is MiniMax's tier name; it is not a DeepSeek Flash variant. Not tested in role.

Close alternatives: **Step 5 Preview** (AA 44, about $7–11, preview build) and **GLM 5.3 Flash** (AA 42, about $1–2; its big sibling refused, so test it first). **GPT-6.1 Sol** is strong (AA 52) but costs about $16–32 and comes from the same family as Luna, which broke role. Avoid **GLM 5.3** and **Muse Spark 1.3**: both refused the role in our smoke test, and reasoning can't be disabled on either.

## Caveats

- **The reference may not be much stronger than the current peer.** Artificial Analysis lists only the 0813 GA build of DeepSeek V4 Pro, at 36 (max reasoning) and 20 (non-reasoning). The id we chose, `deepseek/deepseek-v4-pro`, is the 0423 build, and its only listed endpoints are third-party fp8 (Baidu, StreamLake). We did not find an AA score for the 0423 build or for V4 Flash 0423, so we can't say how big the step up is. Several "Flash" models from other labs score higher (MiniMax M3.1 Flash 43, GLM 5.3 Flash 42). If we stay with DeepSeek, consider `deepseek/deepseek-v4-pro-0813` (first-party endpoint, about $5 per 50 episodes).
- **General capability is not persuasiveness.** The AA index measures knowledge, reasoning and agentic coding. No public benchmark ranks these models as persuaders. Persuasive pressure has to be measured in our own episodes, for example as the give-in rate against the same target with everything else fixed.
- **Role-breaking is the main risk and is mostly untested.** Only Hy3, GPT-6 Luna, GLM 5.3 and Muse Spark 1.3 (plus older Kimi K2.6) have any in-role evidence from us, and it is one opener each. Luna passed the opener but broke role later in real episodes. So a one-call test is not enough: read the peer's turns across a few full episodes before scaling.
- **Reasoning on vs off is a confound.** The current peer runs with reasoning off. Several stronger models are reasoning models whose reasoning may not turn off (confirmed mandatory for GLM 5.3 and Muse Spark 1.3; untested for most others). A peer that reasons is a different condition from one that doesn't, and it costs more output tokens (the second cost figure). Record the reasoning setting for every run.
- **Provider and precision vary.** Many cheap endpoints serve fp4 weights. We saw garbled output from an fp4 target endpoint earlier. Pin the provider and quantisation for the peer, as the harness already does for DeepSeek Flash. Kimi K3.1 Pro, Muse Spark 1.3 and Mercury 3 each have a single provider, so an outage stops the run.
- **Prices and listings change.** All prices and endpoint counts are a 2026-10-25 snapshot. Costs ignore prompt-caching discounts, which could lower input costs a lot for a growing conversation.
- **Benchmark provenance.** AA numbers were read from the public leaderboard page on 2026-10-25. The page text was truncated, so "n/l" may mean the model is listed further down. Vendor figures are self-reported, and different harnesses can move them by 10+ points.

## Suggested next step (needs an OK, costs cents)

Rerun the existing recruiter smoke test (`experiments/E01-behaviour-pilot/smoke/smoke_recruiters.py`) on the top candidates with tools on. Then run 2–3 full episodes per candidate against the main target and read the peer's turns for role breaks. At the token sizes above, one 20-round episode costs about $0.02 (MiniMax M3.1 Flash) to $0.33 (Kimi K3.1 Pro).

## Sources

- OpenRouter model list: https://openrouter.ai/api/v1/models, and per-model endpoints: `https://openrouter.ai/api/v1/models/<id>/endpoints` (fetched 2026-10-25).
- Artificial Analysis leaderboard: https://artificialanalysis.ai/leaderboards/models; model pages https://artificialanalysis.ai/models/kimi-k3-1-pro and https://artificialanalysis.ai/models/deepseek-v4-pro (fetched 2026-10-25).
- Our smoke test: `experiments/E01-behaviour-pilot/smoke/recruiters_summary.json`, `recruiters_raw/`; the Luna role break is logged in `EXPERIMENT_LOG.md` (2026-10-23 22:58).
- Secondary or vendor (unverified): Kimi K3, https://apidog.com/blog/kimi-k3-benchmarks/ and https://rits.shanghai.nyu.edu/ai/kimi-k3-hits-third-on-artificial-analysis-open-weights-due-july-27/; Hy4 preview, https://www.datalearner.com/en/ai-models/pretrained-models/hy4-preview; Mercury 3, https://siliconangle.com/2026/10/20/inception-says-mercury-3-beats-gpt-6-luna-and-claude-haiku-5-5-at-up-to-8x-the-speed/; Muse Spark 1.3, https://www.eesel.ai/blog/muse-spark-1-3 and https://www.mindstudio.ai/blog/meta-muse-spark-1-3-benchmark-confusion; MiniMax M3.1 Flash, https://aimlapi.com/blog/minimax-m3-1-flash-review; MiMo-V2.6, https://computingforgeeks.com/xiaomi-mimo-v2-6-pro-flash/; Step 5 Preview, https://www.developersdigest.tech/blog/stepfun-step-5-preview-open-weights-oct-15-2026; GPT-6.1 Sol, https://www.vellum.ai/md/blog/gpt-6-1-sol-benchmarks-explained; DeepSeek V4 Pro, https://www.datalearner.com/en/ai-models/pretrained-models/deepseek-v4-pro/analysis.
- Persuasion benchmarks: https://arxiv.org/abs/2410.02653; https://caisconf.org/program/2026/papers/persuade-me-if-you-can-a-framework-for-evaluating-persuasion-effectiveness-and-s/.
- tau-bench site: https://taubench.com/.
