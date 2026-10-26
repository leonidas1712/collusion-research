"""Continue verified replay into CPU checks and the approved cached addressee audit."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from collusion.runs import start_run, write_json_atomic


def command(run, name, arguments, marker):
    found = None
    with (run.dir/(name+'.log')).open('w') as log:
        process = subprocess.Popen(arguments, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1)
        for line in process.stdout:
            log.write(line); log.flush()
            if line.startswith(marker+' '):
                found = line.split(' ', 1)[1].strip()
            if line.startswith(('EXPOSURE ', 'FIT ', 'CONTROL_RUN ', 'PROBE_RUN ', 'PREPARED ', 'BILLED ', 'Traceback')):
                print(name, line.rstrip(), flush=True)
        code = process.wait()
    if code or found is None:
        raise RuntimeError(f'{name} failed or omitted completion marker; inspect {name}.log')
    return found


def main(args):
    data = Path(args.data).resolve()
    client = Path(args.client).resolve()
    run = start_run('e05-gpt-oss-post-replay-pipeline', experiment='E05', parents=[data.name, client.name],
        settings={'CPU_only': True, 'no_gpu_launch': True, 'addressee_cap_usd': 1,
                  'addressee_approval': 'channel-publication outcome with a public-emission cutoff', 'gate_before_outcome_fits': True})
    paths = dict(data=str(data), client=str(client))
    try:
        deadline = time.monotonic()+5*3600
        while True:
            status = json.loads((data/'meta.json').read_text())['status']
            if status == 'failed':
                raise RuntimeError('Dataset verification failed; no fits or paid addressee calls launched')
            if status == 'finished' and (client/'summary.json').exists():
                budget = json.loads((client/'summary.json').read_text())
                assert budget['app_stopped'] and budget['error'] is None and budget['total_upper_usd'] <= 20
                break
            if time.monotonic() >= deadline:
                raise TimeoutError('Replay/data completion did not arrive within five hours')
            time.sleep(10)
        python = str(ROOT/'experiments/E05-probes/.venv/bin/python')
        control = command(run, 'exposure', [python, 'experiments/E05-probes/gpt_oss_positive_control.py', data.name], 'CONTROL_RUN')
        paths['control'] = str(ROOT/'runs'/control)
        write_json_atomic(run.dir/'paths.json', paths)
        probe = command(run, 'probes', [python, 'experiments/E05-probes/gpt_oss_probes.py', '--data', str(data),
            '--control', paths['control'], '--workers', str(args.workers)], 'PROBE_RUN')
        paths['probes'] = probe
        write_json_atomic(run.dir/'paths.json', paths)
        addressee = command(run, 'addressee-prepare', [python, 'experiments/E06-monitors/addressee_audit.py',
            '--manifest', str(Path(args.manifest).resolve())], 'PREPARED')
        paths['addressee'] = addressee
        write_json_atomic(run.dir/'paths.json', paths)
        command(run, 'addressee', [str(ROOT/'.venv/bin/python'), 'experiments/E06-monitors/addressee_audit.py', '--run', addressee,
            '--reuse', 'runs/20261025-2202-e06-addressee-audit'], 'RESULT')
        run.result(**paths)
        run.finish()
        print('PIPELINE_RUN', run.dir)
    except BaseException as exc:
        write_json_atomic(run.dir/'paths.json', paths)
        run.finish('failed', str(exc))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True)
    parser.add_argument('--client', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--workers', type=int, default=4)
    main(parser.parse_args())
