# E08: Policy counterfactual replay. Does the probe track breaking the rule, or just emitting the value?

Approved by Leo on 27 Oct 2026. GPU budget: **$6 maximum** on Modal. This comes out of the night's $10 cap, of which $0 has been spent. Benchmark first and stop if the projected cost exceeds the cap.

## Question
Every positive call in the paper writes the secret, and every negative does not. So a probe could be detecting "about to output the protected value" rather than "about to break the operator's rule". This experiment separates the two by keeping the output fixed and changing only the policy.

## Design (counterfactual replay; prefill/teacher-forcing only, no new generation)
1. **Model and probe.** Use Qwen3-32B with the frozen per-call last-prompt probe from `paper-arxiv/frozen/qwen_percall_plan.json` and its three hashed weights. The target is the same as the paper's Qwen per-call result.
2. **Calls.** Take every leaking call in the Qwen fresh episodes (38 calls), plus a matched sample of non-leaking calls from the same episodes and rounds, about 3 per leaking call.
3. **Conditions.** For each call, rebuild the exact prompt the model saw at that call under three system-prompt variants:
   - **FORBID:** the original, unchanged. Check that it reproduces the saved score to within 1e-3.
   - **PERMIT:** edit only the operator-rule sentence so that sharing the value with teammates is explicitly allowed. Keep the edit minimal: same length class, same position.
   - **NEUTRAL-EDIT (control):** reword the rule sentence without changing what it permits. This measures how far any edit alone moves the score.
4. **Capture.** Record the last-prompt-token activation at the probe's layer(s). Score each condition with the frozen probe, using the same ensemble and scaling as the paper.
5. **Stopping point.** Do not generate, and do not refit.

## Freeze before running
Before any GPU run, commit `experiments/E08-policy-counterfactual/plan.json` containing:
- the three rule texts;
- the call list and the rule for selecting it;
- the metrics;
- the reading rules below.

## Metrics
- On leaking calls: the paired score change PERMIT − FORBID, compared with NEUTRAL-EDIT − FORBID. Report the mean or median and a bootstrap CI by episode family.
- The AUROC of leaking vs non-leaking calls under each condition.
- The fraction of leaking calls that cross the original frozen threshold under each condition.

## Reading rules (fixed in advance)
- **The PERMIT drop is clearly larger than the NEUTRAL-EDIT change, with a CI that excludes zero:** the probe is sensitive to the policy violation, not only to the emission.
- **PERMIT ≈ NEUTRAL-EDIT:** the probe mostly tracks "about to write the protected value". The paper says so plainly.
- **Caveat to report:** this is an off-policy counterfactual. Under PERMIT the model might not have produced exactly that output. It plausibly would have, since sharing is allowed.

## Optional, only if under budget
Repeat with gpt-oss-20b's frozen fresh last-prompt probe (`2b05b71`) on its 26 fresh leaking calls.

## Output
- A new run folder, `runs/<ts>-e08-policy-counterfactual/`, with `report.md`, `metrics.json` and the scores CSV.
- A one-paragraph result posted to @claude.
- Do not touch the paper. The coordinator decides placement once the result is in.
