"""Project the remaining approved replay from measured benchmark request timings."""
import json
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import nnls
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run

plan='20261025-0119-e02-replay2-plan';bench='20261024-1721-e02-activation-replay';client='20261025-0121-e02-replay2-modal-client';validation='20261025-0126-e02-main-replay-validation'
run=start_run('e02-replay2-projection',experiment='E02',parents=[plan,bench,client,validation],settings={'approval':'author-approved USD12 replay budget','price_source':'https://modal.com/pricing','max_resource_rate_usd_sec':.00090,'safety_multiplier':1.25})
try:
    rows=[json.loads(s) for s in (ROOT/'runs'/bench/'index.jsonl').read_text().splitlines()]
    remaining=[json.loads(s) for s in (ROOT/'runs'/plan/'remaining.jsonl').read_text().splitlines()]
    n=np.array([r['n_tokens'] for r in rows]);seconds=np.array([r['total_seconds'] for r in rows]);x=np.column_stack([np.ones(len(n)),n/1000,(n/1000)**2]);coef,_=nnls(x,seconds)
    rn=np.array([r['n_tokens'] for r in remaining]);estimate=np.column_stack([np.ones(len(rn)),rn/1000,(rn/1000)**2])@coef
    linear=sum(seconds)*sum(rn)/sum(n);upper=max(float(estimate.sum()),float(linear))*1.25+120
    prior=json.loads((ROOT/'runs'/client/'summary.json').read_text())['conservative_compute_upper_usd']
    output_bytes_per_request=sum((ROOT/'runs'/bench/r['artifact']).stat().st_size for r in rows)/len(rows)
    network_allowance=(output_bytes_per_request*(len(rows)+len(remaining))*1.5)/2**30*.04
    total=prior+upper*.00090+network_allowance+.20
    result=dict(benchmark_requests=len(rows),remaining_requests=len(remaining),remaining_prompt_tokens=int(sum(rn)),nnls_seconds_coefficients=coef.tolist(),
        measured_prompt_tokens_per_processing_second=float(sum(n)/sum(seconds)),projected_remaining_seconds=float(estimate.sum()+60),
        conservative_remaining_seconds=upper,benchmark_compute_upper_usd=prior,network_allowance_usd=network_allowance,misc_allowance_usd=.20,
        conservative_total_usd=total,approved_cap_usd=12,proceed=total<=12,benchmark_nll=json.loads((ROOT/'runs'/validation/'summary.json').read_text())['weighted_nll'])
    (run.dir/'projection.json').write_text(json.dumps(result,indent=2));run.result(**result);run.finish();print(json.dumps(result,indent=2));print('PROJECTION_RUN',run.id)
    if not result['proceed']:raise SystemExit('Projected cap exceeded; no main replay authorized by this gate')
except Exception as exc:run.finish('failed',str(exc));raise
