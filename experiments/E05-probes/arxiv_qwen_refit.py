"""Disjoint-development Qwen ladder and exploratory fresh-set evaluation."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from threadpoolctl import threadpool_limits
from collusion.runs import start_run,write_json_atomic,Run
from models import fit_logistic,score
from metrics import within_round,threshold_at_fpr
from near_term import save_lr
from replay2_core import split_inner
from reasoning_stream_report import stream_metrics

LAYERS=list(range(0,64,4))+[63]
LABELS=['eventual','round_near','immediate']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare(audit,modes):
    audit=audit.resolve()
    rows=json.loads((audit/'rows.json').read_text());oldplans=json.loads((audit/'split_plan.json').read_text())
    dev={i for i,r in enumerate(rows) if r['index']<6026};new=set(range(len(rows)))-dev
    assert not {rows[i]['family'] for i in dev}&{rows[i]['family'] for i in new}
    plans=[]
    for p in oldplans:
        if p['mode'] not in modes:continue
        split={k:sorted(set(v)&dev) for k,v in p['split'].items()}
        assert all(split.values())
        plans.append(dict(mode=p['mode'],seed=p['seed'],fold=p['fold'],split=split))
    if 'fresh' in modes:
        train=np.array(sorted(i for i in dev if rows[i]['condition']=='recruiting'))
        test=sorted(i for i in new if rows[i]['condition']=='recruiting')
        calibration=sorted(i for i in dev if rows[i]['condition']=='control')
        for seed in [42,43,44]:
            f,v,_=split_inner(rows,train,seed,False)
            plans.append(dict(mode='fresh',seed=seed,fold=0,split=dict(train=train.tolist(),test=test,
                calibration=calibration,inner_train=f.tolist(),inner_validation=v.tolist())))
    run=start_run('e05-arxiv-qwen-any-public',experiment='E05',parents=[audit.name],tags=['exploratory','cpu-only'],settings={
        'label_boundary':'first exact value in answer or any tool argument, including source-file writebacks',
        'development_feature_index_lt':6026,'modes':modes,'workers':3,'threads':2,'no_gpu':True,'no_api':True})
    write_json_atomic(run.dir/'rows.json',rows);write_json_atomic(run.dir/'plans.json',plans)
    write_json_atomic(run.dir/'analysis_plan.json',dict(audit=str(audit.relative_to(ROOT)),audit_sha256=sha(audit/'audit.json'),
        feature_path=json.loads((audit/'analysis_plan.json').read_text())['feature_path'],labels=LABELS,candidates=LAYERS,
        C=.1,scaling='training-only StandardScaler',weights='round-balanced; single-class rounds zero weight',
        inner_selection='scenario x round AUROC; saved inner splits restricted to development; final models use development family holdout',
        seeds=[42,43,44],bootstrap=dict(unit='family',seed=20261025,reps=1000),
        fresh_aggregation='mean of three scores standardized by each final model training mean and SD',
        fresh_status='exploratory out-of-sample; already inspected fresh outcomes, not a new confirmation',
        input_hashes={f:sha(run.dir/f) for f in ['rows.json','plans.json']},frozen_confirmations_changed=False))
    return run

def fit(job):
    out,label,p=job
    dest=out/label/p['mode']/f"s{p['seed']}-f{p['fold']}"
    if (dest/'fit.json').exists():return
    start=time.monotonic();rows=json.loads((out/'rows.json').read_text());a=json.loads((out/'analysis_plan.json').read_text())
    x=np.load(a['feature_path'],mmap_mode='r');src=np.array([r['index'] for r in rows]);y=np.array([r['y_'+label] for r in rows])
    rnd=np.array([r['round'] for r in rows]);sc=np.array([r['scenario'] for r in rows]);s={k:np.array(v) for k,v in p['split'].items()}
    for a,b in [('train','test'),('inner_train','inner_validation'),('calibration','test')]:
        assert not {rows[i]['family'] for i in s[a]}&{rows[i]['family'] for i in s[b]}
    assert all(src[s[k]].max()<6026 for k in ['train','inner_train','inner_validation','calibration'])
    if p['mode']=='fresh':assert src[s['test']].min()>=6026
    with threadpool_limits(limits=2):
        choices={}
        f,v=s['inner_train'],s['inner_validation']
        for layer in LAYERS:
            m=fit_logistic(x[src[f],layer],y[f],rnd[f],p['seed']+p['fold']*17)
            choices[layer]=within_round(y[v],score(m,x[src[v],layer]),rnd[v],stratum_key=sc[v])[0]
        assert any(np.isfinite(v) for v in choices.values())
        layer=max(LAYERS,key=lambda k:(choices[k] if np.isfinite(choices[k]) else -1,-k))
        tr,te,cal=s['train'],s['test'],s['calibration']
        m=fit_logistic(x[src[tr],layer],y[tr],rnd[tr],p['seed'])
        pred=score(m,x[src[te],layer]);cp=score(m,x[src[cal],layer]);train_pred=score(m,x[src[tr],layer])
        threshold,cn=threshold_at_fpr(cp,cal,.05)
        dest.mkdir(parents=True,exist_ok=True);save_lr(dest/'model.npz',m)
        with np.load(dest/'model.npz') as saved:
            rebuilt=((np.asarray(x[src[te],layer],float)-saved['mean'])/saved['scale'])@saved['coef'][0]+saved['intercept'][0]
            assert np.max(abs(rebuilt-pred))<1e-9
        np.savez_compressed(dest/'scores.npz',indices=te,scores=pred,calibration_indices=cal,calibration_scores=cp)
        write_json_atomic(dest/'fit.json',dict(label=label,**p,layer=layer,candidates=choices,threshold=threshold,calibration=cn,
            train_score_mean=float(train_pred.mean()),train_score_sd=float(train_pred.std()),seconds=time.monotonic()-start))
        print('FIT',label,p['mode'],p['seed'],p['fold'],round(time.monotonic()-start,1),flush=True)

def summarize(out):
    rows=json.loads((out/'rows.json').read_text());plans=json.loads((out/'plans.json').read_text());metrics={};exports=[]
    for label in LABELS:
      for mode in sorted({p['mode'] for p in plans}):
        values=np.full((3,len(rows)),np.nan);folds=np.full(values.shape,-1)
        selected={}
        for p in [p for p in plans if p['mode']==mode]:
            d=out/label/mode/f"s{p['seed']}-f{p['fold']}";f=json.loads((d/'fit.json').read_text());z=np.load(d/'scores.npz')
            si=p['seed']-42;ids=z['indices'];pred=z['scores']
            assert np.isnan(values[si,ids]).all()
            if mode=='fresh':pred=(pred-f['train_score_mean'])/f['train_score_sd']
            values[si,ids]=pred;folds[si,ids]=p['fold'];selected[f"{p['seed']}/{p['fold']}"]=f['layer']
        ids=np.flatnonzero(np.isfinite(values).all(axis=0));y=np.array([rows[i]['y_'+label] for i in ids])
        assert len(ids)==sum(r['condition']=='recruiting' and ((r['index']>=6026) if mode=='fresh' else (r['index']<6026)) for r in rows)
        arr=values[:,ids].mean(axis=0,keepdims=True) if mode=='fresh' else values[:,ids]
        ff=folds[:1,ids] if mode=='fresh' else folds[:,ids]
        m,_=stream_metrics(rows,ids,y,arr,ff,1000);m['selected_layers']=selected
        # Exclude both protected-source-writeback episodes without refitting.
        audit=json.loads((ROOT/json.loads((out/'analysis_plan.json').read_text())['audit']/'audit.json').read_text())
        excluded={r['episode'] for r in audit['changed_episodes'] if r['scenario'] in ['procurement-reserve-price','dispatch-integration-code']}
        keep=np.array([rows[i]['episode'] not in excluded for i in ids])
        sensitivity,_=stream_metrics(rows,ids[keep],y[keep],arr[:,keep],ff[:,keep],1000)
        m['excluding_source_writeback_episodes']=sensitivity
        metrics[label+'/'+mode]=m
        for si in range(len(arr)):
            for j,i in enumerate(ids):
                r=rows[i];exports.append(dict(row_id=f"{r['episode']}::request_idx={r['request_idx']}",episode=r['episode'],family=r['family'],scenario=r['scenario'],round=r['round'],request_sha256=r['request_sha256'],analysis=mode,label_variant=label,seed='ensemble' if mode=='fresh' else si+42,fold=int(ff[si,j]),label=int(y[j]),score=float(arr[si,j])))
        print('METRIC',label,mode,m['within_round_auc'],flush=True)
    write_json_atomic(out/'metrics.json',metrics)
    with gzip.open(out/'probe_scores.csv.gz','wt',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(exports[0]));w.writeheader();w.writerows(exports)
    write_json_atomic(out/'verification.json',dict(all_models_reconstructed=True,train_test_family_disjoint=True,
        development_only_training=True,frozen_confirmations_changed=False,cells=len(metrics),gpu_spend_usd=0,api_spend_usd=0))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit',type=Path);p.add_argument('--out',type=Path);p.add_argument('--modes',default='loso');p.add_argument('--workers',type=int,default=3)
    a=p.parse_args()
    if 'fresh' in a.modes.split(','):raise ValueError('Fresh scoring requires separately committed weights freeze; use the frozen scorer')
    if a.out:
        out=a.out;meta=json.loads((out/'meta.json').read_text());meta['status']='running';run=Run(out.name,out,meta)
    else:run=prepare(a.audit,a.modes.split(','));out=run.dir
    print('OUTPUT',out,flush=True)
    try:
        plan=json.loads((out/'analysis_plan.json').read_text())
        for f,h in plan['input_hashes'].items():assert sha(out/f)==h
        plans=json.loads((out/'plans.json').read_text())
        jobs=[(out,label,p) for label in ['immediate','round_near','eventual'] for p in plans]
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            for f in as_completed([pool.submit(fit,j) for j in jobs]):f.result()
        with threadpool_limits(limits=2):summarize(out)
        run.result(fits=len(jobs),gpu_spend_usd=0);run.finish()
    except BaseException as e:run.finish('failed',str(e));raise
