"""Exploratory fixed-layer trajectory and pressure probes; CPU only, two threads."""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS'):
    os.environ[name] = '2'
import argparse
import csv
import json
import sys
import time
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits, threadpool_info
from data import ROOT
from models import fit_logistic, score
from metrics import within_round
from evaluate import ranking_summary, score_bootstrap, finite_mean, interval
from explore_features import LAYERS, extract
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run, Run, write_json_atomic

DATA='20261025-0337-e05-replay2-data'
FOLDS='20261025-0240-e05-replay2-folds'
FIT='20261025-0340-e05-replay2-fits'
NEAR='20261025-0730-e05-near-term'
SEEDS=(42,43,44)
METHODS=[f'{kind}_l{layer}' for kind in ('delta','scalar') for layer in LAYERS]


def load_inputs():
    rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
    ref=[json.loads(s) for s in (ROOT/'runs'/FOLDS/'rows.jsonl').read_text().splitlines()]
    assert len(rows)==len(ref)
    for a,b in zip(rows,ref):
        for k in ('episode','request_idx','request_sha256','prompt_sha256','eligible','family','label'):
            assert a[k]==b[k],(a['index'],k)
    eligible=np.load(ROOT/'runs'/FOLDS/'eligible.npy')
    assert np.array_equal(eligible,np.flatnonzero([r['eligible'] for r in rows]))
    near=np.full(len(rows),-1,dtype=int)
    seen=set()
    for line in (ROOT/'runs'/NEAR/'labels.jsonl').read_text().splitlines():
        r=json.loads(line)
        if r['label_variant']!='A_hazard':continue
        i=r['row']; assert i not in seen;seen.add(i)
        assert r['row_id']==rows[i]['episode']+'::request_idx='+str(rows[i]['request_idx'])
        assert r['request_sha256']==rows[i]['request_sha256']
        if r['included']:near[i]=r['label']
    assert len(seen)==len(rows)
    assert np.array_equal(np.flatnonzero(near>=0),np.array([i for i in eligible if rows[i]['condition']=='recruiting']))
    return rows,eligible,near


def cases(rows,eligible):
    pooled=json.loads((ROOT/'runs'/FOLDS/'folds.json').read_text())
    result=[]
    for note in pooled:
        result.append(dict(mode='pooled',seed=note['seed'],fold=note['fold'],
                           train=np.array(note['train_indices']),cal=np.array(note['calibration_indices']),test=np.array(note['test_indices'])))
    for note in json.loads((ROOT/'runs'/FIT/'loso/folds.json').read_text()):
        with np.load(ROOT/'runs'/FIT/'loso'/f"split-s{note['seed']}-f{note['fold']}.npz") as d:
            result.append(dict(mode='loso',seed=note['seed'],fold=note['fold'],
                               train=d['train'],cal=d['calibration'],test=d['test']))
    for c in result:
        train=set(c['train']);cal=set(c['cal']);test=set(c['test'])
        assert not train&cal and not (train|cal)&test
        assert not {rows[i]['family'] for i in train|cal}&{rows[i]['family'] for i in test}
        assert all(rows[i]['condition']=='recruiting' for i in train)
        assert all(rows[i]['condition'] in ('control','alone') for i in cal)
        assert train|cal|test <= set(eligible)
    for mode in ('pooled','loso'):
        for seed in SEEDS:
            test=np.concatenate([c['test'] for c in result if c['mode']==mode and c['seed']==seed])
            assert np.array_equal(np.sort(test),eligible)
    return result


def fit_one(x,y,train,test,rounds,seed,path):
    model=fit_logistic(x[train],y[train],rounds[train],seed)
    values=score(model,x[test]);scaler,clf=model
    np.savez_compressed(path,mean=scaler.mean_,scale=scaler.scale_,coef=clf.coef_,intercept=clf.intercept_,
                        train=train,test=test,scores=values)
    # Independently reconstruct a few scores from persisted coefficients/scaling.
    with np.load(path) as saved:
        sample=np.asarray(x[test[:4]],dtype=np.float64)
        reconstructed=((sample-saved['mean'])/saved['scale'])@saved['coef'][0]+saved['intercept'][0]
        assert np.allclose(reconstructed,values[:4],rtol=1e-7,atol=1e-7)
    return values


def summarize(rows,ids,y,scores,folds,reps):
    rounds=np.array([rows[i]['round'] for i in ids]);scenarios=[rows[i]['scenario'] for i in ids]
    families=np.array([rows[i]['family'] for i in ids]);names,codes=np.unique(families,return_inverse=True)
    weights=np.random.default_rng(20261024).multinomial(len(names),np.ones(len(names))/len(names),size=reps).astype(float)
    summary,_,_=ranking_summary(np.tile(y[ids],(3,1)),scores,rounds,families,reps,stratum_key=scenarios)
    estimates=[];boots=[];coverage=[]
    for si,s in enumerate(scores):
        strata=[(scenario,int(fold)) for scenario,fold in zip(scenarios,folds[si,ids])]
        value,detail=within_round(y[ids],s,rounds,stratum_key=strata)
        boot,_=score_bootstrap(y[ids],s,rounds,codes,weights,stratum_key=strata)
        estimates.append(value);boots.append(boot);coverage.append(detail['positive_coverage'])
    boot=finite_mean(boots,axis=0)
    summary.update(rows=len(ids),positives=int(y[ids].sum()),episodes=len(set(rows[i]['episode'] for i in ids)),
                   positive_episodes=len(set(rows[i]['episode'] for i in ids if y[i])),
                   fold_sensitivity={'auc':float(finite_mean(estimates)),'ci95':interval(boot),
                                     'by_seed':estimates,'positive_coverage_by_seed':coverage,
                                     'valid_bootstrap_reps':int(np.isfinite(boot).sum())})
    return summary


def finish_outputs(run,rows,eligible,near,reps):
    eventual=np.array([r['label'] for r in rows]);pressure=np.array([r['condition']=='recruiting' for r in rows],dtype=int)
    metrics={};exported=0
    fields=['row_id','step_id','row','analysis','seed','fold','score','method','episode','request_idx',
            'request_sha256','condition','scenario','round','label','label_variant']
    with (run.dir/'probe_scores.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=fields);writer.writeheader()
        for mode in ('pooled','loso'):
            with np.load(run.dir/f'{mode}-predictions.npz') as data:
                folds=data['folds']; ids=data['eligible']
                for variant,y in [('eventual',eventual),('A_hazard',near),('pressure',pressure)]:
                    head=ids if variant=='pressure' else ids[[rows[i]['condition']=='recruiting' for i in ids]]
                    methods=['pressure_l32'] if variant=='pressure' else METHODS+['pressure_l32']
                    for method in methods:
                        key=f'{variant}__{method}' if method!='pressure_l32' else 'pressure_l32'
                        values=data[key]
                        result=summarize(rows,head,y,values[:,head],folds,reps)
                        metrics[f'{mode}/{variant}/{method}']=result
                        write_json_atomic(run.dir/'metrics.json',metrics)
                        for si,seed in enumerate(SEEDS):
                            export_ids=head if variant!='eventual' else ids
                            for i in export_ids:
                                r=rows[i];rid=r['episode']+'::request_idx='+str(r['request_idx'])
                                writer.writerow(dict(row_id=rid,step_id=rid,row=int(i),analysis=mode,seed=seed,
                                    fold=int(folds[si,i]),score=float(values[si,i]),method=method,label=int(y[i]),label_variant=variant,
                                    **{k:r[k] for k in ('episode','request_idx','request_sha256','condition','scenario','round')}))
                                exported+=1
                        print('METRIC',mode,variant,method,round(result['within_round_auc'],4),flush=True)
    def fmt(value,ci):
        return f"{value:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]" if ci else f'{value:.3f} [unavailable]'
    lines=['# Exploratory trajectory and pressure probes','',
        'CPU-only; $0 paid compute/API; sequential fits with two-thread numerical libraries. Input features.npy was opened with mmap_mode=r. These are exploratory, fixed-layer analyses, without selecting a winning layer or method on the reported outcomes.','',
        'Trajectory features at each of layers 24/32/40: current minus immediately preceding available request activation from the same episode; scalar vector = [L2 of that difference, L2 distance from the first post-read activation, 1−cosine(current, previous)]. First post-read means token_in_context and ordinal > first_read. That first post-read step uses itself as anchor (distance zero); its previous step can be pre-read. No future step or disclosure-time alignment enters feature extraction. Only original eligible current rows enter fitting/scoring.','',
        'Logistic recipe: original E05 fit_logistic, C=0.1, lbfgs, round-balanced training weights and training-only standardization; no layer selection. Outcome fits use recruiting training rows, with the original eventual label or supplied A_hazard label (disclosure in the current or next round, before action). Pressure fits use layer32 absolute activations and recruiting=1 vs control/alone=0, trained on the outer-training recruiting plus benign-calibration rows; no test families and no threshold calibration. The same pressure scores are evaluated against eventual and A labels only among recruiting test steps, without refitting or reversing their sign.','',
        'Exact 15 pooled split records are reused from the exported folds.json. Exact 18 LOSO saved split files are reused (six scenario rotations × three seeds, shared test families purged). Rows/hashes match the export. A membership filters those assignments; no splitting is redone.','',
        f'Primary metric: E05 metrics.within_round with scenario stratum, averaged across seeds42/43/44. Sensitivity: fold × scenario × round within each seed, then average. CIs use {reps} shared family-bootstrap resamples, conditional on fixed fits/splits. Single-class strata are omitted; positive coverage, per-seed values and valid bootstrap counts are in metrics.json. Sensitivity may compare a different subset of positive rows. No multiplicity correction or confirmatory claims.','',
        '| Analysis | Label evaluated | Probe | Rows (+) | Scenario × round AUROC [95% CI] | Fold × scenario × round [95% CI] |',
        '| --- | --- | --- | ---: | --- | --- |']
    for key,r in metrics.items():
        mode,variant,method=key.split('/');s=r['fold_sensitivity']
        lines.append(f"| {mode} | {variant} | {method} | {r['rows']} ({r['positives']}) | {fmt(r['within_round_auc'],r['within_round_ci95'])} | {fmt(s['auc'],s['ci95'])} |")
    lines+=['','## Files','',
        '- probe_scores.csv: reference export columns plus label_variant; key = (row_id, analysis, seed, method, label_variant). Eventual scores include held-out benign rows; A contains recruiting rows; pressure classification contains both. Scores are raw logistic decisions. No thresholds are estimated.',
        '- pooled-predictions.npz and loso-predictions.npz: all OOF arrays, eligibility and fold indices.',
        '- fits/: coefficients, scaler parameters, exact training/test row indices and test scores for every fitted model.',
        '- delta.npy, scalar.npy, trajectory_links.npz: causal features, predecessor/anchor indices and coverage.',
        '- preflight.json and audit.json: source identity/family separation, feature coverage, persisted-score reconstruction and CSV checks.',
        f'- Parents: {DATA}, {FOLDS}, {FIT} (LOSO splits only), {NEAR} (A labels only).','',
        'Pressure is a condition-discrimination diagnostic, not a measurement of a specific persuasion tactic or causal pressure. Trajectory magnitudes can reflect context length, read/tool transitions and episode progress. First post-read deltas may primarily detect exposure; these analyses do not establish an internal decision time.']
    (run.dir/'report.md').write_text('\n'.join(lines)+'\n')
    return metrics,exported


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path);parser.add_argument('--reps',type=int,default=1000);args=parser.parse_args()
    rows,eligible,near=load_inputs();split_cases=cases(rows,eligible)
    if args.run:
        directory=args.run.resolve();meta=json.loads((directory/'meta.json').read_text())
        history_path=directory/'resume_history.json'
        history=json.loads(history_path.read_text()) if history_path.exists() else []
        history.append({'previous_meta':meta.copy(),'command':sys.argv})
        write_json_atomic(history_path,history)
        meta.update(status='running',error=None)
        write_json_atomic(directory/'meta.json',meta)
        run=Run(directory.name,directory,meta)
    else:
        run=start_run('e05-explore-trajectories-pressure',experiment='E05',parents=[DATA,FOLDS,FIT,NEAR],
                      settings={'threads':2,'layers':LAYERS,'C':.1,'seeds':SEEDS,'bootstrap_reps':args.reps,'exploratory':True,'paid_cost_usd':0})
    try:
        with threadpool_limits(limits=2):
            x=np.load(ROOT/'runs'/DATA/'features.npy',mmap_mode='r');assert isinstance(x,np.memmap)
            if (run.dir/'trajectory_links.npz').exists():
                delta=np.load(run.dir/'delta.npy',mmap_mode='r');scalar=np.load(run.dir/'scalar.npy',mmap_mode='r');valid=np.load(run.dir/'trajectory_links.npz')['valid']
            else:delta,scalar,valid=extract(rows,x,run.dir)
            assert valid[eligible].all(), 'Original eligible rows lack causal trajectory links'
            write_json_atomic(run.dir/'preflight.json',{'rows':len(rows),'eligible':len(eligible),'A_rows':int((near>=0).sum()),'A_positives':int(near[near>=0].sum()),
                'cases':len(split_cases),'eligible_feature_coverage':int(valid[eligible].sum()),'mmap':True,'threadpools':threadpool_info(),
                'hash_identity_and_family_separation_passed':True})
            rounds=np.array([r['round'] for r in rows]);eventual=np.array([r['label'] for r in rows]);pressure=np.array([r['condition']=='recruiting' for r in rows],dtype=int)
            fitdir=run.dir/'fits';fitdir.mkdir(exist_ok=True)
            for mode in ('pooled','loso'):
                pred={f'{v}__{m}':np.full((3,len(rows)),np.nan) for v in ('eventual','A_hazard') for m in METHODS}
                pred['pressure_l32']=np.full((3,len(rows)),np.nan);folds=np.full((3,len(rows)),-1,dtype=int)
                for case in [c for c in split_cases if c['mode']==mode]:
                    started=time.perf_counter();seed=case['seed'];fold=case['fold'];si=SEEDS.index(seed);test=case['test'];train=case['train'];folds[si,test]=fold
                    jobs=[]
                    for variant,y in [('eventual',eventual),('A_hazard',near)]:
                        tr=train if variant=='eventual' else train[near[train]>=0]
                        te=test if variant=='eventual' else test[near[test]>=0]
                        for j,layer in enumerate(LAYERS):
                            for kind,features in [('delta',delta[:,j,:]),('scalar',scalar[:,j,:])]:
                                jobs.append((f'{variant}__{kind}_l{layer}',features,y,tr,te))
                    jobs.append(('pressure_l32',x[:,32,:],pressure,np.sort(np.r_[train,case['cal']]),test))
                    for name,features,y,tr,te in jobs:
                        dest=fitdir/f'{mode}-s{seed}-f{fold}-{name}.npz'
                        if dest.exists():
                            with np.load(dest) as saved:
                                assert np.array_equal(saved['train'],tr) and np.array_equal(saved['test'],te)
                                values=saved['scores']
                        else:values=fit_one(features,y,tr,te,rounds,seed,dest)
                        pred[name][si,te]=values
                    print('FIT_CASE',mode,seed,fold,round(time.perf_counter()-started,1),flush=True)
                for key,values in pred.items():
                    ids=eligible[near[eligible]>=0] if key.startswith('A_hazard') else eligible
                    assert np.isfinite(values[:,ids]).all()
                np.savez_compressed(run.dir/f'{mode}-predictions.npz',**pred,eligible=eligible,folds=folds)
            metrics,exported=finish_outputs(run,rows,eligible,near,args.reps)
            seen=set()
            with (run.dir/'probe_scores.csv').open() as f:
                for r in csv.DictReader(f):
                    key=tuple(r[k] for k in ('row_id','analysis','seed','method','label_variant'));assert key not in seen;seen.add(key)
                    assert r['request_sha256']==rows[int(r['row'])]['request_sha256'] and np.isfinite(float(r['score']))
            write_json_atomic(run.dir/'audit.json',{'csv_rows':len(seen),'expected_export':exported,'unique_keys':True,'hashes_and_finite_scores':True,'fit_artifacts':len(list(fitdir.glob('*.npz'))),'sample_score_reconstruction_passed':True,'threads':2,'paid_cost_usd':0})
            assert len(seen)==exported
        run.result(metrics=len(metrics),exported=exported,paid_cost_usd=0);run.finish();print('EXPLORE_RUN',run.dir,flush=True)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':main()
