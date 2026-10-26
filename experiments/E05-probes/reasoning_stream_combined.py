"""Post-process saved probes into a training-normalized combined running maximum."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
from threadpoolctl import threadpool_limits
from reasoning_stream_data import ROOT,DATA,FITS
from reasoning_stream_labels import add_horizon_labels,VARIANTS
from reasoning_stream_report import stream_metrics,SEEDS
from metrics import threshold_at_fpr
from collusion.runs import start_run,write_json_atomic


def normalizer(last_scores,reasoning_scores):
    """One unit per reply for both streams; reasoning mass is spread over tokens."""
    last=np.asarray(last_scores,dtype=float)
    mu_last=float(last.mean());sd_last=float(last.std())
    mu_reason=float(np.mean([np.mean(s) for s in reasoning_scores]))
    second=float(np.mean([np.mean(np.square(s)) for s in reasoning_scores]))
    sd_reason=float(np.sqrt(max(0,second-mu_reason**2)))
    assert sd_last>1e-12 and sd_reason>1e-12
    return dict(last_mean=mu_last,last_sd=sd_last,reasoning_mean=mu_reason,reasoning_sd=sd_reason)


def combine(last,reasoning,norm):
    first=(float(last)-norm['last_mean'])/norm['last_sd']
    tail=(np.asarray(reasoning)-norm['reasoning_mean'])/norm['reasoning_sd']
    stream=np.r_[first,tail]
    return float(stream.max()),stream


def linear_scores(x,parameters):
    direction=parameters['coef'].reshape(-1)/parameters['scale']
    bias=float(np.asarray(parameters['intercept']).reshape(-1)[0])-parameters['mean']@direction
    result=np.empty(len(x),dtype=float)
    for start in range(0,len(x),2048):
        result[start:start+2048]=np.asarray(x[start:start+2048],dtype=float)@direction+bias
    return result


def fold_scores(file,rows,base,reason,last,out):
    f=json.loads(file.read_text());p=f['plan'];clean=f['clean'];layer=f['layer']
    frozen=FITS/f"post_ask/A_hazard/{p['mode']}/s{p['seed']}-f{p['fold']}"
    layer_last=json.loads((frozen/'fit.json').read_text())['layer']
    last_model=frozen/f'lr-l{layer_last}.npz'
    signature=hashlib.sha256((hashlib.sha256((file.parent/'model.npz').read_bytes()).hexdigest()+hashlib.sha256(last_model.read_bytes()).hexdigest()+json.dumps(f['split'],sort_keys=True)+str(clean)+'score-parity-v1').encode()).hexdigest()
    dest=out/'combined_stream'/f['variant']/('censored' if clean else 'all')/p['mode']/f"s{p['seed']}-f{p['fold']}"
    if (dest/'normalization.json').exists():
        if json.loads((dest/'normalization.json').read_text())['signature']==signature:return dest
    with threadpool_limits(limits=1):
        token_scores=linear_scores(reason[layer],np.load(file.parent/'model.npz'))
        last_scores=linear_scores(last[:,layer_last],np.load(last_model))[[r['index'] for r in rows]]
    length='clean_tokens' if clean else 'reasoning_tokens'
    sequences=[token_scores[r['start']:r['start']+r[length]] for r in rows]
    prior=np.load(file.parent/'scores.npz')
    replayed_max=np.array([sequences[i].max() for i in prior['indices']])
    np.testing.assert_allclose(replayed_max,prior['max_scores'],rtol=1e-8,atol=1e-8)
    parity=float(np.max(np.abs(replayed_max-prior['max_scores'])))
    train=f['split']['train']
    norm=normalizer(last_scores[train],[sequences[i] for i in train])
    combined=np.array([combine(s,t,norm)[0] for s,t in zip(last_scores,sequences)])
    cal=f['split']['calibration']
    threshold,cal_info=threshold_at_fpr(combined[cal],cal,.05)
    cal_episodes={base[i]['episode'] for i in p['split']['calibration']}
    full_cal=[i for i,r in enumerate(rows) if r['episode'] in cal_episodes and r['condition']=='control' and r['stream_window']=='post_ask']
    threshold_full,full_info=threshold_at_fpr(combined[full_cal],full_cal,.05)
    test_episodes={base[i]['episode'] for i in p['split']['test']}
    full_test=np.array([i for i,r in enumerate(rows) if r['episode'] in test_episodes and r['condition']=='recruiting' and r['stream_window']=='post_ask'])
    common=np.array(f['split']['test'])
    assert set(common)<=set(full_test)
    assert not {rows[i]['episode'] for i in train}&test_episodes
    assert not {rows[i]['episode'] for i in full_cal}&test_episodes
    records={}
    for name,indices,t in [('common',common,threshold),('full',full_test,threshold_full)]:
        crossings=[];phases=[]
        for i in indices:
            score,stream=combine(last_scores[i],sequences[i],norm)
            hit=np.flatnonzero(stream>t)
            if not len(hit):crossings.append(np.nan);phases.append(-1)
            elif hit[0]==0:crossings.append(0.);phases.append(0)
            else:crossings.append(float(hit[0])/rows[i]['reasoning_tokens']);phases.append(1)
        records.update({name+'_indices':indices,name+'_scores':combined[indices],name+'_crossings':crossings,name+'_phases':phases})
    dest.mkdir(parents=True,exist_ok=True)
    np.savez(dest/'scores.npz',**records)
    write_json_atomic(dest/'normalization.json',{'signature':signature,'reasoning_score_parity_max_abs':parity,'normalizer':norm,'train_reply_count':len(train),'training_reply_indices':train,'training_only':True,'reasoning_normalization':'each training reply has total weight one across its tokens','threshold_common':threshold,'threshold_full':threshold_full,'calibration_common':cal_info,'calibration_full':full_info,'calibration_common_indices':cal,'calibration_full_indices':full_cal,'plan':{k:p[k] for k in ['seed','fold','mode']},'layer_reasoning':layer,'layer_last_prompt':layer_last})
    return dest


def main(args):
    out=args.out;plan=json.loads((out/'analysis_plan.json').read_text());data=Path(plan['data'])
    rows=add_horizon_labels(json.loads((data/'replies.json').read_text()))
    base=[json.loads(s) for s in (DATA/'rows.jsonl').read_text().splitlines()]
    reason=np.load(data/'reasoning.npy',mmap_mode='r');last=np.load(DATA/'features.npy',mmap_mode='r')
    variants=['immediate','round'] if args.interim else VARIANTS
    run=start_run('e05-reasoning-combined-stream',experiment='E05',parents=[out.name],tags=['exploratory','cpu-only','postprocessing'],settings={'variants':variants,'no_refit':True,'normalization':'training-only, reasoning equal reply mass','bootstrap':args.bootstrap})
    results={};alarms={};export=[]
    try:
        for variant in variants:
            for mask in ['all','censored']:
                for mode in ['pooled','loso']:
                    key=f'{variant}/{mask}/{mode}'
                    files=sorted((out/key).glob('s*-f*/fit.json'))
                    assert len(files)==(15 if mode=='pooled' else 18)
                    arrays={name:{k:np.full((3,len(rows)),np.nan) for k in ['scores','crossings','phases','folds']} for name in ['common','full']}
                    for file in files:
                        dest=fold_scores(file,rows,base,reason,last,out)
                        meta=json.loads((dest/'normalization.json').read_text());p=meta['plan'];si=SEEDS.index(p['seed']);a=np.load(dest/'scores.npz')
                        for name in arrays:
                            ids=a[name+'_indices'];arr=arrays[name];assert np.isnan(arr['scores'][si,ids]).all()
                            for k in ['scores','crossings','phases']:arr[k][si,ids]=a[name+'_'+k]
                            arr['folds'][si,ids]=p['fold']
                            for j,i in enumerate(ids):
                                export.append(dict(variant=variant,mask=mask,analysis=mode,cohort=name,seed=p['seed'],fold=p['fold'],row_id=rows[i]['row_id'],request_sha256=rows[i]['request_sha256'],label=rows[i]['y_'+variant],score=float(a[name+'_scores'][j]),threshold=meta['threshold_'+name],first_alarm_phase=int(a[name+'_phases'][j]),first_alarm_reasoning_fraction=float(a[name+'_crossings'][j])))
                    for name,arr in arrays.items():
                        valid=np.isfinite(arr['scores']).all(axis=0);ids=np.flatnonzero(valid)
                        assert len(ids)==(1995 if name=='common' else 2205)
                        y=np.array([rows[i]['y_'+variant] for i in ids])
                        result,_=stream_metrics(rows,ids,y,arr['scores'][:,ids],arr['folds'][:,ids],args.bootstrap)
                        results[key+'/'+name]=result
                        if variant=='immediate':
                            pos=ids[y==1];held=ids[[not rows[i]['ever_public'] for i in ids]];cross=arr['crossings'][:,pos];ok=cross[np.isfinite(cross)]
                            alarms[key+'/'+name]={'positive_replies':len(pos),'rows':len(ids),'alarm_rate_by_seed':np.mean(arr['phases'][:,pos]>=0,axis=1).tolist(),'last_prompt_alarm_rate_by_seed':np.mean(arr['phases'][:,pos]==0,axis=1).tolist(),'held_reply_alarm_rate_by_seed':np.mean(arr['phases'][:,held]>=0,axis=1).tolist(),'crossing_fraction_q25_median_q75':np.quantile(ok,[.25,.5,.75]).tolist() if len(ok) else None,'last_prompt_position_fraction':0,'calibration':'strict > combined control-reply maximum at nominal 5%; separate common/full calibration'}
                        print('COMBINED',key,name,result['within_round_auc'],flush=True)
                    write_json_atomic(out/'combined_metrics.json',results);write_json_atomic(out/'combined_alarms.json',alarms)
        with (out/'combined_probe_scores.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(export[0]));writer.writeheader();writer.writerows(export)
        append_report(out,results,alarms,variants,args.interim)
        run.result(output=str(out/'report.md'),variants=variants);run.finish()
    except BaseException as e:run.finish('failed',str(e));raise


def append_report(out,results,alarms,variants,interim):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    original=json.loads((out/'metrics.json').read_text())
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharey=True)
    methods=[('token_max','Reasoning MAX','#35618f','o',-.18),('token_mean','Reasoning mean','#b14f35','s',-.06),('frozen_last_prompt_A','Last prompt','#547443','^',.06),('combined','Combined saved stream','#774e91','D',.18)]
    for ax,(mask,mode) in zip(axes.flat,[(m,s) for m in ['all','censored'] for s in ['pooled','loso']]):
        for method,label,color,marker,offset in methods:
            rr=[results[f'{v}/{mask}/{mode}/common'] if method=='combined' else original[f'{v}/{mask}/{mode}/extended/{method}'] for v in variants]
            y=np.array([r['within_round_auc'] for r in rr]);ci=np.array([r['within_round_ci95'] for r in rr]);x=np.arange(len(variants))+offset
            ax.vlines(x,ci[:,0],ci[:,1],color=color);ax.scatter(x,y,color=color,marker=marker,label=label)
        ax.axhline(.5,color='gray',linestyle=':');ax.set_ylim(0,1);ax.set_title(f'{mode}; {mask} reasoning')
        ax.set_xticks(range(len(variants)),[{'immediate':'k=0','h1':'k=1','h2':'k=2','h3':'k=3','round':'Paper round A'}[v] for v in variants]);ax.set_ylabel('Within scenario × round AUROC');ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(out/'horizon_auc_with_combined.png',dpi=180);fig.savefig(out/'horizon_auc_with_combined.pdf');plt.close(fig)
    def fmt(r):
        lo,hi=r['within_round_ci95'];return f"{r['within_round_auc']:.3f} [{lo:.3f}, {hi:.3f}]"
    lines=['## Combined saved-stream addendum','',
        'This post-processing variant prepends the frozen last-prompt score to the reasoning-token score stream, with no new fits or inference. Each component is z-scored using only the outer training replies. The last-prompt mean and variance give each reply equal weight. For reasoning, each reply has total weight one spread uniformly over its available tokens; both moments use those weights. The reply score is the maximum standardized score anywhere in this combined stream. These are independently trained probes combined by a fixed rule, not one probe applied uniformly to all token positions.','',
        'Only residuals at the **last prompt token**, shaped [24, 2880] per request, and the **returned reasoning-body tokens**, shaped [24, n_reasoning, 2880], were saved. Residuals at other prompt-token positions and at answer/tool-call token positions were **not** saved and require the separate expanded replay. Token IDs and saved request/reply transcripts are available, but are not activations. Thus “full saved stream” does not mean every token processed by the model.','',
        'The primary comparison below uses identical 1,995 replies with reasoning. A separate full-coverage result uses all 2,205 replies, including the 210 with no reasoning; those replies have a last-prompt score only. Each cohort has its own nominal 5% training-control reply-maximum threshold. Test labels never enter the normalization or calibration. Training-score normalization is in-sample rather than cross-fitted within the training partition; this is an exploratory combination rule.','',
        '![AUROC by horizon including the combined stream](horizon_auc_with_combined.png)','',
        '| Label | Tokens | Split | Reasoning MAX | Reasoning mean | Last prompt | Combined, same replies | Combined, all replies |','|---|---|---|---|---|---|---|---|']
    for v in variants:
        for mask in ['all','censored']:
            for mode in ['pooled','loso']:
                k=f'{v}/{mask}/{mode}';rr=[original[k+'/extended/'+m] for m in ['token_max','token_mean','frozen_last_prompt_A']]+[results[k+'/common'],results[k+'/full']]
                lines.append('| '+ ' | '.join([v,mask,mode,*[fmt(r) for r in rr]])+' |')
    lines+=['','### Combined alarm timing (k=0)','',
        'A crossing at the last prompt token has position zero. Otherwise the first crossing is expressed as the fraction of the original reasoning length consumed. Rates average the three seeds; crossing quantiles pool crossing reply-seed observations. The full cohort includes all 146 leaking replies, rather than only the 121 with reasoning.','',
        '| Tokens | Split | Cohort | Leaking replies | Warning rate | At last prompt | Held-reply alarms | First crossing median [IQR] |','|---|---|---|---:|---:|---:|---:|---|']
    for k,a in alarms.items():
        _,mask,mode,cohort=k.split('/');q=a['crossing_fraction_q25_median_q75'];text='None' if q is None else f'{q[1]:.3f} [{q[0]:.3f}, {q[2]:.3f}]'
        lines.append(f"| {mask} | {mode} | {cohort} | {a['positive_replies']} | {np.mean(a['alarm_rate_by_seed']):.1%} | {np.mean(a['last_prompt_alarm_rate_by_seed']):.1%} | {np.mean(a['held_reply_alarm_rate_by_seed']):.1%} | {text} |")
    lines+=['','Normalization statistics, training row indices, control calibration indices, and thresholds are saved in `combined_stream/`; metrics and per-row scores are in `combined_metrics.json`, `combined_alarms.json`, and `combined_probe_scores.csv`. The intervals use the same family bootstrap as the primary report. This addendum uses only the original saved residuals, independently of the separate expanded replay.']
    report=out/'report.md';prefix=report.read_text().split('\n## Combined saved-stream addendum')[0]
    report.write_text(prefix.rstrip()+'\n\n'+'\n'.join(lines)+'\n')
    write_json_atomic(out/'combined_status.json',{'complete':True,'interim':interim,'variants':variants,'refit':False,'gpu':False})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--interim',action='store_true');p.add_argument('--bootstrap',type=int,default=1000);a=p.parse_args();main(a)
