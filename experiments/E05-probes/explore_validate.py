"""Audit exploratory exports against saved folds, predictions and model artifacts."""
import argparse
import csv
import json
from pathlib import Path

from explore_trajectories import DATA, LAYERS, METHODS, ROOT, SEEDS, cases, load_inputs
import numpy as np
from threadpoolctl import threadpool_limits


def validate(directory):
    rows, eligible, near = load_inputs()
    assignments = cases(rows, eligible)
    with np.load(directory/'trajectory_links.npz') as links:
        for i in eligible:
            previous, anchor = int(links['previous'][i]), int(links['anchor'][i])
            assert rows[previous]['episode'] == rows[i]['episode'] == rows[anchor]['episode']
            assert rows[i]['ordinal'] - rows[previous]['ordinal'] == 1
            assert rows[anchor]['ordinal'] <= rows[i]['ordinal']
            assert rows[anchor]['ordinal'] == rows[i]['first_read'] + 1
    sources = {
        'delta': np.load(directory/'delta.npy', mmap_mode='r'),
        'scalar': np.load(directory/'scalar.npy', mmap_mode='r'),
        'absolute': np.load(ROOT/'runs'/DATA/'features.npy', mmap_mode='r'),
    }
    predictions = {mode: np.load(directory/f'{mode}-predictions.npz') for mode in ('pooled', 'loso')}
    checked = 0
    max_error = 0.0
    for case in assignments:
        mode, seed, fold = (case[k] for k in ('mode', 'seed', 'fold'))
        si = SEEDS.index(seed)
        output = predictions[mode]
        assert (output['folds'][si, case['test']] == fold).all()
        for name in [f'{v}__{m}' for v in ('eventual', 'A_hazard') for m in METHODS] + ['pressure_l32']:
            with np.load(directory/'fits'/f'{mode}-s{seed}-f{fold}-{name}.npz') as fit:
                train, test = case['train'], case['test']
                if name == 'pressure_l32':
                    train = np.sort(np.r_[train, case['cal']])
                    source = sources['absolute'][:, 32, :]
                else:
                    variant, feature = name.split('__')
                    kind, layer = feature.split('_l')
                    source = sources[kind][:, LAYERS.index(int(layer)), :]
                    if variant == 'A_hazard':
                        train, test = train[near[train] >= 0], test[near[test] >= 0]
                assert np.array_equal(train, fit['train'])
                assert np.array_equal(test, fit['test'])
                assert np.array_equal(output[name][si, test], fit['scores'])
                for start in range(0, len(test), 128):
                    stop = start + 128
                    x = np.asarray(source[test[start:stop]], dtype=np.float64)
                    values = ((x-fit['mean'])/fit['scale']) @ fit['coef'][0] + fit['intercept'][0]
                    error = float(np.max(np.abs(values-fit['scores'][start:stop])))
                    max_error = max(max_error, error)
                    assert np.allclose(values, fit['scores'][start:stop], rtol=1e-7, atol=1e-7)
                checked += 1
    # Load each prediction array once rather than repeatedly decompressing per CSV row.
    arrays = {mode: {key: archive[key] for key in archive.files} for mode, archive in predictions.items()}
    count = 0
    with (directory/'probe_scores.csv').open() as file:
        for record in csv.DictReader(file):
            i, si = int(record['row']), SEEDS.index(int(record['seed']))
            variant, method = record['label_variant'], record['method']
            output = arrays[record['analysis']]
            key = 'pressure_l32' if method == 'pressure_l32' else f'{variant}__{method}'
            assert float(record['score']) == output[key][si, i]
            assert int(record['fold']) == output['folds'][si, i]
            expected_label = near[i] if variant == 'A_hazard' else (
                int(rows[i]['condition'] == 'recruiting') if variant == 'pressure' else rows[i]['label'])
            assert int(record['label']) == expected_label
            assert record['row_id'] == rows[i]['episode']+'::request_idx='+str(rows[i]['request_idx'])
            assert record['request_sha256'] == rows[i]['request_sha256']
            count += 1
    expected_count = 2*len(SEEDS)*(7*len(eligible)+7*int((near >= 0).sum())+len(eligible))
    assert count == expected_count
    assert checked == len(assignments)*13 == 429
    result = dict(fit_artifacts=checked, csv_rows=count, all_scores_reconstructed=True,
                  max_absolute_score_error=max_error, exact_fold_membership=True,
                  csv_labels_and_scores_match=True, consecutive_target_steps=len(eligible))
    (directory/'validation.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    with threadpool_limits(limits=2):
        validate(parser.parse_args().run)
