"""Estimate replay3 cost from measured replay timings before a paid phase."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import nnls

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run


def main(args):
    plan = ROOT / 'runs' / args.plan
    bench = ROOT / 'runs' / args.benchmark
    run = start_run('e02-replay3-projection', experiment='E02',
                    parents=[args.plan, args.benchmark] + ([args.client] if args.client else []),
                    settings={**vars(args), 'cap_usd': 7, 'max_rate': .00090,
                              'price_source': 'https://modal.com/pricing', 'safety_factor': 1.25})
    try:
        rows = [json.loads(s) for s in (bench / 'index.jsonl').read_text().splitlines()]
        wanted = [json.loads(s) for s in (plan / ('remaining.jsonl' if args.client else 'all.jsonl')).read_text().splitlines()]
        n = np.array([r['n_tokens'] for r in rows])
        seconds = np.array([r['total_seconds'] for r in rows])
        features = lambda v: np.column_stack([np.ones(len(v)), v / 1000, (v / 1000) ** 2])
        coef, _ = nnls(features(n), seconds)
        target = np.array([r['n_tokens'] for r in wanted])
        estimated = max(float((features(target) @ coef).sum()), float(seconds.sum() * target.sum() / n.sum()))
        startup = 120 if args.client else 240
        upper_seconds = estimated * 1.25 + startup
        prior = json.loads((ROOT / 'runs' / args.client / 'summary.json').read_text())['conservative_compute_upper_usd'] if args.client else 0
        total = prior + upper_seconds * .00090 + .50
        result = dict(requests=len(wanted), prompt_tokens=int(target.sum()),
                      coefficients=coef.tolist(), projected_processing_seconds=estimated,
                      conservative_future_seconds=upper_seconds, prior_compute_upper_usd=prior,
                      overhead_allowance_usd=.50, conservative_total_usd=total, cap_usd=7,
                      proceed=total <= 7, future_phase_ceiling_usd=6.50-prior)
        (run.dir / 'projection.json').write_text(json.dumps(result, indent=2))
        run.result(**result)
        run.finish()
        print(json.dumps(result, indent=2))
        print('PROJECTION_RUN', run.id)
    except BaseException as exc:
        run.finish('failed', str(exc))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', required=True)
    parser.add_argument('--benchmark', default='20261024-1727-e02-activation-replay')
    parser.add_argument('--client')
    main(parser.parse_args())
