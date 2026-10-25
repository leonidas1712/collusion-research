"""Independent Harmony adapter and teacher-forced gpt-oss replay; no generation."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))
MODEL='openai/gpt-oss-20b'
REVISION='6cee5e81ee83917806bbde320786a8fb61efebee'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def assistant_messages(raw, h, include_reasoning=True):
    messages=[]
    if include_reasoning and raw.get('reasoning'):
        messages.append(h.Message.from_role_and_content(h.Role.ASSISTANT,raw['reasoning']).with_channel('analysis'))
    if raw.get('content'):
        messages.append(h.Message.from_role_and_content(h.Role.ASSISTANT,raw['content']).with_channel('final'))
    for call in raw.get('tool_calls') or []:
        fn=call['function']
        messages.append(h.Message.from_role_and_content(h.Role.ASSISTANT,fn['arguments'])
                        .with_recipient('functions.'+fn['name']).with_channel('commentary').with_content_type('json'))
    return messages


def render(record, date, keep_reasoning=False):
    import openai_harmony as h
    enc=h.load_harmony_encoding(h.HarmonyEncodingName.HARMONY_GPT_OSS)
    req=record['request']; effort=(req.get('reasoning') or req.get('extra_body',{}).get('reasoning') or {}).get('effort','low')
    system=h.SystemContent.new().with_reasoning_effort(h.ReasoningEffort[effort.upper()]).with_conversation_start_date(date)
    developer=h.DeveloperContent.new().with_instructions(req['messages'][0]['content'])
    developer.with_function_tools([h.ToolDescription.new(t['function']['name'],t['function'].get('description',''),t['function'].get('parameters')) for t in req.get('tools',[])])
    messages=[h.Message.from_role_and_content(h.Role.SYSTEM,system),h.Message.from_role_and_content(h.Role.DEVELOPER,developer)]
    names={}
    for raw in req['messages'][1:]:
        if raw['role']=='user':messages.append(h.Message.from_role_and_content(h.Role.USER,raw['content']))
        elif raw['role']=='assistant':
            messages.extend(assistant_messages(raw,h,keep_reasoning))
            for call in raw.get('tool_calls') or []:names[call['id']]='functions.'+call['function']['name']
        elif raw['role']=='tool':
            messages.append(h.Message.from_author_and_content(h.Author.new(h.Role.TOOL,names[raw['tool_call_id']]),raw['content']).with_recipient('assistant').with_channel('commentary'))
        else:raise ValueError('Unsupported saved role: '+raw['role'])
    config=h.RenderConversationConfig(auto_drop_analysis=False)
    prompt=enc.render_conversation_for_completion(h.Conversation.from_messages(messages),h.Role.ASSISTANT,config)
    choices=(record.get('response') or {}).get('choices') or []
    raw=(choices[0].get('message') or {}) if choices else {}
    reply_messages=assistant_messages(raw,h)
    if not reply_messages:
        return dict(prompt_ids=prompt,reply_ids=[],reasoning_positions=[],answer_positions=[],effort=effort,reply_status='missing_or_empty')
    full=enc.render_conversation_for_training(h.Conversation.from_messages(messages+reply_messages),config)
    assert full[:len(prompt)]==prompt, 'Harmony prompt/reply prefix mismatch'
    reply=full[len(prompt):]
    # Locate body spans by the renderer's message delimiter, not text search.
    spans={'reasoning':[],'answer':[]};offset=len(full)-sum(len(enc.render(m,h.RenderOptions(conversation_has_function_tools=True))) for m in reply_messages)
    for m in reply_messages:
        ids=enc.render(m,h.RenderOptions(conversation_has_function_tools=True))
        delimiter=enc.encode('<|message|>',allowed_special='all')[0]
        begin=ids.index(delimiter)+1
        key='reasoning' if m.channel=='analysis' else 'answer'
        spans[key].extend(range(offset+begin,offset+len(ids)-1));offset+=len(ids)
    assert offset==len(full)
    assert all(len(prompt)<=p<len(full) for ps in spans.values() for p in ps)
    return dict(prompt_ids=prompt,reply_ids=reply,reasoning_positions=spans['reasoning'],answer_positions=spans['answer'],effort=effort)


def plan(paths, output):
    from collusion.runs import start_run,write_json_atomic
    run=start_run('e02-gpt-oss-plan',experiment='E02',parents=sorted({Path(p).parent.parent.name for p in paths}),settings={'episodes':paths,'model':MODEL,'revision':REVISION})
    rows=[]
    for path in map(Path,paths):
        raw=path.read_bytes();ep=json.loads(raw);assert ep['status']=='complete' and not ep.get('fake')
        for idx,record in enumerate(ep['requests']):
            if record['actor']!='target' or not record.get('response'):continue
            assert record['request']['model']==MODEL
            date=time.strftime('%Y-%m-%d',time.gmtime(record['response']['created']))
            dropped=render(record,date);kept=render(record,date,True)
            provider_tokens=record['response']['usage'].get('prompt_tokens')
            rows.append(dict(run_id=path.parent.parent.name,episode_file=path.name,request_idx=idx,round=record['round'],
                source_path=str(path.resolve()),episode_sha256=hashlib.sha256(raw).hexdigest(),request_sha256=digest(record['request']),
                served_provider=record['response'].get('provider'),label=ep.get('label'),provider_prompt_tokens=provider_tokens,
                drop_prompt_tokens=len(dropped['prompt_ids']),keep_prompt_tokens=len(kept['prompt_ids']),
                prompt_sha256=digest(dropped['prompt_ids']),**dropped))
    result={'model':MODEL,'revision':REVISION,'history_reasoning':'drop_all','rows':rows}
    write_json_atomic(run.dir/'plan.json',result)
    stats={'requests':len(rows),'episodes':len(paths),'prompt_tokens':sum(len(r['prompt_ids']) for r in rows),
           'reply_tokens':sum(len(r['reply_ids']) for r in rows),'reasoning_tokens':sum(len(r['reasoning_positions']) for r in rows),
           'drop_deltas':[r['drop_prompt_tokens']-r['provider_prompt_tokens'] for r in rows],
           'keep_deltas':[r['keep_prompt_tokens']-r['provider_prompt_tokens'] for r in rows]}
    write_json_atomic(run.dir/'counts.json',stats);run.result(**stats);run.finish()
    if output:Path(output).write_text(json.dumps(result))
    print('PLAN',run.dir/'plan.json');print(json.dumps(stats))


def capture(model, ids, prompt_length, reasoning_positions, device):
    import numpy as np
    import torch
    from replay import decoder_layers
    _,layers=decoder_layers(model)
    last={};reasoning={};handles=[]
    def hook(i):
        def save(module,inputs,output):
            hidden=output[0] if isinstance(output,tuple) else output
            last[i]=hidden[0,prompt_length-1].detach().float().cpu().numpy().copy()
            reasoning[i]=hidden[0,reasoning_positions].detach().float().cpu().numpy().copy()
        return save
    try:
        for i,layer in enumerate(layers):handles.append(layer.register_forward_hook(hook(i)))
        tensor=torch.tensor([ids],device=device)
        with torch.inference_mode():
            out=model.base_model(input_ids=tensor,attention_mask=torch.ones_like(tensor),use_cache=False,return_dict=True)
        return np.stack([last[i] for i in range(len(layers))]),np.stack([reasoning[i] for i in range(len(layers))]),out.last_hidden_state
    finally:
        for handle in handles:handle.remove()


def score_positions(model,hidden,ids,positions):
    import torch
    if not positions:return {'n_tokens':0,'mean_token_nll':None,'top5_fraction':None}
    nll=0.;hits=0
    with torch.inference_mode():
        head=model.get_output_embeddings()
        for start in range(0,len(positions),64):
            pos=positions[start:start+64];target=torch.tensor([ids[p] for p in pos],device=head.weight.device)
            logits=head(hidden[0,[p-1 for p in pos]].to(head.weight.device)).float()
            nll-=logits.log_softmax(-1).gather(-1,target[:,None]).sum().item()
            hits+=(logits.topk(5,dim=-1).indices==target[:,None]).any(-1).sum().item()
    return dict(n_tokens=len(positions),mean_token_nll=nll/len(positions),top5_fraction=hits/len(positions))


def execute(payload, output_root, tiny=False, checkpoint=None, model=None):
    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM,GptOssConfig,Mxfp4Config
    import collusion.runs as rh
    from fidelity import score_hidden
    rh.RUNS=Path(output_root);rh.INDEX=rh.RUNS/'index.jsonl'
    run=rh.start_run('e02-gpt-oss-fidelity',experiment='E02',model=MODEL,settings={'revision':REVISION,'tiny_random':tiny,'requests':len(payload['rows']),'history_reasoning':payload['history_reasoning']})
    start=time.monotonic()
    reused_model=model is not None
    if reused_model:
        model.eval()
    elif tiny:
        config=GptOssConfig(vocab_size=201088,hidden_size=32,intermediate_size=32,num_hidden_layers=2,num_attention_heads=4,num_key_value_heads=2,head_dim=8,num_local_experts=4,num_experts_per_tok=2)
        model=AutoModelForCausalLM.from_config(config,attn_implementation='eager').float().eval()
    else:
        model=AutoModelForCausalLM.from_pretrained(MODEL,revision=REVISION,local_files_only=True,
            quantization_config=Mxfp4Config(dequantize=True),dtype=torch.bfloat16,device_map={'':'cuda:0'},attn_implementation='eager').eval()
        assert all(p.dtype==torch.bfloat16 or (p.dtype==torch.float32 and ('layernorm' in name or '.norm.' in name)) for name,p in model.named_parameters() if p.is_floating_point())
        assert all(p.device.type=='cuda' for p in model.parameters())
    load_seconds=time.monotonic()-start;device=model.get_input_embeddings().weight.device
    index=[]
    for i,row in enumerate(payload['rows']):
        if time.monotonic()-start>1200:raise TimeoutError('Replay wall guard reached')
        prompt=row['prompt_ids'];reply=row['reply_ids'];ids=prompt+reply
        assert digest(prompt)==row['prompt_sha256']
        assert len(ids)<=16384
        last,reasoning,hidden=capture(model,ids,len(prompt),row['reasoning_positions'],device)
        expected=(model.config.num_hidden_layers,model.config.hidden_size)
        assert last.shape==expected and reasoning.shape==(expected[0],len(row['reasoning_positions']),expected[1])
        assert np.isfinite(last).all() and np.isfinite(reasoning).all()
        fidelity=score_hidden(model,hidden,len(prompt),reply) if reply else dict(n_reply_tokens=0,mean_token_nll=None,top5_fraction=None,status='missing_or_empty_reply')
        segments={name:score_positions(model,hidden,ids,row[name+'_positions']) for name in ['reasoning','answer']}
        del hidden
        filename=f'request-{i:04}.npz'
        np.savez_compressed(run.dir/filename,residual_last=last,residual_reasoning=reasoning,
                            input_ids=np.asarray(ids),reasoning_positions=np.asarray(row['reasoning_positions']),
                            layer_indices=np.arange(expected[0]))
        record={k:v for k,v in row.items() if k not in ['prompt_ids','reply_ids']}
        record.update(file=filename,last_shape=list(last.shape),reasoning_shape=list(reasoning.shape),fidelity=fidelity,segments=segments)
        index.append(record);rh.write_json_atomic(run.dir/'index.json',index)
        if checkpoint and (i+1)%10==0:checkpoint()
        print('PROGRESS',i+1,len(payload['rows']),fidelity,flush=True)
    summary={'requests':len(index),'model_load_seconds':load_seconds,'wall_seconds':time.monotonic()-start,
             'reused_model':reused_model,'versions':{n:importlib.metadata.version(n) for n in ['torch','transformers','accelerate','openai-harmony']},
             'model_config':model.config.to_dict(),'parameter_dtypes':sorted({str(p.dtype)for p in model.parameters()}),
             'peak_cuda_bytes':torch.cuda.max_memory_allocated() if torch.cuda.is_available() else None}
    for name in ['all','reasoning','answer']:
        vals=[r['fidelity'] if name=='all' else r['segments'][name] for r in index]
        key='n_reply_tokens' if name=='all' else 'n_tokens';total=sum(v[key] for v in vals)
        summary[name]={'n_tokens':total,**{metric:sum(v[metric]*v[key] for v in vals if v[key])/total if total else None for metric in ['mean_token_nll','top5_fraction']}}
    rh.write_json_atomic(run.dir/'summary.json',summary);run.result(**summary);run.finish()
    if checkpoint:checkpoint()
    return run.dir


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('episodes',nargs='*');p.add_argument('--output');p.add_argument('--tiny-plan');a=p.parse_args()
    if a.tiny_plan:
        payload=json.loads(Path(a.tiny_plan).read_text());payload['rows']=payload['rows'][:1]
        print(execute(payload,ROOT/'runs',tiny=True))
    else:plan(a.episodes,a.output)
