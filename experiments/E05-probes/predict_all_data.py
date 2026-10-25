"""Apply a full-data deployable probe to saved last-prompt-token activations."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np


def predict(run, activations, label, seed, fixed32=False):
    directory=Path(run)/label/'deploy'/f's{seed}-f0'
    layer=32 if fixed32 else json.loads((directory/'fit.json').read_text())['layer']
    x=np.asarray(activations)
    if x.ndim==2:x=x[None,:,:]
    if x.ndim!=3 or x.shape[1:]!=(64,5120):
        raise ValueError('Expected [requests,64,5120] or [64,5120] E02 residual activations')
    with np.load(directory/f'lr-l{layer}.npz') as model:
        value=((np.asarray(x[:,layer],dtype=float)-model['mean'])/model['scale'])@model['coef'][0]+model['intercept'][0]
    if not np.isfinite(value).all():raise ValueError('Nonfinite probe scores')
    return dict(label_variant=label,seed=seed,layer=layer,method='fixed32' if fixed32 else 'nested',scores=value.tolist())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('activations',type=Path)
    p.add_argument('--label',default='A_hazard',choices=['eventual','A_hazard','B_round_contrast','C_step_contrast'])
    p.add_argument('--seed',type=int,default=42,choices=[42,43,44]);p.add_argument('--fixed32',action='store_true')
    a=p.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
    from collusion.runs import start_run
    run=start_run('e05-probe-prediction',experiment='E05',parents=[a.run.name],settings=dict(
        activations=str(a.activations.resolve()),label=a.label,seed=a.seed,fixed32=a.fixed32))
    try:
        result=predict(a.run,np.load(a.activations,mmap_mode='r'),a.label,a.seed,a.fixed32)
        (run.dir/'scores.json').write_text(json.dumps(result)+'\n')
        run.result(rows=len(result['scores']),layer=result['layer']);run.finish();print('PREDICTION_RUN',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise
