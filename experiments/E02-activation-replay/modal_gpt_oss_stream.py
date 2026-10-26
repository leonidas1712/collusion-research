"""Final streaming capture under the shared USD15 watchdog."""
from pathlib import Path
import hashlib
import json
import sys
import os
import time
import modal

HERE=Path(__file__).resolve().parent if modal.is_local() else Path('/app/experiments/E02-activation-replay')
ROOT=HERE.parents[1];sys.path[:0]=[str(HERE),str(ROOT/'src')]
app=modal.App('collusion-e02-gpt-oss-stream')
weights=modal.Volume.from_name('collusion-weights');outputs=modal.Volume.from_name('collusion-activations')
image=(modal.Image.debian_slim(python_version='3.11')
 .pip_install('torch==2.14.1','transformers==5.20.2','accelerate==1.15.0','safetensors==0.8.0',
              'numpy==2.4.6','huggingface-hub==2.3.0','openai-harmony==0.0.8')
 .env({'HF_HOME':'/weights/huggingface','PYTHONPATH':'/app/src','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}))
if modal.is_local():
    image=image.add_local_dir(ROOT/'src'/'collusion',remote_path='/app/src/collusion',ignore=['__pycache__/**'])
    for name in ['gpt_oss_replay.py','gpt_oss_stream_capture.py','replay.py','fidelity.py']:
        image=image.add_local_file(HERE/name,f'/app/experiments/E02-activation-replay/{name}')

    image=image.add_local_file(Path(os.environ['COLLUSION_STREAM_PROJECTION']),'/app/projection.npz')

@app.cls(image=image,gpu='A100-80GB',timeout=1500,cpu=(4,4),memory=(32768,65536),
         volumes={'/weights':weights,'/outputs':outputs},max_containers=1,scaledown_window=15)
class Replay:
    @modal.enter()
    def load(self):
        import torch
        from transformers import AutoModelForCausalLM,Mxfp4Config
        from gpt_oss_replay import MODEL,REVISION
        marker=Path('/weights/ready')/MODEL.replace('/','--')/(REVISION+'.json')
        assert marker.is_file(),'Cached weights required; no GPU downloads'
        self.model=AutoModelForCausalLM.from_pretrained(MODEL,revision=REVISION,local_files_only=True,
            quantization_config=Mxfp4Config(dequantize=True),dtype=torch.bfloat16,device_map={'':'cuda:0'},attn_implementation='eager').eval()
        import numpy as np
        self.projection=torch.tensor(np.load('/app/projection.npz')['projection'],device='cuda:0',dtype=torch.float32)
        assert self.projection.shape==(24,2880,256)
        self.projection_sha=hashlib.sha256(Path('/app/projection.npz').read_bytes()).hexdigest()
        assert all(p.device.type=='cuda' for p in self.model.parameters())
        assert all(p.dtype==torch.bfloat16 or (p.dtype==torch.float32 and ('layernorm' in name or '.norm.' in name))
                   for name,p in self.model.named_parameters() if p.is_floating_point())

    @modal.method()
    def shard(self,payload):
        from gpt_oss_replay import MODEL,REVISION
        from gpt_oss_stream_capture import execute
        assert payload['model']==MODEL and payload['revision']==REVISION and 0<len(payload['rows'])<=100
        assert payload['projection_sha256']==self.projection_sha
        try:
            path=execute(payload,'/outputs/runs',model=self.model,projection=self.projection,checkpoint=outputs.commit)
            return dict(remote=str(path.relative_to('/outputs')),summary=json.loads((path/'summary.json').read_text()))
        finally:outputs.commit()


@app.local_entrypoint()
def main(plan:str,journal:str,remaining_usd:float):
    from collusion.runs import write_json_atomic
    path=Path(plan);raw=path.read_bytes();frozen=json.loads(raw);plan_sha=hashlib.sha256(raw).hexdigest()
    assert 0<remaining_usd<=14.0
    from stream_plan_approval import approved_stream_plan
    assert approved_stream_plan(raw), 'Approved capture plan required'
    assert hashlib.sha256(Path(frozen['source_manifest']).read_bytes()).hexdigest()==frozen['source_manifest_sha256']
    for source,sha in frozen['sources'].items():assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==sha
    destination=Path(journal)
    state=json.loads(destination.read_text()) if destination.exists() else dict(plan_sha256=plan_sha,completed={})
    assert state['plan_sha256']==plan_sha
    pending=[s for s in frozen['shards'] if s['path'] not in state['completed']]
    assert pending,'All shards already complete'
    start=time.monotonic();worker=Replay();slowest=0.
    for part in pending:
        raw=(path.parent/part['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==part['sha256']
        result=worker.shard.remote(json.loads(raw))
        assert result['summary']['requests']==part['requests']
        state['completed'][part['path']]={**result,'sha256':part['sha256'],'total_tokens':part['total_tokens']}
        write_json_atomic(destination,state)
        print('SHARD_DONE',json.dumps(dict(shard=part['path'],remote=result['remote'],summary={k:result['summary'][k] for k in ['requests','wall_seconds','all','reasoning','answer']})),flush=True)
        assert result['summary']['all']['mean_token_nll']<2 and result['summary']['all']['top5_fraction']>.90, 'Replay fidelity guard failed'
        slowest=max(slowest,result['summary']['wall_seconds']/part['total_tokens'])
        left=sum(s['total_tokens'] for s in pending if s['path'] not in state['completed'])
        projected=(time.monotonic()-start+left*slowest*1.25)*.00090
        print('PROJECTION_USD',projected,'REMAINING_LIMIT',remaining_usd,flush=True)
        if projected>remaining_usd:raise RuntimeError('Measured remaining replay projection exceeds approved remainder; completed shard preserved')
    print('FULL_REPLAY_DONE',str(destination),flush=True)
