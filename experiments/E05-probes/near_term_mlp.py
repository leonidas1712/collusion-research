"""Two-thread CPU MLP comparison on the exact saved near-term splits."""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS'):
    os.environ[name]='2'
import argparse
import csv
import json
import sys
import time
from pathlib import Path
import numpy as np
import torch
from threadpoolctl import threadpool_limits
from data import ROOT, CANDIDATES
from near_term import label_rows, saved_splits, check_split, DATA, FIT, SEEDS
from replay2_models import fit_mlp, score_mlp, save_mlp, MLP_SETTINGS
from metrics import within_round
from evaluate import ranking_summary, score_bootstrap, finite_mean, interval
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run, Run, write_json_atomic

NEAR='20261025-0730-e05-near-term'
VARIANTS=('B_round_contrast','A_hazard')
MODES=('pooled','loso')


def inputs():
    rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
    labels={v:label_rows(rows,v) for v in VARIANTS}
    saved_labels=[json.loads(s) for s in (ROOT/'runs'/NEAR/'labels.jsonl').read_text().splitlines()]
    for v,(keep,y) in labels.items():
        reference=[r for r in saved_labels if r['label_variant']==v]
        assert len(reference)==len(rows)
        for r in reference:
            i=r['row'];assert r['request_sha256']==rows[i]['request_sha256']
            assert bool(r['included'])==bool(keep[i])
            if keep[i]:assert r['label']==y[i]
    cases=[]
    for v in VARIANTS:
        keep,y=labels[v]
        for mode in MODES:
            notes=json.loads((ROOT/'runs'/FIT/mode/'folds.json').read_text())
            for note in notes:
                split,_=saved_splits(rows,mode,note,keep);check_split(rows,y,split)
                with np.load(ROOT/'runs'/NEAR/v/mode/f"s{note['seed']}-f{note['fold']}"/'scores.npz') as old:
                    for k,values in split.items():assert np.array_equal(values,old[k])
                cases.append((v,mode,note['seed'],note['fold'],split))
    reference={};columns=None
    with (ROOT/'runs'/NEAR/'probe_scores.csv').open() as file:
        reader=csv.DictReader(file);columns=reader.fieldnames
        for r in reader:
            if r['label_variant'] not in VARIANTS or r['method']!='nested':continue
            i=int(r['row']);v=r['label_variant'];keep,y=labels[v]
            assert keep[i] and int(r['label'])==y[i]
            assert r['request_sha256']==rows[i]['request_sha256']
            key=(v,r['analysis'],int(r['seed']),i);assert key not in reference
            reference[key]=r
    for v,mode,seed,fold,split in cases:
        with np.load(ROOT/'runs'/NEAR/v/mode/f's{seed}-f{fold}'/'scores.npz') as old:
            for j,i in enumerate(split['test']):
                r=reference[v,mode,seed,int(i)]
                assert int(r['fold'])==fold and float(r['score'])==old['nested'][j]
    assert len(reference)==sum(len(s['test']) for _,_,_,_,s in cases)
    return rows,labels,cases,reference,columns


def reconstruct(path,x):
    with np.load(path) as m:
        z=((np.asarray(x,dtype=np.float64)-m['mean'])/m['scale']).astype('float32')
        return (np.maximum(z@m['w1'].T+m['b1'],0)@m['w2'].T+m['b2']).ravel()


def fit_case(directory,rows,x,y,seed,fold,split):
    directory.mkdir(parents=True,exist_ok=True)
    rounds=np.array([r['round'] for r in rows]);tr=split['inner_train'];va=split['inner_validation']
    path=directory/'selection.json';selection=json.loads(path.read_text()) if path.exists() else {}
    for layer in CANDIDATES:
        if str(layer) in selection:continue
        model=fit_mlp(x[tr,layer],y[tr],rounds[tr],seed+fold,threads=2)
        values=score_mlp(model,x[va,layer])
        a=within_round(y[va],values,rounds[va],stratum_key=[rows[i]['scenario'] for i in va])[0]
        assert np.isfinite(a)
        selection[str(layer)]={'auc':a,'final_loss':model[2][-1]}
        np.savez_compressed(directory/f'inner-l{layer}.npz',validation=va,scores=values)
        write_json_atomic(path,selection)
    layer=max(CANDIDATES,key=lambda k:(selection[str(k)]['auc'],-k))
    model=fit_mlp(x[split['train'],layer],y[split['train']],rounds[split['train']],seed+fold,threads=2)
    values=score_mlp(model,x[split['test'],layer]);save_mlp(directory/'model.npz',model)
    check=reconstruct(directory/'model.npz',x[split['test'],layer])
    assert np.allclose(check,values,rtol=1e-4,atol=1e-4)
    np.savez_compressed(directory/'scores.npz',**split,mlp=values,y_test=y[split['test']],layer=layer)
    write_json_atomic(directory/'fit.json',{'layer':layer,'seed':seed+fold,'max_reconstruction_error':float(np.max(np.abs(check-values))),
        'epochs':len(model[2]),'threads':torch.get_num_threads(),'final_loss':model[2][-1]})


def paired_metrics(rows,ids,y,predictions,folds,reps):
    rounds=np.array([rows[i]['round'] for i in ids]);scenarios=[rows[i]['scenario'] for i in ids]
    families=np.array([rows[i]['family'] for i in ids]);names,codes=np.unique(families,return_inverse=True)
    weights=np.random.default_rng(20261024).multinomial(len(names),np.ones(len(names))/len(names),size=reps).astype(float)
    results={};boots={}
    for method,scores in predictions.items():
        summary,boot,_=ranking_summary(np.tile(y[ids],(3,1)),scores,rounds,families,reps,stratum_key=scenarios)
        vals=[];bs=[];coverage=[]
        for si,s in enumerate(scores):
            strata=[(scenario,int(fold)) for scenario,fold in zip(scenarios,folds[si])]
            a,d=within_round(y[ids],s,rounds,stratum_key=strata)
            b,_=score_bootstrap(y[ids],s,rounds,codes,weights,stratum_key=strata)
            vals.append(a);bs.append(b);coverage.append(d['positive_coverage'])
        sensitivity=finite_mean(bs,axis=0)
        summary['fold_sensitivity']={'auc':float(finite_mean(vals)),'ci95':interval(sensitivity),'by_seed':vals,'positive_coverage_by_seed':coverage}
        results[method]=summary;boots[method]=(boot,sensitivity)
    differences={}
    for j,key in enumerate(('scenario_round','fold_sensitivity')):
        delta=boots['mlp'][j]-boots['nested'][j]
        point=lambda m:results[m]['within_round_auc'] if j==0 else results[m]['fold_sensitivity']['auc']
        differences[key]={'mean':point('mlp')-point('nested'),'paired_family_ci95':interval(delta),'valid_bootstrap_reps':int(np.isfinite(delta).sum())}
    return {'rows':len(ids),'positives':int(y[ids].sum()),'methods':results,'mlp_minus_nested':differences}


def summarize(run,rows,labels,cases,reference,columns,reps):
    metrics={};count=0
    with (run.dir/'probe_scores.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=columns);writer.writeheader()
        for v in VARIANTS:
            keep,y=labels[v];ids=np.flatnonzero(keep)
            for mode in MODES:
                pred={m:np.full((3,len(rows)),np.nan) for m in ('mlp','nested')};folds=np.full((3,len(rows)),-1,dtype=int)
                for variant,analysis,seed,fold,split in cases:
                    if (variant,analysis)!=(v,mode):continue
                    si=SEEDS.index(seed)
                    with np.load(run.dir/v/mode/f's{seed}-f{fold}'/'scores.npz') as data:
                        for k in split:assert np.array_equal(split[k],data[k])
                        assert np.array_equal(y[split['test']],data['y_test'])
                        for j,i in enumerate(split['test']):
                            r=reference[v,mode,seed,int(i)]
                            assert folds[si,i]==-1;folds[si,i]=fold
                            pred['mlp'][si,i]=data['mlp'][j];pred['nested'][si,i]=float(r['score'])
                assert (folds[:,ids]>=0).all()
                assert all(np.isfinite(values[:,ids]).all() for values in pred.values())
                for method,values in pred.items():
                    for si,seed in enumerate(SEEDS):
                        for i in ids:
                            r=dict(reference[v,mode,seed,int(i)]);r.update(method=method,score=float(values[si,i]))
                            writer.writerow(r);count+=1
                np.savez_compressed(run.dir/v/mode/'predictions.npz',**pred,folds=folds,eligible=ids,y=y,seeds=SEEDS)
                metrics[f'{v}/{mode}']=paired_metrics(rows,ids,y,{m:s[:,ids] for m,s in pred.items()},folds[:,ids],reps)
                write_json_atomic(run.dir/'metrics.json',metrics)
    lines=['# Near-term MLP versus nested logistic','',
        'Exploratory CPU-only comparison; two threads, memory-mapped activations, no paid calls or GPU. Exact saved outer and inner splits are filtered by the original near-term A/B memberships. MLP layer selection uses only inner validation over layers 0,4,…,60,63 (ties choose the lower layer). Final models refit on all outer-training rows. Both inner and final MLP seeds equal outer seed + fold, matching replay2_core.py.','',
        'Recipe unchanged: training-only StandardScaler; round-balanced weights; one 32-unit ReLU layer; AdamW learning rate .001, weight decay .01; batch size 256; 80 epochs. No tuning using test rows. Nested logistic scores are copied from the existing near-term CSV and checked against its saved fold scores.','',
        f'Primary metric is scenario × round AUROC; sensitivity adds fold. Paired 95% CIs use {reps} identical family-bootstrap resamples for both methods and all three seeds, then subtract seed-averaged AUROCs. Intervals condition on fixed splits/fits. Single-class strata are omitted; coverage is in metrics.json. B uses outcome hindsight to remove earlier give-in steps; A retains those as negatives. Neither contrast is a prospective deployment estimate.','',
        '| Label | Analysis | Rows (+) | MLP primary [CI] | Logistic primary [CI] | Paired MLP − LR [CI] | Fold-stratified difference [CI] |',
        '| --- | --- | ---: | --- | --- | --- | --- |']
    def fmt(value,ci):return f'{value:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]'
    for key,r in metrics.items():
        v,mode=key.split('/');m=r['methods'];d=r['mlp_minus_nested']
        lines.append(f"| {v} | {mode} | {r['rows']} ({r['positives']}) | "+' | '.join([
            fmt(m[k]['within_round_auc'],m[k]['within_round_ci95']) for k in ('mlp','nested')]+[
            fmt(d[k]['mean'],d[k]['paired_family_ci95']) for k in ('scenario_round','fold_sensitivity')])+' |')
    lines+=['',f'OOF export: {count} rows, original CSV schema; methods mlp and nested. Per-fold selection.json, inner validation scores, model.npz, scores.npz and fit.json preserve selection and reconstruction evidence. metrics.json contains all metric and coverage details.','',
            f'Inputs: {DATA}; {FIT} (saved splits); {NEAR} (labels, filtered splits and nested logistic scores).']
    (run.dir/'report.md').write_text('\n'.join(lines)+'\n')
    return metrics,count


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path);parser.add_argument('--preflight',action='store_true');parser.add_argument('--reps',type=int,default=1000);args=parser.parse_args()
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    with threadpool_limits(limits=2):
        rows,labels,cases,reference,columns=inputs()
        preflight={'cases':len(cases),'reference_rows':len(reference),'labels':{v:{'rows':int(k.sum()),'positives':int(y[k].sum())} for v,(k,y) in labels.items()},'threads':2,'exact_saved_splits':True}
        print('PREFLIGHT',json.dumps(preflight),flush=True)
        if args.preflight:return
        if args.run:
            directory=args.run.resolve();meta=json.loads((directory/'meta.json').read_text());meta.update(status='running',error=None);run=Run(directory.name,directory,meta)
        else:run=start_run('e05-near-term-mlp',experiment='E05',parents=[DATA,FIT,NEAR],settings={'threads':2,'variants':VARIANTS,'mlp':MLP_SETTINGS,'candidates':CANDIDATES,'seeds':SEEDS,'bootstrap_reps':args.reps,'paid_cost_usd':0})
        write_json_atomic(run.dir/'preflight.json',preflight)
        x=np.load(ROOT/'runs'/DATA/'features.npy',mmap_mode='r');assert isinstance(x,np.memmap)
        try:
            for v,mode,seed,fold,split in cases:
                dest=run.dir/v/mode/f's{seed}-f{fold}';started=time.perf_counter()
                if not (dest/'fit.json').exists():fit_case(dest,rows,x,labels[v][1],seed,fold,split)
                print('FIT_CASE',v,mode,seed,fold,round(time.perf_counter()-started,1),flush=True)
            results,count=summarize(run,rows,labels,cases,reference,columns,args.reps)
            run.result(cases=len(cases),exported=count,paid_cost_usd=0);run.finish();print('MLP_RUN',run.dir,flush=True)
        except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':main()
