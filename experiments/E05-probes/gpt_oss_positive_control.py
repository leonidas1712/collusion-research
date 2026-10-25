"""Family-held-out exposure check for the 24-layer gpt-oss cache; no outcome fit."""
import argparse
import json
import sys

import numpy as np
from threadpoolctl import threadpool_limits

from data import ROOT
from metrics import auc
from models import fit_logistic, score

sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run, write_json_atomic


def main(args):
    source = ROOT/'runs'/args.data_run
    assert json.loads((source/'meta.json').read_text())['status'] == 'finished'
    rows = [json.loads(line) for line in (source/'rows.jsonl').read_text().splitlines()]
    x = np.load(source/'features.npy', mmap_mode='r')
    assert x.shape == (len(rows), 24, 2880)
    run = start_run('e05-gpt-oss-positive-control', experiment='E05', parents=[args.data_run],
        settings={'gate_layer': 12, 'minimum_auc': .95, 'seed': 42, 'family_holdout': .3,
                  'curve_layers': 'all24', 'C': .1, 'label': 'token_in_context'})
    try:
        # Retain pre-read requests: an exposure control needs both exposed and unexposed inputs.
        indices = np.array([i for i, r in enumerate(rows) if r['valid']])
        families = np.array([r['family'] for r in rows])
        unique = np.unique(families[indices])
        shuffled = np.random.default_rng(42).permutation(unique)
        held = set(shuffled[:int(np.ceil(len(unique)*.3))])
        test = indices[np.isin(families[indices], list(held))]
        train = indices[~np.isin(families[indices], list(held))]
        assert not set(families[train]) & set(families[test])
        y = np.array([r['token_in_context'] for r in rows], dtype=int)
        assert len(set(y[test])) == len(set(y[train])) == 2
        values = []
        pred = np.full((24, len(rows)), np.nan)
        with threadpool_limits(limits=4):
            for layer in [12] + [layer for layer in range(24) if layer != 12]:
                model = fit_logistic(x[train, layer], y[train])
                s = score(model, x[test, layer])
                metric = auc(y[test], s)
                pred[layer, test] = s
                values.append(dict(layer=layer, auc=metric))
                write_json_atomic(run.dir/'curve.json', sorted(values, key=lambda r: r['layer']))
                print('EXPOSURE', layer, metric, flush=True)
                if layer == 12 and metric < .95:
                    raise RuntimeError(f'Integrity gate failed: layer12 exposure AUROC {metric} < .95')
        np.savez_compressed(run.dir/'predictions.npz', scores=pred, train=train, test=test, y=y)
        write_json_atomic(run.dir/'split.json', dict(train_families=sorted(set(families[train])),
            test_families=sorted(held), train_rows=len(train), test_rows=len(test),
            test_episodes=len({rows[i]['episode'] for i in test})))
        result = dict(gate_passed=True, gate_layer=12,
            gate_auc=next(v['auc'] for v in values if v['layer'] == 12),
            min_auc=min(v['auc'] for v in values), test_rows=len(test),
            curve=sorted(values, key=lambda r: r['layer']))
        write_json_atomic(run.dir/'summary.json', result)
        run.result(**result)
        run.finish()
        print('CONTROL_RUN', run.id)
    except BaseException as exc:
        run.finish('failed', str(exc))
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('data_run')
    main(p.parse_args())
