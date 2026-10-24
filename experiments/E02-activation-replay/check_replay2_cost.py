"""Project running cost after separating fixed startup from per-request work."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import nnls
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run

def main(args):
    run=start_run('e02-replay2-cost-check',experiment='E02',parents=[args.remote, '20261025-0119-e02-replay2-plan'],settings={'cap_usd':12,'safety_factor':1.25,'max_rate':.00090})
    try:
        def read(name):
            destination=run.dir/('download-'+name)
            subprocess.run(['modal','volume','get','collusion-activations',f'runs/{args.remote}/{name}',str(destination)],check=True,capture_output=True,text=True)
            return destination.read_text()
        raw=read('index.jsonl');progress=json.loads(read('progress.json'));(run.dir/'index-snapshot.jsonl').write_text(raw);(run.dir/'progress.json').write_text(json.dumps(progress,indent=2))
        rows=[json.loads(s) for s in raw.splitlines()];manifest=[json.loads(s) for s in (ROOT/'runs/20261025-0119-e02-replay2-plan/remaining.jsonl').read_text().splitlines()]
        key=lambda r:(r['run_id'],Path(r['episode_file']).name,r['request_idx']);seen={key(r) for r in rows};remaining=[r for r in manifest if key(r) not in seen]
        n=np.array([r['n_tokens'] for r in rows]);seconds=np.array([r['total_seconds'] for r in rows]);coef,_=nnls(np.column_stack([np.ones(len(n)),n/1000,(n/1000)**2]),seconds)
        rn=np.array([r['n_tokens'] for r in remaining]);estimate=float((np.column_stack([np.ones(len(rn)),rn/1000,(rn/1000)**2])@coef).sum());token_linear=float(seconds.sum()*rn.sum()/n.sum())
        fixed=max(0,progress['wall_seconds']-sum(r['total_seconds'] for r in rows[:progress['requests']]))
        future=max(estimate,token_linear)*1.25;total_seconds=max(progress['wall_seconds'],fixed+sum(seconds))+future
        total=.089208+.50+total_seconds*.00090
        result=dict(processed=len(rows),remaining=len(remaining),fixed_startup_and_unattributed_seconds=fixed,coefficients=coef.tolist(),projected_remaining_seconds=estimate,conservative_remaining_seconds=future,conservative_total_usd=total,cap_usd=12,proceed=total<=12)
        (run.dir/'result.json').write_text(json.dumps(result,indent=2));run.result(**result);run.finish();print(json.dumps(result,indent=2))
        if total>12:
            subprocess.run(['modal','app','stop',args.app],check=True)
            raise SystemExit('Stopped: conservative projected total exceeds USD12')
    except Exception as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--remote',required=True);p.add_argument('--app',required=True);main(p.parse_args())
