"""Verify the completed gpt-oss OOF export against every saved fold score."""
import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np

from data import ROOT
from gpt_oss_probes import label_rows

sys.path.insert(0, str(ROOT/'src'))
from collusion.runs import start_run, write_json_atomic


def main(args):
    source, data = Path(args.probes).resolve(), Path(args.data).resolve()
    assert json.loads((source/'meta.json').read_text())['status'] == 'finished'
    rows = [json.loads(line) for line in (data/'rows.jsonl').read_text().splitlines()]
    plans = json.loads((source/'plans.json').read_text())
    run = start_run('e05-gpt-oss-score-audit', experiment='E05', parents=[source.name, data.name],
                    settings={'no_refit': True, 'check_every_export_row': True})
    try:
        expected = {}
        for plan in plans:
            window, variant, mode, seed, fold = [plan[k] for k in ['window', 'variant', 'mode', 'seed', 'fold']]
            folder = source/window/variant/mode/f's{seed}-f{fold}'
            fit = json.loads((folder/'fit.json').read_text())
            selection = {int(k): v for k, v in fit['selection'].items()}
            chosen = max(selection, key=lambda k: (selection[k] if np.isfinite(selection[k]) else -1, -k))
            assert chosen == fit['layer']
            split = plan['split']
            family = lambda name: {rows[i]['family'] for i in split[name]}
            assert not family('train') & family('test')
            assert not family('inner_train') & family('inner_validation')
            assert not family('calibration') & family('test')
            keep, labels = label_rows(rows, window, variant)
            with np.load(folder/'scores.npz') as saved:
                assert saved['test'].tolist() == split['test']
                assert saved['evaluate'].tolist() == split['test'] + split['calibration']
                assert np.array_equal(saved['y'], labels[saved['evaluate']])
                for method in ['nested', 'fixed12']:
                    for position, i in enumerate(split['test']):
                        assert keep[i]
                        key = (window, variant, mode, seed, fold, method, rows[i]['row_id'])
                        assert key not in expected
                        expected[key] = (float(saved[method][position]), int(labels[i]), i)
        checked = 0
        with (source/'probe_scores.csv').open() as stream:
            for exported in csv.DictReader(stream):
                key = tuple(exported[k] for k in ['window', 'label_variant', 'analysis']) + (
                    int(exported['seed']), int(exported['fold']), exported['method'], exported['row_id'])
                score, label, i = expected.pop(key)
                row = rows[i]
                assert abs(float(exported['score'])-score) < 1e-12
                assert int(exported['label']) == label and int(exported['row']) == i
                assert exported['step_id'] == row['row_id']
                assert exported['request_sha256'] == row['request_sha256']
                assert int(exported['request_idx']) == row['request_idx']
                assert exported['episode'] == row['episode']
                assert exported['scenario'] == row['scenario']
                checked += 1
        assert not expected
        result = dict(folds=len(plans), exported_rows=checked, all_scores_and_labels_match=True,
                      no_missing_or_duplicate_rows=True, family_disjoint=True)
        write_json_atomic(run.dir/'summary.json', result)
        run.result(**result)
        run.finish()
        print('SCORE_AUDIT', run.dir, json.dumps(result))
    except BaseException as exc:
        run.finish('failed', str(exc))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--probes', required=True)
    parser.add_argument('--data', required=True)
    main(parser.parse_args())
