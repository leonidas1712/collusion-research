"""Exploratory, reply-weighted token probes using frozen episode partitions."""
import argparse
import json
from pathlib import Path
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits
from metrics import position_weights, within_round, threshold_at_fpr
from reasoning_stream_data import ROOT, DATA, FITS
from reasoning_stream_labels import add_horizon_labels,VARIANTS
from collusion.runs import start_run, write_json_atomic

LAYERS = [0,1,3,4,6,7,9,10,12,13,15,16,18,19,20,22,23]

def tokens(rows, indices, clean):
    return np.concatenate([np.arange(rows[i]['start'], rows[i]['start'] + rows[i]['clean_tokens' if clean else 'reasoning_tokens']) for i in indices])

def fit(x, rows, indices, label, clean, seed):
    y = np.array([rows[i][label] for i in indices])
    rw = position_weights(y, [rows[i]['round'] for i in indices])
    indices = np.array(indices)[rw > 0]; y = y[rw > 0]; rw = rw[rw > 0]
    lengths = np.array([rows[i]['clean_tokens' if clean else 'reasoning_tokens'] for i in indices])
    ix = tokens(rows, indices, clean)
    xx = np.asarray(x[ix], dtype=np.float64)
    # Each reply contributes one unit of scaler mass and its round-balanced
    # reply weight to the loss, independent of reasoning length.
    scaler = StandardScaler().fit(xx, sample_weight=np.repeat(1 / lengths, lengths))
    xx = scaler.transform(xx, copy=False)
    clf = LogisticRegression(C=.1, solver='lbfgs', max_iter=2000, tol=1e-5, random_state=seed)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', ConvergenceWarning)
        clf.fit(xx, np.repeat(y, lengths), sample_weight=np.repeat(rw / lengths, lengths))
    if any(issubclass(w.category, ConvergenceWarning) for w in caught):
        raise RuntimeError('Token logistic failed to converge')
    return scaler.mean_, scaler.scale_, clf.coef_[0], float(clf.intercept_[0])

def predict(model, x, rows, indices, clean):
    mean, scale, coef, intercept = model
    direction = coef / scale
    bias = intercept - mean @ direction
    return [np.asarray(x[rows[i]['start']:rows[i]['start'] + rows[i]['clean_tokens' if clean else 'reasoning_tokens']], dtype=np.float64) @ direction + bias for i in indices]

def run_job(data, out, plan, variant, clean):
    begin = time.monotonic()
    name = f"{variant}/{'censored' if clean else 'all'}/{plan['mode']}/s{plan['seed']}-f{plan['fold']}"
    dest = Path(out)/name
    if (dest/'fit.json').exists(): return name, 'cached'
    rows = add_horizon_labels(json.loads((Path(data)/'replies.json').read_text()))
    base = [json.loads(s) for s in (DATA/'rows.jsonl').read_text().splitlines()]
    x = np.load(Path(data)/'reasoning.npy', mmap_mode='r')
    length = 'clean_tokens' if clean else 'reasoning_tokens'
    split = {}
    for key, ids in plan['split'].items():
        episodes = {base[i]['episode'] for i in ids}
        split[key] = [i for i,r in enumerate(rows) if r['episode'] in episodes and r['stream_window']=='post_ask' and r[length]>0 and (r['condition']=='control' if key=='calibration' else r['condition']=='recruiting')]
    for left,right in [('train','test'),('inner_train','inner_validation'),('train','calibration')]:
        assert not {rows[i]['episode'] for i in split[left]} & {rows[i]['episode'] for i in split[right]}
    assert not {rows[i]['family'] for i in split['train']} & {rows[i]['family'] for i in split['test']}
    label = 'y_'+variant
    validation = split['inner_validation']
    vy = [rows[i][label] for i in validation]
    vr = [rows[i]['round'] for i in validation]
    vs = [rows[i]['scenario'] for i in validation]
    candidates = []
    with threadpool_limits(limits=2):
        for layer in LAYERS:
            model = fit(x[layer], rows, split['inner_train'], label, clean, plan['seed'])
            pred = predict(model,x[layer],rows,validation,clean)
            value = within_round(vy,[p.max() for p in pred],vr,stratum_key=vs)[0]
            if not np.isfinite(value): raise ValueError('Inner validation AUROC undefined')
            candidates.append({'layer':layer,'auc':value})
            print('LAYER',name,layer,round(time.monotonic()-begin,1),flush=True)
        layer = max(candidates,key=lambda v:v['auc'])['layer']
        model = fit(x[layer],rows,split['train'],label,clean,plan['seed'])
        cal = predict(model,x[layer],rows,split['calibration'],clean)
        threshold, calibration = threshold_at_fpr([p.max() for p in cal],split['calibration'],.05)
        test_eps = {base[i]['episode'] for i in plan['split']['test']}
        evaluation = split['test'] + [i for i,r in enumerate(rows) if r['episode'] in test_eps and r['condition']=='recruiting' and r['stream_window']=='pre_ask' and r[length]>0]
        pred = predict(model,x[layer],rows,evaluation,clean)
    dest.mkdir(parents=True,exist_ok=True)
    np.savez(dest/'model.npz',mean=model[0],scale=model[1],coef=model[2],intercept=model[3])
    offsets = np.r_[0,np.cumsum([len(p) for p in pred])]
    np.savez(dest/'scores.npz',indices=evaluation,offsets=offsets,token_scores=np.concatenate(pred),max_scores=[p.max() for p in pred],mean_scores=[p.mean() for p in pred])
    write_json_atomic(dest/'fit.json',{'layer':layer,'candidates':candidates,'threshold':threshold,'calibration':calibration,'calibration_unit':'control reply maximum','split':split,'plan':plan,'variant':variant,'clean':clean,'seconds':time.monotonic()-begin})
    return name, time.monotonic()-begin

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out');p.add_argument('--workers',type=int,default=2);p.add_argument('--limit',type=int);a=p.parse_args()
    plans=[p for p in json.loads((FITS/'plans.json').read_text()) if p['window']=='post_ask' and p['variant']=='eventual']
    assert len(plans)==33
    run=None
    if a.out: out=Path(a.out)
    else:
        run=start_run('e05-reasoning-stream',experiment='E05',parents=[Path(a.data).name,FITS.name],tags=['exploratory','cpu-only'],settings={'layers':LAYERS,'reply_weighted':True,'C':.1,'selection':'inner reply-max within scenario x round','labels':['immediate any-public','near any-public'],'calibration':'training controls, reply max, strict >, 5%'})
        out=run.dir
    jobs=[(a.data,str(out),p,v,c) for v in ['immediate','round','h1','h2','h3'] for c in [False,True] for p in plans]
    if a.limit:jobs=jobs[:a.limit]
    print('OUTPUT',out,flush=True)
    write_json_atomic(out/'analysis_plan.json',{'data':a.data,'source_plans':str(FITS/'plans.json'),'layers':LAYERS,'jobs':len(jobs),'variants':VARIANTS,'horizon_definition':'eligible reply distance including empty reasoning; round comparator uses frozen channel outcome','complete':False})
    try:
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            futures=[pool.submit(run_job,*j) for j in jobs]
            for f in as_completed(futures):print('DONE',*f.result(),flush=True)
        write_json_atomic(out/'fits_complete.json',{'jobs':len(jobs),'limited':bool(a.limit)})
        if run:run.finish(status='complete')
    except BaseException as e:
        if run:run.finish(status='failed',error=str(e))
        raise

if __name__=='__main__':main()
