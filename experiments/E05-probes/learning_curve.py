"""Training-family learning curves with fixed replay2 test and validation folds."""
import argparse
import csv
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from threadpoolctl import threadpool_limits
from data import ROOT
from near_term import DATA, FIT, SEEDS, MODES, label_rows, restrict, check_split, choose_layer, save_lr
from models import fit_logistic, score
from evaluate import ranking_summary, interval
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run

FRACTIONS = (.25,.5,.75,1.)
LABELS = ('eventual','B_round_contrast')


def labels(rows, name):
    if name == 'B_round_contrast':return label_rows(rows,name)
    return (np.array([r['eligible'] and r['condition']=='recruiting' for r in rows]),
            np.array([r['label'] for r in rows]))


def plan_case(rows, name, mode, seed, fold):
    keep,y=labels(rows,name)
    with np.load(ROOT/'runs'/FIT/mode/f'split-s{seed}-f{fold}.npz') as d:
        base={k:restrict(d[k],keep) for k in ('train','test','inner_train','inner_validation')}
    families=sorted({rows[i]['family'] for i in base['train']});plans=[]
    for draw in range(3):
        rng=np.random.default_rng(seed+fold*101+draw*100003)
        for attempt in range(500):
            permutation=rng.permutation(families).tolist();cases=[]
            try:
                for fraction in FRACTIONS:
                    chosen=set(permutation[:int(np.ceil(len(families)*fraction))])
                    split={k:(v.copy() if k=='test' else np.array([i for i in v if rows[i]['family'] in chosen],dtype=int)) for k,v in base.items()}
                    check_split(rows,y,split)
                    cases.append(dict(label_variant=name,analysis=mode,seed=seed,fold=fold,draw=draw,
                        fraction=fraction,train_families=sorted(chosen),total_train_families=len(families),
                        sample_attempt=attempt,**{k:v.tolist() for k,v in split.items()}))
                plans.extend(cases);break
            except (AssertionError,ValueError):
                continue
        else:raise ValueError(f'No valid nested training subsample: {name} {mode} {seed} {fold} {draw}')
    return plans


def fit_case(args):
    directory,case=args
    with threadpool_limits(limits=2):
        began=time.perf_counter();rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
        _,y=labels(rows,case['label_variant']);x=np.load(ROOT/'runs'/DATA/'features.npy',mmap_mode='r')
        train,test,inner,val=(np.asarray(case[k],dtype=int) for k in ('train','test','inner_train','inner_validation'))
        seed=case['seed'];fold=case['fold']
        layer,selection=choose_layer(rows,x,y,inner,val,seed+fold*17)
        out=directory/case['label_variant']/case['analysis']/f"s{seed}-f{fold}-d{case['draw']}-p{int(case['fraction']*100)}";out.mkdir(parents=True)
        values={};rounds=np.array([rows[i]['round'] for i in train])
        for k in sorted({layer,32}):
            model=fit_logistic(x[train,k],y[train],rounds,seed);pred=score(model,x[test,k]);assert np.isfinite(pred).all()
            save_lr(out/f'lr-l{k}.npz',model)
            if k==layer:values['nested']=pred
            if k==32:values['fixed32']=pred
        np.savez_compressed(out/'predictions.npz',**values,test=test,train=train,inner_train=inner,inner_validation=val)
        note=dict(**case,chosen_layer=layer,validation_auroc=selection,seconds=time.perf_counter()-began)
        write_json(out/'fit.json',note)
        return {k:note[k] for k in ('label_variant','analysis','seed','fold','draw','fraction','chosen_layer','seconds')}


def report(run,rows,plan,near_run,reps):
    result={};bootstrap={};counts={}
    for name in LABELS:
        keep,y=labels(rows,name);ids=np.flatnonzero(keep)
        rounds=np.array([rows[i]['round'] for i in ids]);families=np.array([rows[i]['family'] for i in ids]);scenarios=[rows[i]['scenario'] for i in ids]
        result[name]={}
        for mode in MODES:
            result[name][mode]={};bootstrap[(name,mode)]={}
            base=ROOT/'runs'/(FIT if name=='eventual' else near_run)
            if name!='eventual':base=base/name
            with np.load(base/mode/'predictions.npz') as d:
                full={m:d[m][:,ids] for m in ('nested','fixed32')}
            for fraction in FRACTIONS:
                preds={m:np.full((9,len(rows)),np.nan) for m in full};sizes=[]
                for si,seed in enumerate(SEEDS):
                    for draw in range(3):
                        slot=si*3+draw
                        if fraction==1:
                            for m in full:preds[m][slot,ids]=full[m][si]
                        for fold in range(5 if mode=='pooled' else 6):
                            case=next(c for c in plan if (c['label_variant'],c['analysis'],c['seed'],c['draw'],c['fold'],c['fraction'])==(name,mode,seed,draw,fold,fraction))
                            sizes.append(len(case['train_families']))
                            if fraction==1:continue
                            path=run.dir/name/mode/f's{seed}-f{fold}-d{draw}-p{int(fraction*100)}'
                            with np.load(path/'predictions.npz') as d:
                                assert np.array_equal(d['test'],case['test'])
                                for m in full:preds[m][slot,d['test']]=d[m]
                summaries={};boots={}
                for method,p in preds.items():
                    assert np.isfinite(p[:,ids]).all()
                    summary,wb,_=ranking_summary(np.tile(y[ids],(9,1)),p[:,ids],rounds,families,reps,stratum_key=scenarios)
                    summaries[method]=summary;boots[method]=wb
                summaries['training_family_counts']=dict(min=min(sizes),max=max(sizes),mean=float(np.mean(sizes)))
                result[name][mode][str(fraction)]=summaries;bootstrap[(name,mode)][fraction]=boots
                np.savez_compressed(run.dir/name/mode/f'curve-p{int(fraction*100)}.npz',**preds,eligible=ids,y=y,seeds=np.repeat(SEEDS,3),draws=np.tile(range(3),3))
                print('EVALUATED',name,mode,fraction,flush=True)
            gains={}
            for method in full:
                low=result[name][mode]['0.75'][method]['within_round_auc'];high=result[name][mode]['1.0'][method]['within_round_auc']
                gains[method]=dict(gain_75_to_100=high-low,paired_family_ci95=interval(bootstrap[(name,mode)][1.][method]-bootstrap[(name,mode)][.75][method]))
            result[name][mode]['gain_75_to_100']=gains
            write_json(run.dir/'metrics.json',result)
    lines=['# Training-family learning curves','',
        'Fixed replay-2 outer test sets; eventual outcome and near-term B. At each outer split, three seeded permutations of recruiting training families define nested 25/50/75/100% subsets (rounded up). Saved inner-training/validation assignments are filtered to those families. Draws are retried only when a training or inner-validation split cannot support the original recipe; no fitted scores or outer test labels guide sampling. All selected families and retry counts are in sampling_plan.json.', '',
        'Inner-selected and fixed-layer-32 logistic probes use the original fitting settings. The 100% scores reuse the saved full-data fits and are identical across subsample draws. Estimates average three seeds × three draws; 95% family-bootstrap intervals use the same test-family resamples across sizes and methods. Intervals condition on the fits, not on a new training-data experiment. Primary metric: scenario × round AUROC.', '',
        '| Label | Analysis | Training fraction | Training families (min–max) | Nested AUROC [95% CI] | Fixed32 AUROC [95% CI] |',
        '|---|---|---:|---|---|---|']
    fmt=lambda m:f"{m['within_round_auc']:.3f} [{m['within_round_ci95'][0]:.3f}, {m['within_round_ci95'][1]:.3f}]"
    for name in LABELS:
        for mode in MODES:
            for fraction in FRACTIONS:
                r=result[name][mode][str(fraction)];s=r['training_family_counts']
                lines.append(f"| {name} | {mode} | {fraction:.0%} | {s['min']}–{s['max']} | {fmt(r['nested'])} | {fmt(r['fixed32'])} |")
    lines+=['','## Is performance still rising at 100%?','',
        '| Label | Analysis | Method | Gain, 75% to 100% [paired family CI] |','|---|---|---|---|']
    for name in LABELS:
        for mode in MODES:
            for method,g in result[name][mode]['gain_75_to_100'].items():
                ci=g['paired_family_ci95'];lines.append(f"| {name} | {mode} | {method} | {g['gain_75_to_100']:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}] |")
    lines+=['','A positive final increment is compatible with further gains; an interval spanning zero does not establish saturation. These curves vary training-family count on the existing test distribution and do not predict the benefit of collecting a new scenario.', '',
        'The optional v1+v2 deploy-token comparison is not included: v1 uses a different episode/eligibility cache and combining it would require harmonized family splits and a separate fit. Existing v2-only results remain in the replay-2 report; they are not substituted for a matched combined-data comparison.', '',
        f'Sources: `{DATA}`, `{FIT}`, `{near_run}`. Per-subset coefficients, split indices and predictions are saved for audit. No API/GPU use.']
    (run.dir/'report.md').write_text('\n'.join(lines)+'\n')
    return result


def main(args):
    rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
    run=start_run('e05-learning-curve',experiment='E05',parents=[DATA,FIT,args.near_run]+([args.plan_run] if args.plan_run else []),settings=dict(
        labels=LABELS,fractions=FRACTIONS,draws=3,seeds=SEEDS,workers=args.workers,bootstrap_reps=args.reps,no_gpu=True))
    try:
        plan=[]
        for name in LABELS:
            for mode in MODES:
                for seed in SEEDS:
                    for fold in range(5 if mode=='pooled' else 6):plan.extend(plan_case(rows,name,mode,seed,fold))
        if args.plan_run:
            frozen=json.loads((ROOT/'runs'/args.plan_run/'sampling_plan.json').read_text())
            assert plan==frozen, 'Sampling plan changed after preflight'
        write_json(run.dir/'sampling_plan.json',plan)
        jobs=[(run.dir,c) for c in plan if c['fraction']<1]
        print('PREFLIGHT',len(jobs),'new fits; 100% reused; max rejection attempts',max(c['sample_attempt'] for c in plan),flush=True)
        if args.preflight_only:
            run.result(preflight_passed=True);run.finish();print('CURVE_PREFLIGHT',run.id);return
        assert json.loads((ROOT/'runs'/args.near_run/'meta.json').read_text())['status']=='finished'
        progress=[]
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures=[pool.submit(fit_case,job) for job in jobs]
            try:
                for future in as_completed(futures):
                    r=future.result();progress.append(r);write_json(run.dir/'progress.json',progress)
                    print('FIT',len(progress),'/',len(jobs),r,flush=True)
            except BaseException:
                for future in futures:future.cancel()
                raise
        with threadpool_limits(limits=2):report(run,rows,plan,args.near_run,args.reps)
        run.result(fits=len(progress),complete=True);run.finish();print('CURVE_RUN',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('near_run');p.add_argument('--workers',type=int,default=3)
    p.add_argument('--reps',type=int,default=1000);p.add_argument('--preflight-only',action='store_true');p.add_argument('--plan-run');main(p.parse_args())
