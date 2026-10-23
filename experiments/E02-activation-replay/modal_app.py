"""Modal wrapper. Import defines resources; only modal run submits paid work."""
from pathlib import Path
import sys
import modal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from modal_inputs import pack_runs, manifest

app = modal.App('collusion-e02-replay')
weights = modal.Volume.from_name('collusion-weights', create_if_missing=True)
outputs = modal.Volume.from_name('collusion-activations', create_if_missing=True)
image = (modal.Image.debian_slim(python_version='3.11')
         .pip_install('torch==2.14.1', 'transformers==5.20.2', 'accelerate==1.15.0',
                      'safetensors==0.8.0', 'numpy==2.4.6', 'huggingface-hub==2.3.0')
         .env({'HF_HOME': '/weights/huggingface', 'PYTHONPATH': '/app/src'})
         .add_local_dir(ROOT / 'src' / 'collusion', remote_path='/app/src/collusion', ignore=['__pycache__/**']))
for filename in ('replay.py', 'fidelity.py', 'modal_inputs.py'):
    image = image.add_local_file(HERE / filename, f'/app/experiments/E02-activation-replay/{filename}')


def execute_replay(payload: dict, options: list[str], source_manifest: dict):
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
        args = parser().parse_args([*run_dirs, *options, '--output-root', '/outputs/runs', '--reply-fidelity'])
        try:
            output = main(args)
            (output / 'input_manifest.json').write_text(json.dumps(source_manifest, indent=2))
            return str(output.relative_to('/outputs'))
        finally:
            weights.commit()
            outputs.commit()


replay_remote = app.function(image=image, gpu=['H100!', 'A100-80GB'], timeout=4*60*60,
    volumes={'/weights': weights, '/outputs': outputs}, max_containers=1)(execute_replay)


@app.function(image=image, gpu='A100-80GB', timeout=30*60,
              volumes={'/weights': weights, '/outputs': outputs}, max_containers=1)
def benchmark_a100(payload: dict, options: list[str], source_manifest: dict):
    return execute_replay(payload, options, source_manifest)


@app.function(image=image, gpu='H100!', timeout=4*60*60,
              volumes={'/weights': weights, '/outputs': outputs}, max_containers=1)
def replay_h100(payload: dict, options: list[str], source_manifest: dict):
    return execute_replay(payload, options, source_manifest)


@app.local_entrypoint()
def main(run_ids: str, model: str = 'Qwen/Qwen3-32B', revision: str = 'main',
         layers: str = 'all', max_requests: int = 50, precision: str = 'bf16',
         source_model: str = 'qwen/qwen3-32b', max_tokens: int = 32768,
         gpu: str = 'a100-benchmark', request_order: str = 'longest'):
    if max_requests < 1 or max_tokens < 1:
        raise ValueError('Request and token limits must be positive')
    if precision not in ('bf16', 'fp8'):
        raise ValueError('precision must be bf16 or fp8')
    if precision == 'fp8' and model != 'Qwen/Qwen3-32B-FP8':
        raise ValueError('Use --model Qwen/Qwen3-32B-FP8 with --precision fp8')
    if gpu not in ('a100-benchmark', 'h100', 'fallback'):
        raise ValueError('gpu must be a100-benchmark, h100 or fallback')
    if precision == 'fp8' and gpu != 'h100':
        raise ValueError('FP8 requires --gpu h100; A100 does not support this kernel')
    payload = pack_runs(ROOT, [value.strip() for value in run_ids.split(',')])
    options = ['--model', model, '--revision', revision, '--layers', layers,
               '--max-requests', str(max_requests), '--precision', precision,
               '--source-model', source_model, '--max-tokens', str(max_tokens), '--request-order', request_order]
    function = {'a100-benchmark': benchmark_a100, 'h100': replay_h100, 'fallback': replay_remote}[gpu]
    output = function.remote(payload, options, manifest(payload))
    print(f'modal volume get collusion-activations {output} ./modal-results/{Path(output).name}')
