"""E15: score a payload on Modal in resumable batches.

Splits the payload into batches of at most --size forwards (the E14 reproduction calls go in the
first batch), runs each batch as one Modal job, and downloads its scores.csv to OUT_DIR/batch-NNN.csv.
Batches whose CSV already exists are skipped, so a crash or timeout loses at most one batch.

    python experiments/E15-giving-in-scaleup/gpu_batches.py PAYLOAD_JSON OUT_DIR [--size 400]
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODAL = ROOT / '.venv/bin/modal'


def main(a):
    payload = json.loads(Path(a.payload).read_text())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    batches = [payload[i:i + a.size] for i in range(0, len(payload), a.size)]
    log_path = out / 'batches.json'
    log = json.loads(log_path.read_text()) if log_path.exists() else {'size': a.size, 'batches': {}}
    for n, batch in enumerate(batches):
        target = out / f'batch-{n:03}.csv'
        if target.exists():
            continue
        path = out / f'batch-{n:03}.payload.json'
        path.write_text(json.dumps(batch, ensure_ascii=False))
        for attempt in range(a.attempts):
            started = time.time()
            proc = subprocess.run([str(MODAL), 'run', str(HERE / 'modal_app.py'), '--mode', 'full', '--payload-path', str(path)],
                                  cwd=ROOT, capture_output=True, text=True)
            wall = time.time() - started
            found = re.search(r'"path": "(runs/[^"]+)"', proc.stdout)
            entry = {'forwards': len(batch), 'attempt': attempt + 1, 'local_wall_seconds': wall, 'returncode': proc.returncode,
                     'remote_run': found.group(1) if found else None}
            log['batches'].setdefault(str(n), []).append(entry)
            log_path.write_text(json.dumps(log, indent=1))
            if proc.returncode == 0 and found:
                subprocess.run([str(MODAL), 'volume', 'get', 'collusion-activations', f'{found.group(1)}/scores.csv',
                                str(target), '--force'], cwd=ROOT, check=True, capture_output=True)
                print('BATCH', n, len(batch), f'{wall:.0f}s', found.group(1), flush=True)
                break
            print('BATCH_FAILED', n, attempt + 1, proc.stderr[-500:], flush=True)
            time.sleep(60 * (attempt + 1))
        else:
            raise SystemExit(f'batch {n} failed after {a.attempts} attempts')
        path.unlink()
    print('GPU_DONE', len(batches), 'batches', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('payload')
    p.add_argument('out')
    p.add_argument('--size', type=int, default=400)
    p.add_argument('--attempts', type=int, default=3)
    main(p.parse_args())
