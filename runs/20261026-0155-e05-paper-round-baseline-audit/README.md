# Round-only baseline audit

This audit scores eligible recruiting steps with the round number and its negative,
using ordinary, unstratified AUROC. Earlier rounds receive higher risk under the
negative-round score. No model is fitted and no activation array is loaded.

Reproduce and check every value in `summary.json` from the repository root:

```sh
uv run --with numpy --with scipy --with scikit-learn --with threadpoolctl \
  python experiments/E05-probes/round_baseline_audit.py --check
```

The default input is
`runs/20261025-1026-e05-replay3-data-1d95/rows.jsonl`. Both labels use the
4,697 eligible recruiting steps. The eventual label has 998 positives; the
current-or-next-round label has 250. Negative-round AUROC is 0.7232731209919162
and 0.7074904429952777, respectively. Tied round scores count one half.

Use `--rows` for another row table, `--reference` for another saved summary, and
`--output` to save the computed JSON. The original `meta.json` retains the stdin
command used for the initial calculation; this script supplies its rerunnable
equivalent without changing that provenance.
