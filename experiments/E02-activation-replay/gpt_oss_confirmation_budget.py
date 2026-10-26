"""Confirmation replay ledger within the shared USD10 API/GPU cap and process watchdog; always stops its Modal app."""
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
CAP=4.
OVERHEAD=.50


def full_run_projection(plan, client_path, old_plan_path):
    """Scale the completed same-model full replay, including its retries/load time."""
    client=json.loads(Path(client_path).read_text());old=json.loads(Path(old_plan_path).read_text())
    assert client['app_stopped'] and not client['error']
    assert (old['model'],old['revision'])==(plan['model'],plan['revision'])
    old_tokens=old['counts']['prompt_tokens']+old['counts']['reply_tokens']
    new_tokens=plan['counts']['prompt_tokens']+plan['counts']['reply_tokens']
    projected_seconds=new_tokens/old_tokens*client['client_wall_seconds']
    return dict(benchmark_client=str(client_path),benchmark_plan=str(old_plan_path),
                old_tokens=old_tokens,new_tokens=new_tokens,old_wall_seconds=client['client_wall_seconds'],
                projected_seconds=projected_seconds,margin=1.25,
                upper_usd=projected_seconds*RATE*1.25+OVERHEAD,
                note='Outcome-blind completed full-run estimate; cap and measured longest-first shard guard unchanged')


def main(plan_path, benchmark_client=None, benchmark_plan=None):
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
    projection=full_run_projection(plan,benchmark_client,benchmark_plan) if benchmark_client else None
    estimate=projection['upper_usd'] if projection else plan['counts']['prior_projection_usd_with_2x_margin']
    assert estimate<=remaining+OVERHEAD,'Prior projection exceeds phase/shared remainder'
    run=start_run('e02-gpt-oss-confirm-client',experiment='E02',parents=[plan_path.parent.name],
        settings={'approval':'frozen confirmation: sharedUSD10 total, API cost deducted before GPU','cap_usd':CAP,'prior_upper_usd':spent,
                  'overhead_reserve_usd':OVERHEAD,'remaining_usd':remaining,'rate_per_second':RATE,'plan':str(plan_path)})
    if projection:write_json_atomic(run.dir/'projection.json',projection)
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
            if not stopped:subprocess.run(['modal','app','stop',app_id,'--yes'],check=True)
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
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--api-ledger',required=True);p.add_argument('--cap',type=float,default=4)
    p.add_argument('--benchmark-client');p.add_argument('--benchmark-plan');a=p.parse_args()
    assert bool(a.benchmark_client)==bool(a.benchmark_plan)
    api=sum(float(r['charged_or_reserved_usd']) for r in json.loads(Path(a.api_ledger).read_text()))
    assert 0<a.cap<=10-api-1, 'API plus GPU cap plus reserve must remain belowUSD10'
    CAP=a.cap
    main(a.plan,a.benchmark_client,a.benchmark_plan)
