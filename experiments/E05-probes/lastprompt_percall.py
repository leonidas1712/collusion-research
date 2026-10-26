"""Matched-label last-prompt ablation using saved activations and frozen folds."""
import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits
from models import fit_logistic, score
from metrics import within_round, threshold_at_fpr
from near_term import save_lr
from reasoning_stream_labels import add_horizon_labels
from reasoning_stream_report import stream_metrics
from reasoning_stream_data import ROOT, DATA, FITS
from gpt_oss_replay_data import CANDIDATES
from collusion.runs import start_run, write_json_atomic

STREAM = ROOT/'runs/20261026-0526-e05-reasoning-stream'
STREAM_DATA = ROOT/'runs/20261026-0522-e05-reasoning-stream-data'
SEEDS = [42,43,44]


def load():
    rows = add_horizon_labels(json.loads((STREAM_DATA/'replies.json').read_text()))
    base = [json.loads(s) for s in (DATA/'rows.jsonl').read_text().splitlines()]
    x = np.load(DATA/'features.npy', mmap_mode='r')
    for r in rows:
        assert base[r['index']]['row_id'] == r['row_id']
        assert base[r['index']]['request_sha256'] == r['request_sha256']
        r['y_strict1'] = int(r['eligible_replies_until_public'] == 1)
    plans = [p for p in json.loads((FITS/'plans.json').read_text()) if p['window']=='post_ask' and p['variant']=='eventual']
    assert len(plans)==33
    return rows, base, x, plans


def run_fit(out, rows, base, x, plan, label, cohort):
    dest=out/cohort/label/plan['mode']/f"s{plan['seed']}-f{plan['fold']}"
    if (dest/'fit.json').exists(): return
    begin=time.monotonic()
    split={}
    for key, ids in plan['split'].items():
        episodes={base[i]['episode'] for i in ids}
        split[key]=np.array([i for i,r in enumerate(rows) if r['episode'] in episodes
            and r['stream_window']=='post_ask' and (cohort=='all' or r['reasoning_tokens']>0)
            and (label!='strict1' or not r['y_immediate'])
            and r['condition']==('control' if key=='calibration' else 'recruiting')],dtype=int)
    for left,right in [('train','test'),('inner_train','inner_validation'),('calibration','test')]:
        assert not {rows[i]['family'] for i in split[left]} & {rows[i]['family'] for i in split[right]}
    assert not {rows[i]['episode'] for i in split['train']} & {rows[i]['episode'] for i in split['calibration']}
    y=np.array([r['y_'+label] for r in rows]); rounds=np.array([r['round'] for r in rows]); scenarios=np.array([r['scenario'] for r in rows])
    source=np.array([r['index'] for r in rows]); fit,val=split['inner_train'],split['inner_validation']
    candidates={}
    for layer in CANDIDATES:
        model=fit_logistic(x[source[fit],layer],y[fit],rounds[fit],plan['seed']+17*plan['fold'])
        candidates[layer]=within_round(y[val],score(model,x[source[val],layer]),rounds[val],stratum_key=scenarios[val])[0]
    assert any(np.isfinite(v) for v in candidates.values())
    layer=max(CANDIDATES,key=lambda k:(candidates[k] if np.isfinite(candidates[k]) else -1,-k))
    train,test,cal=split['train'],split['test'],split['calibration']
    model=fit_logistic(x[source[train],layer],y[train],rounds[train],plan['seed'])
    pred=score(model,x[source[test],layer]); cp=score(model,x[source[cal],layer])
    threshold, calibration=threshold_at_fpr(cp,cal,.05)
    dest.mkdir(parents=True,exist_ok=True)
    save_lr(dest/'model.npz',model)
    np.savez_compressed(dest/'scores.npz',indices=test,scores=pred,calibration_indices=cal,calibration_scores=cp)
    write_json_atomic(dest/'fit.json',dict(layer=layer,candidates=candidates,threshold=threshold,calibration=calibration,
        split={k:v.tolist() for k,v in split.items()},plan=plan,label=label,cohort=cohort,seconds=time.monotonic()-begin))
    print('FIT',str(dest.relative_to(out)),round(time.monotonic()-begin,2),flush=True)


def summarize(out,rows,plans,reps):
    results={}; exports=[]
    for cohort in ['matched','all']:
      for label in ['immediate','strict1']:
       for mode in ['loso','pooled']:
        files=list((out/cohort/label/mode).glob('s*-f*/fit.json'))
        if len(files)!=(18 if mode=='loso' else 15):continue
        scores=np.full((3,len(rows)),np.nan); fold=np.full((3,len(rows)),-1); alarms=np.zeros((3,len(rows)),bool)
        rs=np.full_like(scores,np.nan); ra=np.zeros_like(alarms)
        layers={}
        for path in files:
            f=json.loads(path.read_text());seed=f['plan']['seed'];si=SEEDS.index(seed);fo=f['plan']['fold']
            z=np.load(path.parent/'scores.npz');ids=z['indices'];assert np.isnan(scores[si,ids]).all()
            scores[si,ids]=z['scores'];fold[si,ids]=fo;alarms[si,ids]=z['scores']>f['threshold'];layers[f'{seed}/{fo}']=f['layer']
            if cohort=='matched':
                rp=STREAM/('immediate' if label=='immediate' else 'h1')/'all'/mode/f's{seed}-f{fo}'
                rf=json.loads((rp/'fit.json').read_text());rz=np.load(rp/'scores.npz')
                lookup={int(i):j for j,i in enumerate(rz['indices'])}
                jj=[lookup[int(i)] for i in ids]
                rs[si,ids]=rz['max_scores'][jj];ra[si,ids]=rz['max_scores'][jj]>rf['threshold']
        ids=np.flatnonzero(np.isfinite(scores).all(axis=0));y=np.array([rows[i]['y_'+label] for i in ids])
        expected=sum(r['condition']=='recruiting' and r['stream_window']=='post_ask' and (cohort=='all' or r['reasoning_tokens']>0) and (label!='strict1' or not r['y_immediate']) for r in rows)
        assert len(ids)==expected and np.isfinite(scores[:,ids]).all()
        metrics,boot=stream_metrics(rows,ids,y,scores[:,ids],fold[:,ids],reps)
        held=np.array([not rows[i]['ever_public'] for i in ids]);pos=y==1
        metrics.update(selected_layers=layers,held_reply_alarm_by_seed=alarms[:,ids][:,held].mean(axis=1).tolist(),positive_reply_alarm_by_seed=alarms[:,ids][:,pos].mean(axis=1).tolist(),held_replies=int(held.sum()))
        if cohort=='matched':
            assert np.isfinite(rs[:,ids]).all()
            rm,rb=stream_metrics(rows,ids,y,rs[:,ids],fold[:,ids],reps)
            delta=boot['within_round']-rb['within_round']
            metrics.update(reasoning=rm,lastprompt_minus_reasoning=dict(estimate=metrics['within_round_auc']-rm['within_round_auc'],ci95=np.nanquantile(delta,[.025,.975]).tolist()),reasoning_held_reply_alarm_by_seed=ra[:,ids][:,held].mean(axis=1).tolist())
        key=f'{cohort}/{label}/{mode}';results[key]=metrics
        for si,seed in enumerate(SEEDS):
            for j,i in enumerate(ids):
                exports.append(dict(cohort=cohort,label_variant=label,analysis=mode,seed=seed,fold=int(fold[si,i]),row_id=rows[i]['row_id'],request_sha256=rows[i]['request_sha256'],label=int(y[j]),score=float(scores[si,i]),reasoning_score=float(rs[si,i]) if cohort=='matched' else '',alarm=bool(alarms[si,i]),episode=rows[i]['episode'],scenario=rows[i]['scenario'],round=rows[i]['round']))
        write_json_atomic(out/'metrics.json',results)
        print('METRIC',key,metrics['within_round_auc'],flush=True)
    with (out/'probe_scores.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(exports[0]));w.writeheader();w.writerows(exports)
    lines=['# Last-prompt per-call label ablation','',
      'Exploratory CPU fits on saved last-prompt activations, including the 146 first-public-emission calls. No replay or model API calls. The primary matched cohort excludes empty reasoning from both methods; the all-reply sensitivity retains it. Labels count eligible calls before filtering empty reasoning. Strict one-ahead removes own-leak calls from every fitting, validation and evaluation partition and labels only the preceding eligible call positive.','',
      'The paper recipe is unchanged: C=0.1 logistic regression, training-only StandardScaler, round-balanced weights (single-class rounds have zero weight), 17 candidate layers, frozen pooled-family and held-out-scenario outer/inner partitions, seeds 42/43/44. Layer selection maximises inner scenario × round AUROC, breaking ties toward the earlier layer. The original main plans are expanded by episode to include leaking calls. Thresholds use training-side no-ask control reply scores at nominal 5%, strict >; held recruiting rates below are evaluation results, not control FPR.','',
      '| Cohort / label / split | Rows / positives | Last prompt AUROC [95% CI] | Reasoning AUROC | Paired last prompt minus reasoning [95% CI] | Held-reply alarms: prompt / reasoning |',
      '|---|---:|---|---:|---|---|']
    for key,m in results.items():
        lo,hi=m['within_round_ci95'];r=m.get('reasoning');d=m.get('lastprompt_minus_reasoning')
        difference=f"{d['estimate']:+.3f} [{d['ci95'][0]:+.3f}, {d['ci95'][1]:+.3f}]" if d else '—'
        reason=f"{r['within_round_auc']:.3f}" if r else '—'
        alarm=f"{np.mean(m['held_reply_alarm_by_seed']):.1%} / "+(f"{np.mean(m['reasoning_held_reply_alarm_by_seed']):.1%}" if r else '—')
        lines.append(f"| {key} | {m['rows']} / {m['positives']} | {m['within_round_auc']:.3f} [{lo:.3f}, {hi:.3f}] | {reason} | {difference} | {alarm} |")
    lines+=['','Intervals use 1,000 family bootstrap draws (seed 20261025) of saved OOF scores, conditional on fitted/selected models. Paired differences use identical draws and rows. Immediate reasoning and last-prompt fits share the outcome and partitions; token pooling and token-weighted versus single-position fitting remain differences. Strict-one-ahead reasoning scores come from existing inclusive 0–1 horizon fits; only last-prompt is refit on strict labels. That comparison does not isolate position and must not be presented as a matched-label ablation. Alarm rates are reply-level, not episode-level intervention rates. Most strict-next positives are same-round read-file calls in the existing timing audit.','',
      'Sources: `runs/20261026-0522-e05-reasoning-stream-data`, `runs/20261025-2305-e05-gpt-oss-full-data`, frozen plans `runs/20261026-0138-e05-gpt-oss-main/plans.json`, reasoning fits `runs/20261026-0526-e05-reasoning-stream/{immediate,h1}/all`. Script: `experiments/E05-probes/lastprompt_percall.py`.']
    (out/'report.md').write_text('\n'.join(lines)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--limit',type=int);p.add_argument('--summarize-only',action='store_true');p.add_argument('--bootstrap',type=int,default=1000);a=p.parse_args()
    run=None
    if a.out:out=a.out
    else:
        run=start_run('e05-lastprompt-percall',experiment='E05',parents=[STREAM.name,DATA.name,FITS.name],settings={'C':.1,'layers':CANDIDATES,'threads':2,'seeds':SEEDS,'labels':['immediate','strict1'],'cohorts':['matched','all'],'no_api':True,'no_gpu':True})
        out=run.dir
    out.mkdir(parents=True,exist_ok=True);print('OUTPUT',out,flush=True)
    rows,base,x,plans=load()
    jobs=[(cohort,label,plan) for cohort in ['matched','all'] for label in ['immediate','strict1'] for plan in sorted(plans,key=lambda v:(v['mode']!='loso',v['seed'],v['fold']))]
    write_json_atomic(out/'analysis_plan.json',dict(jobs=len(jobs),source_plans=str(FITS/'plans.json'),source_features=str(DATA/'features.npy'),script=__file__,cohorts=['matched','all'],strict_label='distance exactly 1; own-leak calls excluded from all splits',reasoning_strict_comparator='inclusive h1 model; no strict refit'))
    try:
      with threadpool_limits(limits=2):
        if not a.summarize_only:
            for cohort,label,plan in jobs[:a.limit]:run_fit(out,rows,base,x,plan,label,cohort)
        if a.limit is None:summarize(out,rows,plans,a.bootstrap)
      if run:run.finish(status='complete' if a.limit is None else 'partial')
    except BaseException as e:
      if run:run.finish(status='failed',error=str(e))
      raise


if __name__=='__main__':main()
