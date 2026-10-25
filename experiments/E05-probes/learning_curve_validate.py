"""Audit learning-curve subsets, serialized models and reuse of full-data scores."""
import argparse
import json
import sys
import numpy as np
from threadpoolctl import threadpool_limits
from learning_curve import ROOT,DATA,FIT,LABELS,MODES,SEEDS,FRACTIONS,labels
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run


def main(args):
    source=ROOT/'runs'/args.run
    run=start_run('e05-learning-curve-validation',experiment='E05',parents=[args.run,DATA,FIT,args.near_run],settings={'no_refits':True})
    try:
        rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
        x=np.load(ROOT/'runs'/DATA/'features.npy',mmap_mode='r')
        plan=json.loads((source/'sampling_plan.json').read_text());errors=[];count=0
        with threadpool_limits(limits=2):
            for case in plan:
                if case['fraction']==1:continue
                name,mode=case['label_variant'],case['analysis'];seed,fold,draw=case['seed'],case['fold'],case['draw']
                path=source/name/mode/f"s{seed}-f{fold}-d{draw}-p{int(case['fraction']*100)}"
                note=json.loads((path/'fit.json').read_text())
                with np.load(path/'predictions.npz') as d:
                    for key in ('train','test','inner_train','inner_validation'):assert np.array_equal(d[key],case[key])
                    train,test=d['train'],d['test']
                    assert {rows[i]['family'] for i in train}==set(case['train_families'])
                    assert not {rows[i]['family'] for i in train}&{rows[i]['family'] for i in test}
                    with np.load(source/name/mode/f"curve-p{int(case['fraction']*100)}.npz") as aggregate:
                        slot=SEEDS.index(seed)*3+draw
                        for method,layer in [('nested',note['chosen_layer']),('fixed32',32)]:
                            assert np.array_equal(aggregate[method][slot,test],d[method])
                            with np.load(path/f'lr-l{layer}.npz') as model:
                                pred=((np.asarray(x[test,layer],dtype=float)-model['mean'])/model['scale'])@model['coef'][0]+model['intercept'][0]
                            error=float(np.max(np.abs(pred-d[method])));assert error<1e-9;errors.append(error)
                count+=1
            for name in LABELS:
                keep,y=labels(rows,name);ids=np.flatnonzero(keep)
                for mode in MODES:
                    origin=ROOT/'runs'/(FIT if name=='eventual' else args.near_run)
                    if name!='eventual':origin=origin/name
                    with np.load(origin/mode/'predictions.npz') as old, np.load(source/name/mode/'curve-p100.npz') as curve:
                        for method in ('nested','fixed32'):
                            for si in range(3):
                                for draw in range(3):assert np.array_equal(curve[method][si*3+draw,ids],old[method][si,ids])
                    for fraction in FRACTIONS:
                        with np.load(source/name/mode/f'curve-p{int(fraction*100)}.npz') as d:
                            assert np.array_equal(d['eligible'],ids) and np.array_equal(d['y'],y)
                            for method in ('nested','fixed32'):assert np.isfinite(d[method][:,ids]).all()
        result=dict(subset_fits=count,max_reconstruction_error=max(errors),full_data_scores_reused_exactly=True,
                    subset_and_aggregate_predictions_exact=True,no_family_leakage=True)
        write_json(run.dir/'summary.json',result);run.result(**result);run.finish();print('CURVE_VALIDATION',run.id,result)
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('near_run');main(p.parse_args())
