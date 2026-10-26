"""Independently reconstruct confirmation AUROCs from its exported row scores."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits


def pair_auc(y, score, weights):
    positive, negative = y == 1, y == 0
    wp, wn = weights[:, positive], weights[:, negative]
    wins = ((score[positive, None] > score[negative][None, :]).astype(float)
            + .5 * (score[positive, None] == score[negative][None, :]))
    denominator = wp.sum(axis=1) * wn.sum(axis=1)
    numerator = np.sum((wn @ wins.T) * wp, axis=1)
    return np.divide(numerator, denominator, out=np.full(len(weights), np.nan), where=denominator > 0), wp.sum(axis=1)


def within(y, score, weights, strata):
    numerator = np.zeros(len(weights)); denominator = np.zeros(len(weights))
    for group in sorted(set(strata)):
        mask = np.array([s == group for s in strata])
        value, positives = pair_auc(y[mask], score[mask], weights[:, mask])
        valid = np.isfinite(value)
        numerator[valid] += value[valid] * positives[valid]
        denominator[valid] += positives[valid]
    return np.divide(numerator, denominator, out=np.full(len(weights), np.nan), where=denominator > 0)


def main(freeze):
    result = json.loads((freeze / 'confirmation_result.json').read_text()); out = Path(result['run'])
    metrics = json.loads((out / 'metrics.json').read_text())
    all_rows = list(csv.DictReader((out / 'probe_scores.csv').open()))
    rows = [r for r in all_rows if r['condition'] == 'recruiting' and int(r['reasoning_tokens']) > 0]
    assert len(rows) == result['counts']['scored_recruiting_replies']
    y = np.array([int(r['y_immediate']) for r in rows])
    family, codes = np.unique([r['family'] for r in rows], return_inverse=True)
    draws = np.random.default_rng(20261025).multinomial(len(family), np.ones(len(family)) / len(family), size=1000)
    weights = np.vstack([np.ones(len(rows)), draws[:, codes]])
    strata = [(r['scenario'], int(r['round'])) for r in rows]
    checked = {}
    with threadpool_limits(limits=2):
        for method, expected in metrics.items():
            scores = np.array([float(r[method]) for r in rows])
            values = within(y, scores, weights, strata)
            pooled, _ = pair_auc(y, scores, weights)
            for key, array in [('within_round', values), ('pooled', pooled)]:
                if not np.isfinite(array[0]):
                    assert not np.isfinite(expected[key + '_auc'])
                    continue
                assert abs(array[0] - expected[key + '_auc']) < 1e-10, (method, key)
                ci = np.nanquantile(array[1:], [.025, .975])
                np.testing.assert_allclose(ci, expected[key + '_ci95'], rtol=0, atol=1e-10)
            checked[method] = {'within_auc': float(values[0]), 'pooled_auc': float(pooled[0]), 'ci_parity': True}
    frozen = json.loads((freeze / 'frozen_plan.json').read_text())
    assert hashlib.sha256((freeze / 'frozen_weights.json').read_bytes()).hexdigest() == frozen['weights_sha256']
    threshold = frozen['alarm']['threshold']
    for row in all_rows:
        alarm = bool(row['max_score'] and float(row['max_score']) > threshold)
        assert alarm == (row['alarm'] == 'True'), row['row_id']
    audit = {'methods': checked, 'source_rows': len(all_rows), 'scored_rows': len(rows),
             'bootstrap_draws': 1000, 'seed': 20261025, 'all_row_alarm_decisions_match': True,
             'weights_hash_unchanged': True, 'independent_method': 'direct row-pair wins, before family aggregation',
             'source_csv_sha256': hashlib.sha256((out / 'probe_scores.csv').read_bytes()).hexdigest()}
    (out / 'independent_audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print('INDEPENDENT_CONFIRMATION_AUDIT_PASS', out, len(rows))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--freeze', type=Path, required=True)
    main(p.parse_args().freeze)
