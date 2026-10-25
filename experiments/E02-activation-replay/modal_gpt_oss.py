"""Isolated, capped A100 Harmony replay. The Qwen Modal app is unchanged."""
from pathlib import Path
import json
import sys
import modal

HERE=Path(__file__).resolve().parent if modal.is_local() else Path('/app/experiments/E02-activation-replay')
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
app=modal.App('collusion-e02-gpt-oss-fidelity')
weights=modal.Volume.from_name('collusion-weights')
outputs=modal.Volume.from_name('collusion-activations')
image=(modal.Image.debian_slim(python_version='3.11')
       .pip_install('torch==2.14.1','transformers==5.20.2','accelerate==1.15.0',
                    'safetensors==0.8.0','numpy==2.4.6','huggingface-hub==2.3.0','openai-harmony==0.0.8')
       .env({'HF_HOME':'/weights/huggingface','PYTHONPATH':'/app/src','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}))
if modal.is_local():
    image=image.add_local_dir(ROOT/'src'/'collusion',remote_path='/app/src/collusion',ignore=['__pycache__/**'])
    for name in ['gpt_oss_replay.py','replay.py','fidelity.py']:
        image=image.add_local_file(HERE/name,f'/app/experiments/E02-activation-replay/{name}')


@app.function(image=image,gpu='A100-80GB',timeout=1500,cpu=(4,4),memory=(32768,65536),
              volumes={'/weights':weights,'/outputs':outputs},max_containers=1,scaledown_window=2)
def replay(payload):
    from gpt_oss_replay import execute,MODEL,REVISION
    marker=Path('/weights/ready')/MODEL.replace('/','--')/(REVISION+'.json')
    assert marker.is_file(),'CPU prefetch must finish first'
    assert payload['model']==MODEL and payload['revision']==REVISION
    assert 0<len(payload['rows'])<=100
    try:
        result=execute(payload,'/outputs/runs',checkpoint=outputs.commit)
        return str(result.relative_to('/outputs'))
    finally:outputs.commit()


@app.local_entrypoint()
def main(plan:str):
    import hashlib
    payload=json.loads(Path(plan).read_text())
    sources={}
    for row in payload['rows']:
        path=row['source_path']
        if path not in sources:sources[path]=Path(path).read_bytes()
        assert hashlib.sha256(sources[path]).hexdigest()==row['episode_sha256'],'Source episode changed'
    remote=replay.remote(payload)
    print(f'modal volume get collusion-activations {remote} ./modal-results')
