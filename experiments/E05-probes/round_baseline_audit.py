"""Unstratified AUROC for round and minus-round on eligible recruiting steps.

No models are fitted and no activation arrays are loaded. Run from the repo root:
    uv run --with numpy --with scipy --with scikit-learn --with threadpoolctl \
      python experiments/E05-probes/round_baseline_audit.py --check
"""
import argparse
import json
from pathlib import Path

import numpy as np

from data import ROOT
from metrics import auc


DEFAULT_ROWS = ROOT / 'runs/20261025-1026-e05-replay3-data-1d95/rows.jsonl'
REFERENCE = ROOT / 'runs/20261026-0155-e05-paper-round-baseline-audit/summary.json'


def calculate(rows):
    rounds = np.array([r['round'] for r in rows], dtype=float)
    eventual_keep = np.array([r['eligible'] and r['condition'] == 'recruiting' for r in rows])
    eventual = np.array([r['label'] for r in rows], dtype=int)
    # near_term.label_rows('A_hazard') retains the same eligible recruiting rows.
    hazard_keep = eventual_keep.copy()
    hazard = np.zeros(len(rows), dtype=int)
    for i in np.flatnonzero(eventual_keep):
        r = rows[i]
        assert r['ordinal'] > r['first_read']
        if eventual[i]:
            assert r['first_action'] > r['ordinal']
            assert r['steps_until_action'] == r['first_action'] - r['ordinal']
            delta = r['action_round'] - r['round']
            assert delta >= 0
            hazard[i] = int(delta <= 1)
    result = {}
    for name, keep, labels in [('eventual', eventual_keep, eventual),
                                ('A_hazard', hazard_keep, hazard)]:
        y, score = labels[keep], rounds[keep]
        if set(y) != {0, 1}:
            raise ValueError(f'{name} needs both positive and negative rows')
        result[name] = {
            'rows': len(y),
            'positives': int(y.sum()),
            'positive_round_auc': auc(y, score),
            'negative_round_auc': auc(y, -score),
            'positive_mean_round': float(score[y == 1].mean()),
            'negative_mean_round': float(score[y == 0].mean()),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows', type=Path, default=DEFAULT_ROWS)
    parser.add_argument('--output', type=Path, help='Optional JSON output; otherwise print only')
    parser.add_argument('--check', action='store_true', help='Compare all values with the saved audit')
    parser.add_argument('--reference', type=Path, default=REFERENCE)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.rows.read_text().splitlines() if line.strip()]
    result = calculate(rows)
    if args.check:
        expected = json.loads(args.reference.read_text())
        assert result.keys() == expected.keys()
        for label, values in result.items():
            assert values.keys() == expected[label].keys()
            for key, value in values.items():
                assert np.isclose(value, expected[label][key], rtol=0, atol=1e-12), (label, key, value)
    rendered = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end='')


if __name__ == '__main__':
    main()
