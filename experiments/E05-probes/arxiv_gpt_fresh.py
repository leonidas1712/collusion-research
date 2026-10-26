"""Freeze a development-only GPT-OSS input probe and evaluate saved fresh activations."""
import argparse,csv,gzip,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from threadpoolctl import threadpool_limits
from collusion.runs import start_run,write_json_atomic
from models import fit_logistic,score
from metrics import within_round,threshold_at_fpr
from replay2_core import split_inner
from reasoning_stream_report import stream_metrics
LAYERS=[0,1,3,4,6,7,9,10,12,13,15,16,18,19,20,22,23]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def freeze(saved_root):
    source=saved_root/'runs/20261026-0522-e05-reasoning-stream-data/replies.json'
    rows=[r for r in json.loads(source.read_text()) if r['stream_window']=='post_ask' and r['reasoning_tokens']>0]
    train=np.array([i for i,r in enumerate(rows) if r['condition']=='recruiting']);cal=np.array([i for i,r in enumerate(rows) if r['condition']=='control'])
    assert len(train)==1995 and len(cal)==892
    feature=saved_root/'runs/20261025-2305-e05-gpt-oss-full-data/features.npy';x=np.load(feature,mmap_mode='r')
    ix=np.array([r['index'] for r in rows]);y=np.array([r['y_immediate'] for r in rows]);rnd=np.array([r['round'] for r in rows]);sc=np.array([r['scenario'] for r in rows])
    fresh_source=saved_root/'runs/20261026-1302-e05-stream-confirm-score/probe_scores.csv'
    fresh=[]
    for r in csv.DictReader(fresh_source.open()):
        if r['condition']!='recruiting' or int(r['reasoning_tokens'])==0:continue
        for k in ['round','ordinal','y_immediate','reasoning_tokens']:r[k]=int(r[k])
        fresh.append(r)
    assert len(fresh)==594 and sum(r['y_immediate'] for r in fresh)==26
    assert not {str(r['family']) for r in rows}&{str(r['family']) for r in fresh}
    integrity=saved_root/'runs/20261026-1302-e05-stream-confirm-score/integrity.json'
    files={r['row_id']:r for r in json.loads(integrity.read_text())['files']}
    for r in fresh:
        r['artifact']=str(saved_root/files[r['row_id']]['path']);r['artifact_sha256']=files[r['row_id']]['sha256']
        assert Path(r['artifact']).exists()
    run=start_run('e05-arxiv-gpt-percall-freeze',experiment='E05',parents=['20261026-0522-e05-reasoning-stream-data','20261026-1302-e05-stream-confirm-score'],tags=['cpu-only'],settings={'test_scored':False})
    try:
      specs=[];cp=[]
      with threadpool_limits(limits=2):
        for seed in [42,43,44]:
            f,v,_=split_inner(rows,train,seed,False);choices={}
            for layer in LAYERS:
                m=fit_logistic(x[ix[f],layer],y[f],rnd[f],seed)
                choices[layer]=within_round(y[v],score(m,x[ix[v],layer]),rnd[v],stratum_key=sc[v])[0]
            layer=max(LAYERS,key=lambda k:(choices[k] if np.isfinite(choices[k]) else -1,-k));assert np.isfinite(choices[layer])
            m=fit_logistic(x[ix[train],layer],y[train],rnd[train],seed);tr=score(m,x[ix[train],layer]);cc=score(m,x[ix[cal],layer])
            mean=float(tr.mean());sd=float(tr.std());assert sd>0;cp.append((cc-mean)/sd)
            scaler,lr=m;weights=dict(mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=lr.coef_[0].tolist(),intercept=float(lr.intercept_[0]))
            path=run.dir/f'weights-s{seed}.json.gz'
            with gzip.open(path,'wt') as h:json.dump(weights,h)
            specs.append(dict(seed=seed,layer=layer,selection=choices,weights=str(path.relative_to(ROOT)),weights_sha256=sha(path),train_mean=mean,train_sd=sd))
            print('FROZEN_MODEL',seed,layer,flush=True)
      threshold,detail=threshold_at_fpr(np.mean(cp,axis=0),cal,.05)
      write_json_atomic(run.dir/'fresh_rows.json',fresh)
      plan=dict(model='GPT-OSS-20B',status='new held-out test on previously inspected episodes; separate from frozen reasoning confirmation',
        label='first exact value in answer or any tool arguments; private reasoning excluded',recipe=dict(C=.1,scaling='train-only StandardScaler',round_balanced=True,candidates=LAYERS,seeds=[42,43,44],inner='25% development family holdout',selection='within scenario x round AUROC; earliest layer tie',aggregation='mean of training-z-scored logits'),
        models=specs,threshold=threshold,calibration=detail,threshold_rule='strict >; 5% development control calls',
        metric='positive-weighted within scenario x round AUROC',bootstrap=dict(unit='family',reps=1000,seed=20261025),primary_comparison='AUROC vs 0.5',
        fresh_rows=str((run.dir/'fresh_rows.json').relative_to(ROOT)),fresh_rows_sha256=sha(run.dir/'fresh_rows.json'),
        training_replies_sha256=sha(source),fresh_saved_scores_sha256=sha(fresh_source),train_calls=1995,train_positives=121,test_calls=594,
        script_sha256=sha(Path(__file__)),fresh_predictions_computed=False,gpu_spend_usd=0)
      p=ROOT/'paper-arxiv/frozen/gpt_percall_plan.json';assert not p.exists();write_json_atomic(p,plan);write_json_atomic(run.dir/'freeze.json',plan)
      run.result(models=3,fresh_predictions_computed=False);run.finish();print('COMMIT_AND_PUSH_BEFORE_SCORING',p,flush=True)
    except BaseException as e:run.finish('failed',str(e));raise

def evaluate(path):
    path=path.resolve();plan=json.loads(path.read_text());rel=str(path.relative_to(ROOT))
    assert subprocess.check_output(['git','show','origin/followup:'+rel],cwd=ROOT)==path.read_bytes()
    assert sha(Path(__file__))==plan['script_sha256']
    rp=ROOT/plan['fresh_rows'];assert sha(rp)==plan['fresh_rows_sha256'];rows=json.loads(rp.read_text())
    weights=[]
    for s in plan['models']:
        p=ROOT/s['weights'];assert sha(p)==s['weights_sha256']
        assert subprocess.check_output(['git','show','origin/followup:'+s['weights']],cwd=ROOT)==p.read_bytes()
        with gzip.open(p,'rt') as f:weights.append(json.load(f))
    values=[]
    with threadpool_limits(limits=2):
      for r in rows:
        p=Path(r['artifact']);assert sha(p)==r['artifact_sha256']
        with np.load(p,allow_pickle=False) as a:
            x=a['residual_last'];assert x.shape==(24,2880) and np.isfinite(x).all()
            v=[]
            for s,w in zip(plan['models'],weights):
                z=((x[s['layer']].astype(float)-w['mean'])/w['scale'])@np.array(w['coef'])+w['intercept']
                v.append((z-s['train_mean'])/s['train_sd'])
            values.append(float(np.mean(v)))
    values=np.array(values);ids=np.arange(len(rows));y=np.array([r['y_immediate'] for r in rows])
    run=start_run('e05-arxiv-gpt-fresh-percall',experiment='E05',parents=[rp.parent.name],tags=['cpu-only','held-out'],settings={'plan_sha256':sha(path),'freeze_pushed_before_scoring':True})
    try:
        m,_=stream_metrics(rows,ids,y,values[None,:],np.zeros((1,len(rows)),int),1000)
        m.update(threshold=plan['threshold'],positive_alarms=int(sum((values>plan['threshold'])&(y==1))),positive_calls=int(y.sum()),all_negative_alarms=int(sum((values>plan['threshold'])&(y==0))),negative_calls=int(sum(y==0)))
        write_json_atomic(run.dir/'metrics.json',m)
        with gzip.open(run.dir/'probe_scores.csv.gz','wt',newline='') as f:
            fields=['row_id','episode','family','scenario','round','request_sha256','label','score'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
            for i,r in enumerate(rows):w.writerow({k:r[k] for k in fields if k not in ['label','score']}|dict(label=int(y[i]),score=float(values[i])))
        write_json_atomic(run.dir/'verification.json',dict(freeze_pushed=True,weights_pushed=True,script_unchanged=True,all_artifact_hashes_verified=True,no_refit=True))
        run.result(auc=m['within_round_auc']);run.finish();print(run.dir);print(json.dumps(m,indent=2))
    except BaseException as e:run.finish('failed',str(e));raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze-from-saved-root',type=Path);p.add_argument('--score',type=Path);a=p.parse_args();assert bool(a.freeze_from_saved_root)!=bool(a.score)
    if a.score:evaluate(a.score)
    else:freeze(a.freeze_from_saved_root)
