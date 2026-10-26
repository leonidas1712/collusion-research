"""Shared USD20 full-replay ledger and process watchdog; always stops its Modal app."""
import argparse
import json
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic
RATE=.00090
CAP=20.
OVERHEAD=.50


def main(plan_path):
    plan_path=Path(plan_path).resolve();plan=json.loads(plan_path.read_text())
    assert plan.get('rendering_gate_approval'), 'Provider rendering gate is pending author decision (#1173); do not launch this plan'
    budget_root=Path(plan.get('budget_root',plan_path.parent));budget_root.mkdir(parents=True,exist_ok=True)
    ledger_path=budget_root/'clients.json';journal=plan_path.parent/'completed-shards.json'
    previous=json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    spent=0.
    for path in previous:
        summary=json.loads((Path(path)/'summary.json').read_text())
        assert summary['app_stopped'],'Previous app must be stopped before restart'
        spent+=max(summary['conservative_compute_upper_usd'],summary['billed_so_far_usd'])
    remaining=min(CAP-OVERHEAD-spent,float(plan.get('phase_ceiling_usd',CAP)))
    assert remaining>0
    assert plan['counts']['prior_projection_usd_with_2x_margin']<=remaining+OVERHEAD,'Prior projection exceeds phase/shared remainder'
    run=start_run('e02-gpt-oss-full-client',experiment='E02',parents=[plan_path.parent.name],
        settings={'approval':'full replay and addressee audit: USD20 total','cap_usd':CAP,'prior_upper_usd':spent,
                  'overhead_reserve_usd':OVERHEAD,'remaining_usd':remaining,'rate_per_second':RATE,'plan':str(plan_path)})
    write_json_atomic(ledger_path,[*previous,str(run.dir.resolve())])
    command=['modal','run','experiments/E02-activation-replay/modal_gpt_oss_full.py','--plan',str(plan_path),
             '--journal',str(journal),'--remaining-usd',str(remaining)]
    start=time.monotonic();app_id=None;p=None;stopped=False;failure=None;done=False
    try:
        events=queue.Queue();p=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        def read():
            for line in p.stdout:events.put(line)
            events.put(None)
        threading.Thread(target=read,daemon=True).start()
        with (run.dir/'modal.log').open('w') as log:
            while True:
                if time.monotonic()-start>remaining/RATE-60:raise TimeoutError('Shared full-replay cost watchdog reached')
                try:line=events.get(timeout=1)
                except queue.Empty:continue
                if line is None:break
                log.write(line);log.flush()
                match=re.search(r'\bap-[A-Za-z0-9]+\b',line)
                if match:
                    if app_id and app_id!=match.group():raise RuntimeError('Ambiguous app ID')
                    app_id=match.group();(run.dir/'app-id.txt').write_text(app_id)
                if 'FULL_REPLAY_DONE' in line:done=True
                if any(key in line for key in ['SHARD_DONE','PROJECTION_USD','FULL_REPLAY_DONE','https://modal.com/apps','Traceback','Error','preemption']):
                    print(line.rstrip(),flush=True)
        if p.wait()!=0 or not done:raise RuntimeError('Modal replay did not finish; checkpoint retained')
    except BaseException as exc:failure=exc
    finally:
        if app_id:
            info=subprocess.run(['modal','app','info',app_id,'--json'],capture_output=True,text=True,check=True)
            stopped=json.loads(info.stdout)['lifecycle']['state']=='stopped'
            if not stopped:subprocess.run(['modal','app','stop',app_id],check=True)
            info=subprocess.run(['modal','app','info',app_id,'--json'],capture_output=True,text=True,check=True)
            (run.dir/'app.json').write_text(info.stdout);stopped=json.loads(info.stdout)['lifecycle']['state']=='stopped'
            assert stopped
        if p is not None and p.poll() is None:p.terminate();p.wait(timeout=30)
        elapsed=time.monotonic()-start;billing=[]
        if app_id:
            report=subprocess.run(['modal','billing','report','--for','today','--resolution','h','--show-resources','--json'],capture_output=True,text=True,check=True)
            billing=[row for row in json.loads(report.stdout) if row.get('object_id')==app_id]
        write_json_atomic(run.dir/'billing.json',billing)
        summary=dict(app_id=app_id,app_stopped=stopped or app_id is None,client_wall_seconds=elapsed,
            conservative_compute_upper_usd=elapsed*RATE,billed_so_far_usd=sum(float(r['cost']) for r in billing),billing_may_lag=True,
            total_upper_usd=spent+elapsed*RATE+OVERHEAD,journal=str(journal),error=str(failure) if failure else None)
        write_json_atomic(run.dir/'summary.json',summary);run.result(**summary)
        run.finish('failed' if failure else 'finished',str(failure) if failure else None)
    print('CLIENT_RUN',run.dir);print(json.dumps(summary,indent=2))
    if failure:raise failure


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);main(p.parse_args().plan)
