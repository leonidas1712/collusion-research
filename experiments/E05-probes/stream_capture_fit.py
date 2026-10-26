"""Fixed-view streaming ablations on the frozen family and scenario partitions."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from threadpoolctl import threadpool_limits
from reasoning_stream_data import ROOT,DATA,FITS
from reasoning_stream_labels import add_horizon_labels
from metrics import position_weights,threshold_at_fpr
from stream_model import fit,predict
from stream_loss import inference_scores
from collusion.runs import start_run,write_json_atomic

ABLATIONS={'uniform':(False,False),'swim':(True,False),'softmax':(False,True),'both':(True,True)}

def job(data,out,plan,view,variant,ablation,stream="action_time",max_train_tokens=None):
    dest=out/stream/view/variant/ablation/plan['mode']/f"s{plan['seed']}-f{plan['fold']}"
    if (dest/'fit.json').exists():return json.loads((dest/'fit.json').read_text())
    if stream=='last_prompt' and ablation!='uniform':
        import shutil
        result=job(data,out,plan,view,variant,'uniform',stream)
        origin=out/stream/view/variant/'uniform'/plan['mode']/f"s{plan['seed']}-f{plan['fold']}"
        dest.mkdir(parents=True,exist_ok=True)
        for name in ['model.npz','scores.npz']:shutil.copyfile(origin/name,dest/name)
        result={**result,'ablation':ablation,'equivalent_single_token_alias':str(origin),'total_seconds':0}
        write_json_atomic(dest/'fit.json',result);return result
    rows=add_horizon_labels(json.loads((data/'replies.json').read_text()))
    positions=np.load(data/'positions.npz')
    for r in rows:
        ids=np.arange(r['capture_start'],r['capture_stop']);role=positions['roles'][ids]
        mask=np.ones(len(ids),dtype=bool) if stream=='action_time' else role==0 if stream=='incoming' else role==4 if stream=='last_prompt' else np.isin(positions['positions'][ids],r['reasoning_positions'])
        r['capture_indices']=ids[mask];r['capture_tokens']=int(mask.sum())
    base=[json.loads(s) for s in (DATA/'rows.jsonl').read_text().splitlines()]
    split={}
    for name,ids in plan['split'].items():
        episodes={base[i]['episode'] for i in ids}
        split[name]=[i for i,r in enumerate(rows) if r['capture_tokens']>0 and r['episode'] in episodes and r['condition']==('control' if name=='calibration' else 'recruiting')]
    for left,right in [('train','test'),('inner_train','inner_validation')]:
        assert not {rows[i]['family'] for i in split[left]} & {rows[i]['family'] for i in split[right]}
    x=np.load(data/('full.npy' if view=='layer18' else view+'.npy'),mmap_mode='r')
    if view=='layer18':x=x[:,2,:]
    train=split['train'];y=np.array([rows[i]['y_'+variant] for i in train]);rw=position_weights(y,[rows[i]['round'] for i in train])
    begin=time.monotonic()
    with threadpool_limits(limits=2):
        training_rows=rows
        if max_train_tokens:
            training_rows=[dict(r) for r in rows]
            for i in train:
                ix=rows[i]['capture_indices'];take=np.unique(np.linspace(0,len(ix)-1,min(len(ix),max_train_tokens),dtype=int))
                training_rows[i]['capture_indices']=ix[take];training_rows[i]['capture_tokens']=len(take)
        model,diagnostics=fit(x,training_rows,train,y,rw,swim=ABLATIONS[ablation][0],weighted=ABLATIONS[ablation][1])
        calibration=predict(model,x,rows,split['calibration']);test=predict(model,x,rows,split['test'])
    thresholds={};statistics={};payload={}
    for aggregation in ['raw','ema','rolling10']:
        cal=[inference_scores(z)[aggregation].max() for z in calibration]
        threshold,info=threshold_at_fpr(cal,split['calibration'],.05)
        thresholds[aggregation]=threshold;statistics[aggregation]=info
        streams=[inference_scores(z)[aggregation] for z in test]
        payload[aggregation+'_max']=np.array([z.max() for z in streams])
        payload[aggregation+'_first_alarm']=np.array([int(h[0]) if len(h:=np.flatnonzero(z>threshold)) else -1 for z in streams])
    dest.mkdir(parents=True,exist_ok=True);np.savez(dest/'model.npz',**model)
    np.savez(dest/'scores.npz',indices=split['test'],offsets=np.r_[0,np.cumsum([len(z) for z in test])],token_logits=np.concatenate(test),**payload)
    result={'max_train_tokens':max_train_tokens,'training_subsample':'evenly spaced, endpoints included; SWiM over sampled sequence' if max_train_tokens else None,'scoring_tokens':'all selected stream positions','stream':stream,'view':view,'variant':variant,'ablation':ablation,'plan':plan,'split':split,'C':.1,'swim_window':16,'tau':1,'ema_alpha':2/17,'rolling_window':10,'fixed_view_no_layer_selection':True,'thresholds':thresholds,'calibration':statistics,'diagnostics':diagnostics,'total_seconds':time.monotonic()-begin}
    write_json_atomic(dest/'fit.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path);p.add_argument('--stream',choices=['action_time','reasoning','incoming','last_prompt'],default='action_time');p.add_argument('--benchmark',action='store_true');p.add_argument('--view',choices=['full','projected','layer18'],default='full');p.add_argument('--variant',default='immediate');p.add_argument('--ablation',choices=ABLATIONS,default='uniform');a=p.parse_args()
    plans=[p for p in json.loads((FITS/'plans.json').read_text()) if p['window']=='post_ask' and p['variant']=='eventual'];assert len(plans)==33
    run=start_run('e05-expanded-stream-benchmark' if a.benchmark else 'e05-expanded-stream-fit',experiment='E05',parents=[a.data.name,FITS.name],tags=['exploratory','cpu-only'],settings={'view':a.view,'variant':a.variant,'ablation':a.ablation,'benchmark':a.benchmark,'fixed_features':True,'no_outcome_based_view_selection':True})
    try:
        out=a.out or run.dir;results=[]
        chosen=[p for p in plans if p['mode']=='pooled' and p['seed']==42 and p['fold']==0] if a.benchmark else plans
        for plan in chosen:results.append(job(a.data,out,plan,a.view,a.variant,a.ablation,a.stream))
        run.result(fits=len(results),seconds=sum(r['total_seconds'] for r in results));run.finish();print('FIT_RUN',run.dir,flush=True)
    except BaseException as e:run.finish('failed',str(e));raise
