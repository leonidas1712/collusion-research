"""Report only complete seed-42 pooled cells from the stopped expanded grid."""
import argparse,json
from pathlib import Path
import numpy as np
from reasoning_stream_labels import add_horizon_labels
from reasoning_stream_report import stream_metrics
from collusion.runs import write_json_atomic

def report(out,data):
 rows=add_horizon_labels(json.loads((data/'replies.json').read_text()));results={};coverage={}
 for stream in ['reasoning','incoming','action_time']:
  for variant in ['immediate','round']:
   key=f'{stream}/full/{variant}/both/pooled';files=sorted((out/key).glob('s42-f*/fit.json'));coverage[key]=len(files)
   if len(files)!=5:continue
   ids=[];scores=[];folds=[];hit=[]
   for path in files:
    fit=json.loads(path.read_text());z=np.load(path.parent/'scores.npz');ids.extend(z['indices'].tolist());scores.extend(z['ema_max'].tolist());folds.extend([fit['plan']['fold']]*len(z['indices']));hit.extend((z['ema_max']>fit['thresholds']['ema']).tolist())
   assert len(ids)==len(set(ids));ids=np.array(ids);scores=np.array(scores);y=np.array([rows[i]['y_'+variant] for i in ids]);hit=np.array(hit)
   r=stream_metrics(rows,ids,y,scores[None,:],np.array(folds)[None,:],1000)[0]
   pos=np.array([rows[i]['y_immediate']==1 for i in ids]);held=np.array([not rows[i]['ever_public'] for i in ids])
   r.update(immediate_reply_warning=float(hit[pos].mean()),held_reply_alarm=float(hit[held].mean()),seed=42,aggregation='EMA max, alpha2/17',folds=5)
   results[key]=r
 write_json_atomic(out/'stopped_grid_interim.json',{'completed_fold_counts':coverage,'metrics':results,'scope':'single seed42 pooled only; full4layers,bothloss,EMA; incomplete cells omitted from AUROC'})
 lines=['# Stopped expanded-grid interim: single seed 42, pooled family CV','','This is an exploratory interim from the stopped four-layer concatenation grid. Only complete five-fold pooled cells are reported. It is not LOSO, not a three-seed estimate, and not the final respecified one-layer analysis. The completed priority grid contains 22 fit files: four complete five-fold cells and two action-time immediate folds. The two action-time folds are preserved but excluded from aggregate estimates.','','| Stream | Label | Replies / positives | Within scenario × round AUROC [95% family CI] | Immediate-reply warning | Held-reply alarms |','|---|---|---:|---|---:|---:|']
 for key,r in results.items():
  stream,_,variant,_,_=key.split('/');lo,hi=r['within_round_ci95'];lines.append(f"| {stream} | {variant} | {r['rows']} / {r['positives']} | {r['within_round_auc']:.3f} [{lo:.3f}, {hi:.3f}] | {r['immediate_reply_warning']:.1%} | {r['held_reply_alarm']:.1%} |")
 lines+=['','Features concatenate full layers6,12,18,23. Both-loss means SWiM16 plus tau1 softmax-weighted BCE; EMA alpha2/17 is fixed. Control-reply thresholds are calibrated at nominal5% using training-side control maxima with strict >. The warning column always concerns immediate leaking replies, even when the model was trained on the round label. Family-bootstrap intervals condition on these fitted single-seed models. No outcomes were used to select the subsequent fixed layer18.','','Forecasting streams (reasoning and incoming) are shown above. Action-time aggregates remain pending and must not be substituted with the partial folds. Exact matching nulls, lead measurements and prevention estimates will be reported with the smaller LOSO run.','','Reproduce: `experiments/E05-probes/.venv/bin/python experiments/E05-probes/stream_capture_interim.py --out '+str(out)+' --data '+str(data)+'`. Existing per-fold model/scores/fit files are the source; no fits are performed by this script.']
 (out/'interim_report.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps(results,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--data',type=Path,required=True);a=p.parse_args();report(a.out,a.data)
