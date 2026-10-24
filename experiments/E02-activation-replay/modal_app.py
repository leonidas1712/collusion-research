"""Modal wrapper. Import defines resources; only modal run submits paid work."""
from pathlib import Path
import sys
import re
import modal

HERE = Path(__file__).resolve().parent if modal.is_local() else Path('/app/experiments/E02-activation-replay')
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

app = modal.App('collusion-e02-replay')
weights = modal.Volume.from_name('collusion-weights', create_if_missing=True)
outputs = modal.Volume.from_name('collusion-activations', create_if_missing=True)
image = (modal.Image.debian_slim(python_version='3.11')
         .pip_install('torch==2.14.1', 'transformers==5.20.2', 'accelerate==1.15.0',
                      'safetensors==0.8.0', 'numpy==2.4.6', 'huggingface-hub==2.3.0')
         .env({'HF_HOME': '/weights/huggingface', 'PYTHONPATH': '/app/src'}))
if modal.is_local():
    image = image.add_local_dir(ROOT / 'src' / 'collusion', remote_path='/app/src/collusion', ignore=['__pycache__/**'])
    for filename in ('replay.py', 'fidelity.py', 'modal_inputs.py', 'replay_manifest.py'):
        image = image.add_local_file(HERE / filename, f'/app/experiments/E02-activation-replay/{filename}')


def execute_replay(payload: dict, options: list[str], source_manifest: dict):
    import os
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    model_id = options[options.index('--model')+1]
    revision = options[options.index('--revision')+1]
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('GPU replay requires a pinned 40-character HF revision')
    marker = Path('/weights/ready') / model_id.replace('/', '--') / f'{revision}.json'
    if not marker.is_file():
        raise FileNotFoundError('Weights are not prefetched. Run the separately approved CPU prefetch first.')
    import json
    import tempfile
    import torch
    sys.path.insert(0, '/app/experiments/E02-activation-replay')
    from replay import main, parser
    if '--precision' in options and options[options.index('--precision')+1] == 'fp8':
        if torch.cuda.get_device_capability()[0] < 9:
            raise RuntimeError('Official Qwen FP8 requires Hopper or newer; A100 fallback cannot run this precision')
    with tempfile.TemporaryDirectory() as temp:
        run_dirs = []
        for run_id, files in payload.items():
            if Path(run_id).name != run_id or run_id in ('.', '..'):
                raise ValueError('Invalid run ID')
            directory = Path(temp) / run_id / 'episodes'
            directory.mkdir(parents=True)
            for name, raw in files.items():
                if Path(name).name != name:
                    raise ValueError('Invalid episode filename')
                (directory / name).write_text(raw)
            run_dirs.append(str(directory.parent))
        if source_manifest.get('request_selection'):
            selection_path = Path(temp) / 'selection.jsonl'
            selection_path.write_text(''.join(json.dumps(row)+'\n' for row in source_manifest['request_selection']))
            options = [*options, '--manifest', str(selection_path)]
        args = parser().parse_args([*run_dirs, *options, '--output-root', '/outputs/runs', '--local-files-only'])
        try:
            output = main(args, checkpoint=outputs.commit)
            (output / 'input_manifest.json').write_text(json.dumps(source_manifest, indent=2))
            return str(output.relative_to(Path('/outputs').resolve()))
        finally:
            outputs.commit()


replay_remote = app.function(image=image, gpu=['H100!', 'A100-80GB'], timeout=4*60*60,
    volumes={'/weights': weights, '/outputs': outputs}, max_containers=1, cpu=4, memory=32768, scaledown_window=2)(execute_replay)


@app.function(image=image, gpu='A100-80GB', timeout=20*60,
              volumes={'/weights': weights, '/outputs': outputs}, max_containers=1, cpu=(4,4), memory=(32768,65536), scaledown_window=2)
def benchmark_a100(payload: dict, options: list[str], source_manifest: dict):
    return execute_replay(payload, options, source_manifest)


@app.function(image=image, gpu='A100-80GB', timeout=160*60,
              volumes={'/weights': weights, '/outputs': outputs}, max_containers=1,
              cpu=(4,4), memory=(32768,65536), scaledown_window=2)
def replay_a100(payload: dict, options: list[str], source_manifest: dict):
    return execute_replay(payload, options, source_manifest)


@app.function(image=image, gpu='H100!', timeout=4*60*60,
              volumes={'/weights': weights, '/outputs': outputs}, max_containers=1, cpu=4, memory=32768, scaledown_window=2)
def replay_h100(payload: dict, options: list[str], source_manifest: dict):
    return execute_replay(payload, options, source_manifest)


prefetch_image = (modal.Image.debian_slim(python_version='3.11')
    .pip_install('huggingface-hub==2.3.0')
    .env({'HF_HOME': '/weights/huggingface', 'PYTHONPATH': '/app/src'}))
if modal.is_local():
    prefetch_image = prefetch_image.add_local_dir(ROOT / 'src' / 'collusion', remote_path='/app/src/collusion', ignore=['__pycache__/**'])


@app.function(image=prefetch_image, timeout=20*60, cpu=(4,4), memory=(16384,16384),
              volumes={'/weights': weights}, max_containers=1, scaledown_window=2)
def prefetch_weights(model: str, revision: str):
    import json
    from huggingface_hub import snapshot_download
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Prefetch requires an immutable 40-character HF revision')
    import collusion.runs as run_helpers
    run_helpers.RUNS = Path('/weights/prefetch-runs')
    run_helpers.INDEX = run_helpers.RUNS / 'index.jsonl'
    run = run_helpers.start_run('e02-prefetch', experiment='E02', settings={'model': model, 'revision': revision}, model=model)
    try:
        snapshot = snapshot_download(model, revision=revision,
            allow_patterns=['*.json', '*.safetensors', '*.jinja', '*.model', '*.txt', '*.tiktoken'])
        marker = Path('/weights/ready') / model.replace('/', '--') / f'{revision}.json'
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({'model': model, 'revision': revision, 'snapshot': snapshot}))
        run.result(snapshot=snapshot)
        run.finish()
        return str(marker)
    except BaseException as error:
        run.finish('failed', f'{type(error).__name__}: {error}')
        raise
    finally:
        weights.commit()


@app.local_entrypoint()
def prefetch(model: str, revision: str):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Prefetch requires a pinned 40-character revision')
    print(prefetch_weights.remote(model, revision))


@app.local_entrypoint()
def main(run_ids: str = '', model: str = 'Qwen/Qwen3-32B', revision: str = '9216db5781bf21249d130ec9da846c4624c16137',
         layers: str = 'all', max_requests: int = 50, precision: str = 'bf16',
         source_model: str = 'qwen/qwen3-32b', max_tokens: int = 32768,
         gpu: str = 'a100-benchmark', request_order: str = 'longest',
         manifest_path: str = '', activations_only: bool = False, fidelity_tokens: int = 64):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Use a pinned 40-character revision')
    if max_requests < 1 or max_tokens < 1:
        raise ValueError('Request and token limits must be positive')
    if precision not in ('bf16', 'fp8'):
        raise ValueError('precision must be bf16 or fp8')
    if precision == 'fp8' and model != 'Qwen/Qwen3-32B-FP8':
        raise ValueError('Use --model Qwen/Qwen3-32B-FP8 with --precision fp8')
    if gpu not in ('a100-benchmark', 'a100', 'h100', 'fallback'):
        raise ValueError('gpu must be a100-benchmark, a100, h100 or fallback')
    if precision == 'fp8' and gpu != 'h100':
        raise ValueError('FP8 requires --gpu h100; A100 does not support this kernel')
    from modal_inputs import pack_runs, manifest
    request_selection = []
    if manifest_path:
        if run_ids:
            raise ValueError('Use manifest-path or run-ids, not both')
        from replay_manifest import load_manifest
        request_selection = load_manifest(manifest_path)
        run_ids = ','.join(dict.fromkeys(row['run_id'] for row in request_selection))
    if not run_ids:
        raise ValueError('Supply manifest-path or run-ids')
    payload = pack_runs(ROOT, [value.strip() for value in run_ids.split(',')])
    if request_selection:
        import hashlib
        selected_files = {(row['run_id'], Path(row['episode_file']).name) for row in request_selection}
        payload = {run_id: {name: raw for name, raw in files.items() if (run_id, name) in selected_files}
                   for run_id, files in payload.items()}
        for row in request_selection:
            raw = payload[row['run_id']][Path(row['episode_file']).name]
            if hashlib.sha256(raw.encode()).hexdigest() != row['episode_sha256']:
                raise ValueError('Source changed since manifest planning; no remote call submitted')
    options = ['--model', model, '--revision', revision, '--layers', layers,
               '--max-requests', str(max_requests), '--precision', precision,
               '--source-model', source_model, '--max-tokens', str(max_tokens), '--request-order', request_order]
    if request_selection:
        for flag in ('--max-requests', '--request-order'):
            i = options.index(flag)
            del options[i:i+2]
    options += ['--fidelity-tokens', str(fidelity_tokens)]
    if gpu == 'a100':
        options += ['--max-wall-seconds', str(150*60)]
    if activations_only:
        options.append('--activations-only')
    function = {'a100': replay_a100, 'a100-benchmark': benchmark_a100, 'h100': replay_h100, 'fallback': replay_remote}[gpu]
    import hashlib
    import subprocess
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    provenance = {'episodes': manifest(payload), 'local_git_commit': commit,
        'request_selection': request_selection,
        'code_sha256': {name: hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                       for name in ('replay.py', 'fidelity.py', 'modal_app.py', 'modal_inputs.py', 'replay_manifest.py')}}
    output = function.remote(payload, options, provenance)
    print('mkdir -p ./modal-results')
    print(f'modal volume get collusion-activations {output} ./modal-results')
