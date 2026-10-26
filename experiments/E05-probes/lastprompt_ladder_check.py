"""Independently verify saved label-ladder predictions and stratified AUROCs."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits
from lastprompt_percall import load, SEEDS, FITS


def check(out):
    rows, _, x, _ = load()
    metrics = json.loads((out / 'metrics.json').read_text())
    fits = points = 0
    max_error = reconstruction_error = 0.
    for key, metric in metrics.items():
        label, mode = key.split('/')
        estimates, baseline_estimates = [], []
        for seed in SEEDS:
            observed = []
            groups, baseline_groups = defaultdict(list), defaultdict(list)
            for path in sorted((out / 'matched' / key).glob(f's{seed}-*/fit.json')):
                f = json.loads(path.read_text())
                z = np.load(path.parent / 'scores.npz')
                model = np.load(path.parent / 'model.npz')
                ids = z['indices']
                observed.extend(ids.tolist())
                for a, b in [('train', 'test'), ('inner_train', 'inner_validation'), ('calibration', 'test')]:
                    assert not {rows[i]['family'] for i in f['split'][a]} & {rows[i]['family'] for i in f['split'][b]}
                values = np.asarray(x[[rows[i]['index'] for i in ids], f['layer']], dtype=float)
                pred = ((values - model['mean']) / model['scale']) @ model['coef'][0] + model['intercept'][0]
                error = float(np.max(abs(pred - z['scores'])))
                assert error < 1e-9
                reconstruction_error = max(reconstruction_error, error)
                cp = z['calibration_scores']
                threshold = np.sort(cp)[len(cp) - int(.05 * len(cp)) - 1]
                assert threshold == f['threshold'] and np.mean(cp > threshold) <= .05
                folder = FITS / 'post_ask/A_hazard' / mode / f"s{seed}-f{f['plan']['fold']}"
                bf = json.loads((folder / 'fit.json').read_text())
                b = np.load(folder / f"lr-l{bf['layer']}.npz")
                values = np.asarray(x[[rows[i]['index'] for i in ids], bf['layer']], dtype=float)
                bp = ((values-b['mean'])/b['scale']) @ b['coef'][0] + b['intercept'][0]
                for i, score, base in zip(ids, pred, bp):
                    r = rows[i]
                    y = int(r['ever_public'] and (label == 'eventual_any' or r['y_near']))
                    groups[r['scenario'], r['round']].append((y, score))
                    baseline_groups[r['scenario'], r['round']].append((y, base))
                fits += 1
            expected = {i for i,r in enumerate(rows) if r['condition']=='recruiting' and r['stream_window']=='post_ask' and r['reasoning_tokens']>0}
            assert len(observed) == len(set(observed)) == 1995 and set(observed) == expected
            for collection, dest in [(groups, estimates), (baseline_groups, baseline_estimates)]:
                weighted, positives = 0., 0
                for pairs in collection.values():
                    y, s = np.asarray(pairs).T
                    if len(np.unique(y)) < 2:
                        continue
                    weighted += roc_auc_score(y, s) * y.sum()
                    positives += y.sum()
                dest.append(weighted / positives)
                points += 1
        for got, want in [(np.mean(estimates), metric['within_round_auc']), (np.mean(baseline_estimates), metric['frozen_paper_A']['within_round_auc'])]:
            error = abs(got-want)
            assert error < 1e-12
            max_error = max(max_error, error)
    result = dict(fits_checked=fits, thresholds_checked=fits, independent_sklearn_points=points, max_point_error=max_error, max_model_reconstruction_error=reconstruction_error, cohort_and_family_checks='passed')
    (out/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    with threadpool_limits(limits=2):
        check(p.parse_args().out)
