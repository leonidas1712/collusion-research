"""Serial expanded fits, prioritizing complete seed-42 interim folds."""
import argparse
import json
from pathlib import Path
import time
from stream_capture_fit import job,FITS,ROOT
from collusion.runs import start_run,write_json_atomic

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path);a=p.parse_args()
 plans=[p for p in json.loads((FITS/'plans.json').read_text()) if p['window']=='post_ask' and p['variant']=='eventual'];assert len(plans)==33
 priority=[p for p in plans if p['mode']=='pooled' and p['seed']==42];remaining=[p for p in plans if p not in priority]
 run=start_run('e05-expanded-stream',experiment='E05',parents=[a.data.name,FITS.name],tags=['cpu-only','exploratory'],settings={'streams':['last_prompt','reasoning','incoming','action_time'],'views':['projected','full'],'ablations':['uniform','swim','softmax','both'],'variants':['immediate','round','h1','h2','h3'],'priority':'author1820: main full4 both/uniform k0/round pooledseed42 thenLOSOseed42 before widergrid','fixed_views':True,'candidate_layer_selection':'none; fixed4full layers or all24independent256sketches','single_token_ablations':'mathematically identical, alias uniform fit'})
 out=a.out or run.dir
 print('BATCH_RUN',out,flush=True);completed=[]
 tasks=[]
 def add(partitions,variants,streams,views,ablations):
  for ablation in ablations:
   for stream in streams:
    for variant in variants:
     for view in views:
      for plan in partitions:
       item=(plan,view,variant,ablation,stream)
       if item not in tasks:tasks.append(item)
 main_streams=['reasoning','incoming','action_time']
 # Author-prioritized complete single-seed headline cells, not outer-score selection.
 add(priority,['immediate','round'],main_streams,['full'],['both','uniform'])
 loso42=[p for p in plans if p['mode']=='loso' and p['seed']==42]
 add(loso42,['immediate','round'],main_streams,['full'],['both','uniform'])
 add(priority,['immediate','round'],['last_prompt','reasoning','incoming','action_time'],['projected','full'],['both','uniform','swim','softmax'])
 add(remaining,['immediate','round'],['last_prompt','reasoning','incoming','action_time'],['projected','full'],['both','uniform','swim','softmax'])
 add(plans,['h1','h2','h3'],['last_prompt','reasoning','incoming','action_time'],['projected','full'],['both','uniform','swim','softmax'])
 write_json_atomic(out/'batch_plan.json',{'data':str(a.data),'jobs':len(tasks),'tasks':[{'seed':p['seed'],'fold':p['fold'],'mode':p['mode'],'view':v,'variant':y,'ablation':l,'stream':s} for p,v,y,l,s in tasks]})
 try:
  for n,args in enumerate(tasks):
   result=job(a.data,out,*args);completed.append({k:result[k] for k in ['stream','view','variant','ablation','total_seconds']})
   write_json_atomic(out/'progress.json',{'completed':n+1,'total':len(tasks),'fits':completed})
   print('DONE',n+1,len(tasks),args[1:],result['total_seconds'],flush=True)
  run.result(jobs=len(tasks));run.finish()
 except BaseException as e:
  run.finish('failed',str(e));raise
