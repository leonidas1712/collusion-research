"""Continue approved replay2 locally after the running GPU client has stopped."""
import json
import subprocess
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run
E02=ROOT/'experiments/E02-activation-replay';E05=ROOT/'experiments/E05-probes'
PY02=str(E02/'.venv/bin/python');PY05=str(E05/'.venv/bin/python')
CLIENT='20261025-0126-e02-replay2-modal-client';REMOTE='20261024-1727-e02-activation-replay';BENCH='20261024-1721-e02-activation-replay'


def main():
    resumed_from=sys.argv[1] if len(sys.argv)>1 else None
    run=start_run('e05-replay2-pipeline',experiment='E05',parents=[CLIENT]+([resumed_from] if resumed_from else []),settings={'no_gpu_launches':True,'stop_on_any_stage_failure':True,'approval':'Aboard #609 and #611; CPU continuation authorized','resumed_from':resumed_from,'resume_reason':'increase read-only download concurrency; reuse atomic completed files' if resumed_from else None})
    stages={}
    def step(name,command,marker=None):
        print('START',name,flush=True);p=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);found=None
        with (run.dir/f'{name}.log').open('w') as log:
            for line in p.stdout:
                log.write(line);log.flush();print(line.rstrip(),flush=True)
                if marker and line.startswith(marker+' '):found=line.strip().split()[-1]
        assert p.wait()==0,f'{name} failed; see {run.dir/name}.log'
        if marker:assert found,f'{name} did not report a run id'
        stages[name]=found or 'passed';(run.dir/'stages.json').write_text(json.dumps(stages,indent=2));return found
    try:
        summary=ROOT/'runs'/CLIENT/'summary.json'
        while not summary.exists():time.sleep(5)
        status=json.loads(summary.read_text());assert status['app_stopped'] and status['error'] is None
        assert json.loads((summary.parent/'meta.json').read_text())['status']=='finished'
        step('download',['/Users/leo/.local/share/uv/tools/modal/bin/python',str(E02/'download_volume.py'),'runs/'+REMOTE])
        step('verify',[PY02,str(E02/'verify_main.py'),'runs/'+REMOTE,'--manifest','runs/20261025-0119-e02-replay2-plan/remaining.jsonl'])
        data=step('data',[PY05,str(E05/'replay2_data.py'),BENCH,REMOTE],'DATA_RUN')
        control=step('positive-control',[PY05,str(E05/'replay2_positive_control.py'),data],'CONTROL_RUN')
        branch=step('branching',[PY05,str(E05/'replay2_branching.py'),data],'BRANCH_RUN')
        fits=step('fits',[PY05,str(E05/'replay2_core.py'),data,control],'REPLAY2_FITS')
        report=step('report',[PY05,str(E05/'replay2_report.py'),data,fits,control,branch],'ANALYSIS_RUN')
        run.result(**stages);run.finish();print('PIPELINE_COMPLETE',report,flush=True)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':main()
