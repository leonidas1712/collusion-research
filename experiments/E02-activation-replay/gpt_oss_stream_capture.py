"""Final streaming capture: four full layers and a fixed all-layer sketch."""
from pathlib import Path
import time
import numpy as np
from gpt_oss_replay import MODEL,REVISION,digest,score_positions

FULL_LAYERS=[6,12,18,23]
PROJECTION_SEED=20261026
PROJECTION_DIM=256

def capture(model,ids,prompt_length,positions,projection,full_layers):
    import torch
    from replay import decoder_layers
    _,layers=decoder_layers(model);full={};sketch={};last={};handles=[]
    def hook(i):
        def save(module,inputs,output):
            h=output[0] if isinstance(output,tuple) else output
            selected=h[0,positions]
            last[i]=h[0,prompt_length-1].detach().float().cpu().numpy().copy()
            if i in full_layers:full[i]=selected.detach().to(torch.float16).cpu().numpy().copy()
            sketch[i]=(selected.float()@projection[i]).detach().to(torch.float16).cpu().numpy().copy()
        return save
    try:
        for i,layer in enumerate(layers):handles.append(layer.register_forward_hook(hook(i)))
        tensor=torch.tensor([ids],device=model.get_input_embeddings().weight.device)
        with torch.inference_mode():out=model.base_model(input_ids=tensor,attention_mask=torch.ones_like(tensor),use_cache=False,return_dict=True)
        a=np.stack([full[i] for i in full_layers]);b=np.stack([sketch[i] for i in range(len(layers))]);c=np.stack([last[i] for i in range(len(layers))])
        assert np.isfinite(a).all() and np.isfinite(b).all() and np.isfinite(c).all(),'Activation overflow/nonfinite'
        return a,b,c,out.last_hidden_state
    finally:
        for handle in handles:handle.remove()


def execute(payload,output_root,model,projection,checkpoint=None):
    import collusion.runs as rh
    from fidelity import score_hidden
    rh.RUNS=Path(output_root);rh.INDEX=rh.RUNS/'index.jsonl'
    layers=payload.get('full_layers',FULL_LAYERS)
    run=rh.start_run('e02-gpt-oss-stream-shard',experiment='E02',model=MODEL,settings={'revision':REVISION,'requests':len(payload['rows']),'full_layers':layers,'storage_dtype':'float16','last_prompt_dtype':'float32','projection_seed':PROJECTION_SEED,'projection_dim':projection.shape[-1],'projection_sha256':payload['projection_sha256'],'tiny_random':model.config.hidden_size!=2880})
    start=time.monotonic();index=[]
    for i,row in enumerate(payload['rows']):
        if time.monotonic()-start>1200:raise TimeoutError('Capture shard wall guard')
        prompt=row['prompt_ids'];reply=row['reply_ids'];ids=prompt+reply;positions=row['capture_positions']
        assert digest(prompt)==row['prompt_sha256'] and digest(ids)==row['input_ids_sha256']
        full,sketch,last,hidden=capture(model,ids,len(prompt),positions,projection,layers)
        assert full.shape==(len(layers),len(positions),model.config.hidden_size)
        assert sketch.shape==(model.config.num_hidden_layers,len(positions),projection.shape[-1])
        fidelity=score_hidden(model,hidden,len(prompt),reply)
        segments={name:score_positions(model,hidden,ids,row[name+'_positions']) for name in ['reasoning','answer']}
        del hidden
        file=f'request-{i:04}.npz';sentinel=np.iinfo(np.int32).min
        np.savez_compressed(run.dir/file,residual_full=full,residual_projected=sketch,residual_last=last,
            input_ids=np.asarray(ids,dtype=np.int32),capture_positions=np.asarray(positions,dtype=np.int32),capture_roles=np.asarray(row['capture_roles'],dtype=np.int8),
            offset_to_first_secret=np.asarray([x if x is not None else sentinel for x in row['offset_to_first_secret']],dtype=np.int32),
            offset_to_first_public_secret=np.asarray([x if x is not None else sentinel for x in row['offset_to_first_public_secret']],dtype=np.int32),
            full_layers=np.asarray(layers),projection_layers=np.arange(model.config.num_hidden_layers))
        record={k:v for k,v in row.items() if k not in ['prompt_ids','reply_ids']}
        record.update(file=file,full_shape=list(full.shape),projection_shape=list(sketch.shape),fidelity=fidelity,segments=segments,artifact_bytes=(run.dir/file).stat().st_size)
        index.append(record);rh.write_json_atomic(run.dir/'index.json',index)
        if checkpoint and (i+1)%10==0:checkpoint()
        print('STREAM_PROGRESS',i+1,len(payload['rows']),flush=True)
    summary={'requests':len(index),'wall_seconds':time.monotonic()-start,'capture_positions':sum(len(r['capture_positions']) for r in index),'artifact_bytes':sum(r['artifact_bytes'] for r in index),'full_layers':layers,'projection_dim':projection.shape[-1]}
    for name in ['all','reasoning','answer']:
        values=[r['fidelity'] if name=='all' else r['segments'][name] for r in index];nk='n_reply_tokens' if name=='all' else 'n_tokens';n=sum(v[nk] for v in values)
        summary[name]={'n_tokens':n,**{m:sum(v[m]*v[nk] for v in values if v[nk])/n if n else None for m in ['mean_token_nll','top5_fraction']}}
    rh.write_json_atomic(run.dir/'summary.json',summary);run.result(**summary);run.finish()
    if checkpoint:checkpoint()
    return run.dir
