"""Author-respecified fixed layer18, seed42 LOSO, immediate CC++ fits."""
import argparse,json,time
from pathlib import Path
from stream_capture_fit import job,FITS
from collusion.runs import start_run,write_json_atomic
import subprocess

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);a=p.parse_args()
 plans=[p for p in json.loads((FITS/'plans.json').read_text()) if p['window']=='post_ask' and p['variant']=='eventual' and p['mode']=='loso' and p['seed']==42];assert len(plans)==6
 run=start_run('e05-stream-layer18-loso',experiment='E05',parents=[a.data.name,FITS.name],tags=['exploratory','cpu-only'],settings={'author_decision':'Aboard1823','layer':18,'layer_choice':'fixed before fitting respecified run, not outcome-selected','training_tokens_per_reply_max':64,'subsampling':'evenly spaced including endpoints; SWiM16 runs on sampled sequence, so its original-token span may exceed16','scoring':'all stream tokens','seed':42,'split':'LOSO6rotations','variant':'immediate','loss':'both','streams':['incoming','action_time'],'C':.1,'ema_alpha':2/17})
 print('SMALL_RUN',run.dir,flush=True);done=[];begin=time.monotonic()
 try:
  for plan in plans:
   for stream in ['incoming','action_time']:
    result=job(a.data,run.dir,plan,'layer18','immediate','both',stream,max_train_tokens=64);done.append(result['total_seconds'])
    write_json_atomic(run.dir/'progress.json',{'complete':len(done),'total':12,'fit_seconds':done,'elapsed_seconds':time.monotonic()-begin})
    print('DONE',stream,plan['fold'],result['total_seconds'],flush=True)
    if len(done)==1:
     seconds=done[0];subprocess.run(['aboard','say','--reply','1823',f'@codex-2 @claude: first respecified layer18/64-training-token fit completed in {seconds/60:.2f} min. Simple 12-fit projection {seconds*12/60:.1f} min (incoming first; action-time may differ). Run {run.dir}; all scoring positions retained. Check next paired fit before treating this as final ETA.'],check=True)
  run.result(fits=12,seconds=time.monotonic()-begin);run.finish()
  subprocess.run(['aboard','say','--reply','1823','@codex-2 @claude: all12 respecified single-seed layer18 LOSO fits complete at '+str(run.dir)+'. Reporting/nulls/lead/prevention checks are next; no wider grid resumed.'],check=True)
 except BaseException as e:
  run.finish('failed',str(e));subprocess.run(['aboard','say','--reply','1823','@codex-2 @claude: respecified CPU fit failed; inspect private/stream-layer18.log. Completed files preserved; no paid compute.']);raise
