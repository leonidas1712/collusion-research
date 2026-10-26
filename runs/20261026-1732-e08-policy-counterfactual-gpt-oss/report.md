# E08 policy-counterfactual replay

Run: `20261026-1732-e08-policy-counterfactual-gpt-oss`. `openai/gpt-oss-20b` prefill/teacher-forcing only; no generation or refitting. The frozen plan contains 26 leaking calls and 57 score-blind non-leaking calls matched exactly by scenario and round, each replayed under FORBID, PERMIT and NEUTRAL-EDIT.

## Integrity

The unchanged FORBID condition reproduced the saved frozen-probe score with maximum absolute error 8.88178e-16 (required <= 0.001). All 249 call-condition rows and their activation files are present.

The gpt-oss benchmark and full run used an estimated $0.158 of A100 time. Total estimated E08 GPU spend across both model arms, including the rejected Qwen diagnostic pair, was $1.040 against the $6 cap.

## Results

| Quantity | Estimate | 95% family-bootstrap CI |
|---|---:|---:|
| Median PERMIT - FORBID, leaking calls | 0.002 | [-0.022, 0.027] |
| Median NEUTRAL-EDIT - FORBID, leaking calls | 0.012 | [-0.025, 0.042] |
| Median PERMIT - NEUTRAL-EDIT, leaking calls | -0.000 | [-0.025, 0.027] |
| Within-scenario-and-round AUROC, FORBID | 0.808 | [0.649, 0.944] |
| Within-scenario-and-round AUROC, PERMIT | 0.821 | [0.663, 0.957] |
| Within-scenario-and-round AUROC, NEUTRAL_EDIT | 0.827 | [0.679, 0.957] |
| Leaking calls above frozen threshold, FORBID | 8/26 (30.8%) | [13.0%, 50.0%] |
| Leaking calls above frozen threshold, PERMIT | 8/26 (30.8%) | [13.0%, 50.0%] |
| Leaking calls above frozen threshold, NEUTRAL_EDIT | 6/26 (23.1%) | [8.3%, 40.7%] |

## Reading

PERMIT and the neutral edit are not clearly separated; the frozen probe mostly tracks being about to emit the protected value in this test.

Caveat: this is an off-policy counterfactual. Under PERMIT the model might not have produced exactly the observed output, although sharing was allowed. The prompt edit leaves the separate consequence sentence unchanged, so PERMIT removes the prohibition but not every operational cost of disclosure.

## Files

- `plan.json`: immutable pre-GPU design and exact call list.
- `scores.csv`: one row per call and policy condition.
- `activations/`: last-prompt residual vectors at frozen layers 6, 13.
- `gpu_summary.json` and `input_manifest.json`: runtime and hash provenance.
- `spend.json`: gpt-oss arm and shared E08 GPU-time accounting.
