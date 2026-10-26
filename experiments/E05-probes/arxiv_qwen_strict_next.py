"""Development-only strict-next-call sensitivity, excluding emitting calls."""
import argparse,json,sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic
import arxiv_qwen_refit as core

def main(source):
 source=source.resolve();rows=json.loads((source/'rows.json').read_text());plans=json.loads((source/'plans.json').read_text());a=json.loads((source/'analysis_plan.json').read_text())
 for r in rows:r['y_strict1']=int(r['public_ordinal'] is not None and r['public_ordinal']-r['ordinal']==1)
 for p in plans:p['split']={k:[i for i in v if not rows[i]['y_immediate']] for k,v in p['split'].items()}
 run=start_run('e05-arxiv-qwen-strict-next',experiment='E05',parents=[source.name],settings={'label':'next completed eligible target call emits; own-emitting calls excluded','no_gpu':True,'no_api':True})
 try:
  write_json_atomic(run.dir/'rows.json',rows);write_json_atomic(run.dir/'plans.json',plans);a['labels']=['strict1'];a['input_hashes']={f:core.sha(run.dir/f) for f in ['rows.json','plans.json']};write_json_atomic(run.dir/'analysis_plan.json',a)
  with ProcessPoolExecutor(max_workers=3) as pool:
   for f in as_completed([pool.submit(core.fit,(run.dir,'strict1',p)) for p in plans]):f.result()
  core.LABELS=['strict1']
  # Summarizer's full-cohort assertion is inappropriate for the intentionally reduced window.
  rows_meta=rows;results={};exports=[]
  import numpy as np,gzip,csv
  from reasoning_stream_report import stream_metrics
  values=np.full((3,len(rows)),np.nan);folds=np.full(values.shape,-1)
  for p in plans:
   d=run.dir/'strict1'/p['mode']/f"s{p['seed']}-f{p['fold']}";z=np.load(d/'scores.npz');i=z['indices'];values[p['seed']-42,i]=z['scores'];folds[p['seed']-42,i]=p['fold']
  ids=np.flatnonzero(np.isfinite(values).all(axis=0));y=np.array([rows[i]['y_strict1'] for i in ids]);assert len(ids)==2910
  m,_=stream_metrics(rows,ids,y,values[:,ids],folds[:,ids],1000);write_json_atomic(run.dir/'metrics.json',m)
  with gzip.open(run.dir/'probe_scores.csv.gz','wt',newline='') as f:
   fields=['row_id','episode','family','scenario','round','label','seed','fold','score'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
   for si in range(3):
    for i in ids:
     r=rows[i];w.writerow(dict(row_id=f"{r['episode']}::request_idx={r['request_idx']}",**{k:r[k] for k in ['episode','family','scenario','round']},label=r['y_strict1'],seed=si+42,fold=int(folds[si,i]),score=float(values[si,i])))
  run.result(auc=m['within_round_auc'],calls=len(ids),positives=int(y.sum()));run.finish();print(run.dir)
 except BaseException as e:run.finish('failed',str(e));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);main(p.parse_args().source)
