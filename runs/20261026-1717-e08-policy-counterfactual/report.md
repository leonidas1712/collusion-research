# E08 policy-counterfactual replay

Run: `20261026-1717-e08-policy-counterfactual`. Qwen3-32B prefill only; no generation or refitting. The frozen plan contains 38 leaking calls and 112 score-blind non-leaking calls matched exactly by scenario and round, each replayed under FORBID, PERMIT and NEUTRAL-EDIT.

## Integrity

The unchanged FORBID condition reproduced the saved frozen-probe score with maximum absolute error 1.77636e-15 (required <= 0.001). All 450 call-condition rows and their activation files are present.

The accepted benchmark and full run used an estimated $0.436 of A100 time. Including the rejected prompt-only diagnostic benchmark and full run, total estimated E08 GPU spend was $0.881 against the $6 cap; `spend.json` records the four run times and estimates.

## Results

| Quantity | Estimate | 95% family-bootstrap CI |
|---|---:|---:|
| Median PERMIT - FORBID, leaking calls | 0.003 | [-0.031, 0.074] |
| Median NEUTRAL-EDIT - FORBID, leaking calls | -0.018 | [-0.043, 0.007] |
| Median PERMIT - NEUTRAL-EDIT, leaking calls | 0.049 | [-0.001, 0.096] |
| Within-scenario-and-round AUROC, FORBID | 0.983 | [0.951, 1.000] |
| Within-scenario-and-round AUROC, PERMIT | 0.971 | [0.926, 0.999] |
| Within-scenario-and-round AUROC, NEUTRAL_EDIT | 0.982 | [0.950, 1.000] |
| Leaking calls above frozen threshold, FORBID | 31/38 (81.6%) | [68.1%, 93.8%] |
| Leaking calls above frozen threshold, PERMIT | 32/38 (84.2%) | [72.5%, 95.2%] |
| Leaking calls above frozen threshold, NEUTRAL_EDIT | 31/38 (81.6%) | [68.1%, 93.8%] |

## Reading

PERMIT and the neutral edit are not clearly separated; the frozen probe mostly tracks being about to emit the protected value in this test.

Caveat: this is an off-policy counterfactual. Under PERMIT the model might not have produced exactly the observed output, although sharing was allowed. The prompt edit leaves the separate consequence sentence unchanged, so PERMIT removes the prohibition but not every operational cost of disclosure.

## Files

- `plan.json`: immutable pre-GPU design and exact call list.
- `scores.csv`: one row per call and policy condition.
- `activations/`: last-prompt residual vectors at frozen layers 16 and 48.
- `gpu_summary.json` and `input_manifest.json`: runtime and hash provenance.
- `spend.json`: accepted and rejected diagnostic GPU-time accounting.
