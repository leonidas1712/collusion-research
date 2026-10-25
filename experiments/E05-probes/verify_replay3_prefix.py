"""Require exact old-cache preservation and exact append-only replay3 assembly."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run


def main(args):
    old_id = '20261025-0337-e05-replay2-data'
    run = start_run('e05-replay3-prefix-validation', experiment='E05', parents=[old_id, args.combined, args.new], settings=vars(args))
    try:
        def load(name):
            directory = ROOT / 'runs' / name
            assert json.loads((directory / 'meta.json').read_text())['status'] == 'finished'
            rows = [json.loads(s) for s in (directory / 'rows.jsonl').read_text().splitlines()]
            return rows, np.load(directory / 'features.npy', mmap_mode='r')
        old, old_x = load(old_id)
        new, new_x = load(args.new)
        combined, combined_x = load(args.combined)
        assert len(old) == 6026
        assert combined[:len(old)] == old
        assert len(combined) == len(old) + len(new)
        for i, row in enumerate(new):
            assert combined[len(old) + i] == {**row, 'index': len(old) + i}
        for start in range(0, len(old), 64):
            end = min(start + 64, len(old))
            assert np.array_equal(combined_x[start:end], old_x[start:end])
        for start in range(0, len(new), 64):
            assert np.array_equal(combined_x[len(old) + start:len(old) + min(start + 64, len(new))], new_x[start:start + 64])
        old_families = {r['family'] for r in old if not r['shared_branch_history']}
        new_families = {r['family'] for r in new}
        assert not old_families & new_families, 'Confirmation families overlap development data'
        result = dict(old_rows=len(old), new_rows=len(new), combined_rows=len(combined),
                      exact_metadata_prefix=True, exact_feature_prefix=True, exact_new_append=True,
                      development_confirmation_families_disjoint=True)
        (run.dir / 'summary.json').write_text(json.dumps(result, indent=2))
        run.result(**result)
        run.finish()
        print('PREFIX_RUN', run.id)
    except BaseException as exc:
        run.finish('failed', str(exc))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('combined')
    parser.add_argument('new')
    main(parser.parse_args())
