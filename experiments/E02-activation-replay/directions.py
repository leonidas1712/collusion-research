"""Descriptive difference of means; wiring only, not a trained/evaluated probe."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from collusion.runs import start_run, write_json_atomic


def main(args):
    source = Path(args.replay_run).resolve()
    run = start_run('e02-direction-wiring', experiment='E02', settings=vars(args),
                    parents=[source.name], tags=['wiring'])
    try:
        rows = [json.loads(line) for line in (source/'index.jsonl').read_text().splitlines()]
        groups = {True:[],False:[]}
        episodes = {True:set(),False:set()}
        # One input per episode, so tool loops and retries cannot dominate the mean.
        seen = set()
        for row in rows:
            key = (row['run_id'],row['episode_file'])
            group = row.get(args.group)
            if key in seen or row['attempt'] != 1 or row['step_in_turn'] != 1 or row['before_first_leak'] is not True:
                continue
            if not isinstance(group,bool):
                continue
            seen.add(key)
            with np.load(source/row['artifact']) as data:
                groups[group].append(data['residual_last'].copy())
            episodes[group].add(key)
        counts = {str(k):len(v) for k,v in groups.items()}
        if not all(groups.values()):
            raise ValueError(f'Both boolean groups required; found {counts}. No direction produced.')
        means = {k:np.stack(v).mean(axis=0) for k,v in groups.items()}
        direction = means[True]-means[False]
        np.savez_compressed(run.dir/'directions.npz', direction=direction,
                            mean_true=means[True],mean_false=means[False])
        summary = {'group':args.group,'episodes':counts,'shape':list(direction.shape),
                   'layer_norms':np.linalg.norm(direction,axis=1).tolist(),
                   'interpretation':'Wiring only. First eligible pre-leak prompt per episode; true minus false. No validation, accuracy, causal or predictive claim.'}
        write_json_atomic(run.dir/'summary.json',summary)
        print(json.dumps(summary))
        run.result(**summary); run.finish()
    except BaseException as exc:
        run.finish('failed',f'{type(exc).__name__}: {exc}')
        raise


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('replay_run')
    p.add_argument('--group',choices=['objective_success','eligible_resisted','first_step'],default='objective_success')
    main(p.parse_args())
