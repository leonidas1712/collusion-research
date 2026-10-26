"""Rescore saved input-monitor and workflow baselines on Qwen development calls."""
import argparse,csv,gzip,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from threadpoolctl import threadpool_limits
from collusion.runs import start_run,write_json_atomic
from reasoning_stream_report import stream_metrics
from reasoning_stream_immediate_readstep import structural

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(audit,fits,restore):
    audit=audit.resolve();fits=fits.resolve()
    rows=json.loads((audit/'rows.json').read_text());ids=np.array([i for i,r in enumerate(rows) if r['index']<6026 and r['condition']=='recruiting'])
    lookup={f"{rows[i]['episode']}::request_idx={rows[i]['request_idx']}":i for i in ids}
    monitor=ROOT/'runs/20261026-1309-e06-percall-input-jev-qwen/probe_scores.csv'
    if not monitor.exists():shutil.copyfile(restore/monitor.relative_to(ROOT),monitor)
    seen={};hashes={}
    for r in csv.DictReader(monitor.open()):
        if r['row_id'] not in lookup:continue
        i=lookup[r['row_id']];assert r['request_sha256']==rows[i]['request_sha256']
        if i in seen:assert seen[i]==float(r['score'])
        seen[i]=float(r['score'])
    assert set(seen)==set(ids)
    probe=np.full((3,len(rows)),np.nan);fold=np.full(probe.shape,-1)
    alarms=np.zeros(probe.shape,bool)
    files=list((fits/'immediate/loso').glob('*/fit.json'));assert len(files)==18
    for p in files:
        f=json.loads(p.read_text());z=np.load(p.parent/'scores.npz');si=f['seed']-42;ii=z['indices']
        assert np.isnan(probe[si,ii]).all();probe[si,ii]=z['scores'];fold[si,ii]=f['fold'];alarms[si,ii]=z['scores']>f['threshold']
    assert np.isfinite(probe[:,ids]).all()
    incoming=[];previous=[];cache={}
    for i in ids:
        row=rows[i];folder,name=row['episode'].split('/');p=ROOT/'runs'/folder/'episodes'/name
        if row['episode'] not in cache:cache[row['episode']]=json.loads(p.read_text())
        a,b=structural(cache[row['episode']],row['request_idx']);incoming.append(a);previous.append(b)
    y=np.array([rows[i]['y_immediate'] for i in ids]);methods=dict(probe=probe[:,ids],jev=np.tile([seen[i] for i in ids],(3,1)),read_flag=np.tile(incoming,(3,1)),previous_read=np.tile(previous,(3,1)))
    run=start_run('e05-arxiv-qwen-controls',experiment='E05',parents=[fits.name,monitor.parent.name],tags=['cpu-only'],settings={'monitor_sha256':sha(monitor),'rows_sha256':sha(audit/'rows.json'),'same_calls':True})
    try:
      results={};boots={};paired={}
      with threadpool_limits(limits=2):
        for name,score in methods.items():results[name],boots[name]=stream_metrics(rows,ids,y,score,fold[:,ids],1000)
        for name in ['jev','read_flag','previous_read']:
            delta=boots['probe']['within_round']-boots[name]['within_round'];paired['probe_minus_'+name]=dict(estimate=results['probe']['within_round_auc']-results[name]['within_round_auc'],ci95=np.nanquantile(delta,[.025,.975]).tolist())
        keep=np.array(incoming,dtype=bool)
        for name in ['probe','jev']:
            results[name+'_within_postread']=stream_metrics(rows,ids[keep],y[keep],methods[name][:,keep],fold[:,ids][:,keep],1000)[0]
      result=dict(metrics=results,paired=paired,coverage=dict(expected=len(ids),monitor_available=len(seen),missing=0),
        structural_counts=dict(postread_calls=int(sum(incoming)),postread_positive=int(sum(y[np.array(incoming,dtype=bool)]))),
        primary_label='any public emission',dataset='Qwen development episodes',api_spend_usd=0)
      write_json_atomic(run.dir/'metrics.json',result)
      run.result(coverage=len(ids),jev_auc=results['jev']['within_round_auc']);run.finish();print(run.dir);print(json.dumps(result,indent=2))
    except BaseException as e:run.finish('failed',str(e));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True);p.add_argument('--fits',type=Path,required=True);p.add_argument('--restore-root',type=Path,required=True);a=p.parse_args();main(a.audit,a.fits,a.restore_root)
