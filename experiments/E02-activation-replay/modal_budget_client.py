"""Run one approved Modal phase with a conservative wall-cost watchdog and cleanup."""
import argparse
import json
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run

# Published A10080 + four cores + maximum64GiB RAM; rounding upward.
MAX_RATE_PER_SECOND=.00090

def main(args):
    command=['modal','run','experiments/E02-activation-replay/modal_app.py::main','--manifest-path',args.manifest,
             '--model','Qwen/Qwen3-32B','--revision','9216db5781bf21249d130ec9da846c4624c16137',
             '--source-model','qwen/qwen3-32b','--precision','bf16','--gpu',args.gpu,'--layers','all','--fidelity-tokens','64']
    run=start_run('e02-replay2-modal-client',experiment='E02',parents=[Path(args.manifest).parent.name],settings={'approval':'Aboard #609/#611 + direct user confirmation','total_approved_usd':12,'phase_ceiling_usd':args.phase_ceiling,'watchdog_max_resource_rate_per_second':MAX_RATE_PER_SECOND,'command':command})
    start=time.monotonic();app_id=None;remote=None;p=None;stopped=False;failure=None
    try:
        events=queue.Queue();p=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        def read():
            for line in p.stdout:events.put(line)
            events.put(None)
        threading.Thread(target=read,daemon=True).start()
        with (run.dir/'modal.log').open('w') as log:
            finished=False
            while not finished:
                if time.monotonic()-start > args.phase_ceiling/MAX_RATE_PER_SECOND-30:
                    raise TimeoutError('Conservative phase cost watchdog reached')
                try:line=events.get(timeout=1)
                except queue.Empty:continue
                if line is None:finished=True;continue
                log.write(line);log.flush()
                match=re.search(r'\bap-[A-Za-z0-9]+\b',line)
                if match:
                    if app_id is not None and app_id!=match.group():raise RuntimeError('Ambiguous Modal app ID')
                    app_id=match.group();(run.dir/'app-id.txt').write_text(app_id)
                match=re.search(r'modal volume get collusion-activations (runs/[^\s]+)',line)
                if match:remote=match.group(1)
                if any(k in line for k in ['PROGRESS','https://modal.com/apps','modal volume get','Traceback','Error']):print(line.rstrip(),flush=True)
        code=p.wait()
        if code:raise RuntimeError(f'Modal command exited {code}')
        if not app_id or not remote:raise RuntimeError('Missing app ID or completed output path')
    except BaseException as exc:failure=exc
    finally:
        if app_id:
            info=subprocess.run(['modal','app','info',app_id,'--json'],capture_output=True,text=True)
            if info.returncode==0:
                data=json.loads(info.stdout);(run.dir/'app-before-stop.json').write_text(info.stdout)
                stopped=data['lifecycle']['state']=='stopped'
            if not stopped:subprocess.run(['modal','app','stop',app_id],check=True);stopped=True
            info=subprocess.run(['modal','app','info',app_id,'--json'],capture_output=True,text=True,check=True)
            (run.dir/'app.json').write_text(info.stdout);assert json.loads(info.stdout)['lifecycle']['state']=='stopped'
        if p is not None and p.poll() is None:p.terminate();p.wait(timeout=30)
        elapsed=time.monotonic()-start
        billing=[]
        if app_id:
            report=subprocess.run(['modal','billing','report','--for','today','--resolution','h','--show-resources','--json'],capture_output=True,text=True,check=True)
            billing=[r for r in json.loads(report.stdout) if r.get('object_id')==app_id]
            (run.dir/'billing.json').write_text(json.dumps(billing,indent=2))
        summary=dict(app_id=app_id,remote_path=remote,app_stopped=stopped,client_wall_seconds=elapsed,
                     conservative_compute_upper_usd=elapsed*MAX_RATE_PER_SECOND,billed_so_far_usd=sum(float(r['cost']) for r in billing),billing_may_lag=True,error=str(failure) if failure else None)
        (run.dir/'summary.json').write_text(json.dumps(summary,indent=2));run.result(**summary)
        run.finish('failed' if failure else 'finished',str(failure) if failure else None)
    print(json.dumps(summary,indent=2));print('CLIENT_RUN',run.id)
    if failure:raise failure

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--gpu',choices=['a100','a100-benchmark'],required=True);p.add_argument('--phase-ceiling',type=float,required=True);main(p.parse_args())
