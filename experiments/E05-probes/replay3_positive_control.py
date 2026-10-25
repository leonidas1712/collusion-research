"""Replay3 fixed-layer32 token-exposure gate with replay2 family split and model."""
import argparse
import json
import sys
import numpy as np
from threadpoolctl import threadpool_limits
from data import ROOT
from models import fit_logistic,score
from metrics import auc
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run

def main(args):
    source=ROOT/'runs'/args.data_run;rows=[json.loads(s) for s in (source/'rows.jsonl').read_text().splitlines()];x=np.load(source/'features.npy',mmap_mode='r')
    run=start_run('e05-replay3-positive-control',experiment='E05',parents=[args.data_run],settings={'gate_layer':32,'minimum_auc':.95,'seed':42,'family_holdout':.3,'curve_layers':[32],'C':.1})
    try:
        indices=np.array([i for i,r in enumerate(rows) if r['valid'] and not r['shared_branch_history']]);families=np.array([r['family'] for r in rows]);unique=np.unique(families[indices]);shuffled=np.random.default_rng(42).permutation(unique);held=set(shuffled[:int(np.ceil(len(unique)*.3))]);test=indices[np.isin(families[indices],list(held))];train=indices[~np.isin(families[indices],list(held))]
        assert not set(families[train])&set(families[test]);y=np.array([r['token_in_context'] for r in rows],dtype=int);assert len(set(y[test]))==len(set(y[train]))==2
        values=[];pred=np.full((64,len(rows)),np.nan)
        with threadpool_limits(limits=4):
            for layer in [32]:
                model=fit_logistic(x[train,layer],y[train]);s=score(model,x[test,layer]);metric=auc(y[test],s);pred[layer,test]=s
                values.append(dict(layer=layer,auc=metric));write_json(run.dir/'curve.json',sorted(values,key=lambda r:r['layer']))
                print('EXPOSURE',layer,metric,flush=True)
                if layer==32 and metric<.95:raise RuntimeError(f'Integrity gate failed: layer32 exposure AUROC {metric} < .95')
        np.savez_compressed(run.dir/'predictions.npz',scores=pred,train=train,test=test,y=y)
        write_json(run.dir/'split.json',{'train_families':sorted(set(families[train])),'test_families':sorted(held),'train_rows':len(train),'test_rows':len(test),'test_episodes':len({rows[i]['episode'] for i in test})})
        result=dict(gate_passed=True,gate_layer=32,gate_auc=next(v['auc'] for v in values if v['layer']==32),min_auc=min(v['auc'] for v in values),test_rows=len(test),curve=sorted(values,key=lambda r:r['layer']))
        write_json(run.dir/'summary.json',result);run.result(**result);run.finish();print('CONTROL_RUN',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('data_run');main(p.parse_args())
