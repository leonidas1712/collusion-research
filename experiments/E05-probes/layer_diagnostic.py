"""Appendix-only outer-fold layer diagnostic; never selects the headline layer."""
import argparse
import csv
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from threadpoolctl import threadpool_limits
from data import ROOT,CANDIDATES
from near_term import DATA,FIT,SEEDS,MODES,save_lr
from learning_curve import LABELS,labels
from models import fit_logistic,score
from evaluate import ranking_summary
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run


def case(args):
    directory,near,name,mode,seed,fold=args
    with threadpool_limits(limits=2):
        rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
        keep,y=labels(rows,name);x=np.load(ROOT/'runs'/DATA/'features.npy',mmap_mode='r')
        with np.load(ROOT/'runs'/FIT/mode/f'split-s{seed}-f{fold}.npz') as d:
            train=d['train'][keep[d['train']]];test=d['test'][keep[d['test']]]
        out=directory/name/mode/f's{seed}-f{fold}';out.mkdir(parents=True)
        predictions=np.empty((len(test),len(CANDIDATES)));sources={};si=SEEDS.index(seed)
        aux=None
        if name=='eventual' and mode=='pooled':
            with np.load(ROOT/'runs'/FIT/mode/'predictions.npz') as d:aux=d['layer_scores'][si,test]
            assert np.isfinite(aux).all()
        for j,layer in enumerate(CANDIDATES):
            source=(ROOT/'runs'/FIT/mode/f'lr-s{seed}-f{fold}-l{layer}.npz') if name=='eventual' else (ROOT/'runs'/near/name/mode/f's{seed}-f{fold}'/f'lr-l{layer}.npz')
            if aux is not None:
                predictions[:,j]=aux[:,j];sources[layer]='saved_aux_scores'
            elif source.exists():
                with np.load(source) as model:
                    predictions[:,j]=((np.asarray(x[test,layer],dtype=float)-model['mean'])/model['scale'])@model['coef'][0]+model['intercept'][0]
                sources[layer]=str(source.relative_to(ROOT))
            else:
                model=fit_logistic(x[train,layer],y[train],np.array([rows[i]['round'] for i in train]),seed)
                predictions[:,j]=score(model,x[test,layer]);save_lr(out/f'lr-l{layer}.npz',model);sources[layer]='refit_original_recipe'
        assert np.isfinite(predictions).all()
        np.savez_compressed(out/'predictions.npz',scores=predictions,test=test,train=train,layers=CANDIDATES)
        write_json(out/'sources.json',sources)
        return name,mode,seed,fold,sum(v=='refit_original_recipe' for v in sources.values())


def summarize(run,rows,near,reps):
    results={};table=[];maxerror=0.
    for name in LABELS:
        keep,y=labels(rows,name);ids=np.flatnonzero(keep)
        rounds=np.array([rows[i]['round'] for i in ids]);families=np.array([rows[i]['family'] for i in ids]);scenarios=[rows[i]['scenario'] for i in ids]
        results[name]={}
        for mode in MODES:
            values=np.full((3,len(rows),len(CANDIDATES)),np.nan)
            for si,seed in enumerate(SEEDS):
                for fold in range(5 if mode=='pooled' else 6):
                    with np.load(run.dir/name/mode/f's{seed}-f{fold}'/'predictions.npz') as d:
                        assert np.isnan(values[si,d['test']]).all();values[si,d['test']]=d['scores']
            assert np.isfinite(values[:,ids]).all()
            source=ROOT/'runs'/(FIT if name=='eventual' else near)
            if name!='eventual':source=source/name
            with np.load(source/mode/'predictions.npz') as d:
                error=float(np.max(np.abs(values[:,ids,CANDIDATES.index(32)]-d['fixed32'][:,ids])));maxerror=max(maxerror,error);assert error<1e-9
                headline,_,_=ranking_summary(np.tile(y[ids],(3,1)),d['nested'][:,ids],rounds,families,reps,stratum_key=scenarios)
            metrics={}
            for j,layer in enumerate(CANDIDATES):
                summary,_,_=ranking_summary(np.tile(y[ids],(3,1)),values[:,ids,j],rounds,families,reps,stratum_key=scenarios)
                metrics[str(layer)]=summary;table.append(dict(label_variant=name,analysis=mode,layer=layer,
                    auc=summary['within_round_auc'],ci_low=summary['within_round_ci95'][0],ci_high=summary['within_round_ci95'][1],
                    rows=len(ids),families=len(set(families))))
            results[name][mode]=dict(layers=metrics,headline=headline,rows=len(ids),families=len(set(families)))
            np.savez_compressed(run.dir/name/mode/'layer_scores.npz',scores=values,eligible=ids,y=y,layers=CANDIDATES,seeds=SEEDS)
            write_json(run.dir/'metrics.json',results);print('EVALUATED',name,mode,flush=True)
    with (run.dir/'layer_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.rc_context({'font.size':10,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False}):
        fig,axes=plt.subplots(2,2,figsize=(9,6.5),sharex=True,sharey=True,layout='constrained')
        for row,name in enumerate(LABELS):
            for col,mode in enumerate(MODES):
                ax=axes[row,col];m=results[name][mode];z=[m['layers'][str(k)] for k in CANDIDATES]
                a=np.array([v['within_round_auc'] for v in z]);lo=np.array([v['within_round_ci95'][0] for v in z]);hi=np.array([v['within_round_ci95'][1] for v in z])
                ax.vlines(CANDIDATES,lo,hi,color='#0072B2',linewidth=1,alpha=.7)
                ax.plot(CANDIDATES,a,'o-',color='#0072B2',markersize=3,linewidth=1)
                ax.axhline(.5,color='#777777',linestyle='--',linewidth=1)
                ax.set_title(f"{name.replace('_',' ')} · {mode}\n{m['rows']} steps, {m['families']} families; nested={m['headline']['within_round_auc']:.3f}")
                ax.set(ylim=(0,1),xlim=(-1,64),xticks=[0,16,32,48,63])
                if row==1:ax.set_xlabel('Decoder block (zero-based)')
                if col==0:ax.set_ylabel('Scenario × round AUROC')
        fig.suptitle('Per-layer diagnostic — headline remains inner-selected',fontsize=13)
        for extension in ('png','pdf'):fig.savefig(run.dir/f'layer_diagnostic.{extension}',dpi=300,facecolor='white')
        plt.close(fig)
    caption='All 17 fixed candidate layers, evaluated on unchanged outer test folds. Points average three seeds; vertical intervals are pointwise 95% family-bootstrap intervals (1,000 resamples), conditional on fitted models. Dashed line: AUROC 0.5. No smoothing or missing-layer interpolation. This is a diagnostic, not a new layer-selection result; intervals are not simultaneous across layers.'
    (run.dir/'figure_description.txt').write_text('Four panels compare eventual outcome and near-term B, each under pooled CV and leave-one-scenario-out. '+caption+' Numeric values are in layer_metrics.csv.\n')
    lines=['# Outcome-probe layer diagnostic','',caption,'',
        '![All candidate layers](layer_diagnostic.png)','',
        'The highest observed layer is reported descriptively below. Selecting it on these outer-test scores would invalidate a headline estimate. The original inner-selected result is unchanged. Pooled curves retain the scenario × round metric’s sensitivity to cross-fold score calibration; LOSO comparisons stay within one fitted model per scenario.','',
        '| Label | Analysis | Descriptive maximum layer | AUROC | Inner-selected AUROC |','|---|---|---:|---:|---:|']
    for name in LABELS:
        for mode in MODES:
            m=results[name][mode];peak=max(CANDIDATES,key=lambda k:m['layers'][str(k)]['within_round_auc'])
            lines.append(f"| {name} | {mode} | {peak} | {m['layers'][str(peak)]['within_round_auc']:.3f} | {m['headline']['within_round_auc']:.3f} |")
    lines+=['',f'Parents: `{DATA}`, `{FIT}`, `{near}`. Eventual pooled scores reuse aux-mode outputs; other saved layer coefficients are reused, and only missing layers are refit on the original training rows. Fixed32 predictions agree with original scores to maximum absolute error {maxerror:.3g}. CSV supplies every plotted estimate and interval. PDF and 300-dpi PNG are provisional appendix exports; no publisher-specific formatting was assumed.']
    (run.dir/'report.md').write_text('\n'.join(lines)+'\n')
    write_json(run.dir/'figure_provenance.json',dict(sources=[DATA,FIT,near],data='layer_metrics.csv',dimensions_inches=[9,6.5],dpi=300,
        uncertainty='pointwise 95% family bootstrap, 1000 replicates',bootstrap_seed=20261024,layer_selection='none; all 17 candidates',max_fixed32_error=maxerror))
    return maxerror


def main(args):
    run=start_run('e05-layer-diagnostic',experiment='E05',parents=[DATA,FIT,args.near_run],settings=dict(layers=CANDIDATES,diagnostic_only=True,bootstrap_reps=args.reps,no_gpu=True))
    try:
        assert json.loads((ROOT/'runs'/args.near_run/'meta.json').read_text())['status']=='finished'
        assert json.loads((ROOT/'runs'/FIT/'meta.json').read_text())['settings']['candidate_layers']==CANDIDATES
        jobs=[(run.dir,args.near_run,name,mode,seed,fold) for name in LABELS for mode in MODES for seed in SEEDS for fold in range(5 if mode=='pooled' else 6)]
        refits=0
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures=[pool.submit(case,job) for job in jobs]
            try:
                for future in as_completed(futures):
                    result=future.result();refits+=result[-1];print('SCORED',result,flush=True)
            except BaseException:
                for future in futures:future.cancel()
                raise
        rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
        with threadpool_limits(limits=2):error=summarize(run,rows,args.near_run,args.reps)
        run.result(refitted_layers=refits,max_fixed32_error=error);run.finish();print('LAYER_DIAGNOSTIC',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('near_run');p.add_argument('--workers',type=int,default=3);p.add_argument('--reps',type=int,default=1000);main(p.parse_args())
