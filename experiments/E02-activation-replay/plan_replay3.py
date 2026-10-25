"""Freeze balanced-batch replay3 inputs; no GPU or API calls."""
import json
import sys
from collections import Counter
from pathlib import Path
import numpy as np
from transformers import AutoTokenizer
from replay import ROOT,digest,render,request_rows,start_run
sys.path.insert(0,str(ROOT/'experiments/E01-behaviour-pilot'))
from request_labels import request_index_labels,completed_target_requests

MODEL='Qwen/Qwen3-32B'
REV='9216db5781bf21249d130ec9da846c4624c16137'
RUN_LIST=ROOT/'experiments/E02-activation-replay/manifests/replay3_runs.txt'

def main():
    paths=[ROOT/p for p in RUN_LIST.read_text().splitlines() if p.strip()]
    run=start_run('e02-replay3-plan',experiment='E02',parents=[p.name for p in paths],settings={'approval':'Aboard #698: Leo approval relayed by Claude','hard_cap_usd':4,'model':MODEL,'revision':REV,'all_target_requests':True})
    try:
        tok=AutoTokenizer.from_pretrained(ROOT/'runs/20261024-1018-e02-activation-replay/tokenizer',local_files_only=True)
        inputs=[];counts=Counter();epnotes=[]
        for directory in paths:
            assert directory.is_dir()
            for path in sorted((directory/'episodes').glob('*.json')):
                if '.partial.' in path.name or '.attempt-' in path.name:continue
                raw=path.read_bytes();ep=json.loads(raw)
                if ep.get('status')!='complete':continue
                assert not ep.get('fake');lab=ep['label'];meta=ep['scenario_spec']['metadata']
                calculated=request_index_labels(ep,lab)
                for k,v in calculated.items():assert lab.get(k)==v,(path.name,k,lab.get(k),v)
                completed=completed_target_requests(ep);ordinal={idx:n for n,(idx,_) in enumerate(completed,1)}
                action=lab['first_action_target_request'];action_idx=completed[action-1][0] if action else None
                tokens=ep['scenario_spec']['honeypots'];assert tokens and all(isinstance(t,str) and t for t in tokens)
                scenario=meta.get('spray_row_id') or 'deploy-token-v2'
                assert int(meta['family_id'])>=8001,(directory.name,meta['family_id'])
                first={}
                for idx,step,record in request_rows(ep):
                    first.setdefault(record['round'],idx)
                    assert record['request']['model']=='qwen/qwen3-32b'
                    prompt,ids,_,thinking=render(tok,record['request'],'from-request');assert not thinking
                    assert len(ids)<=32768
                    exposed=any(t in prompt for t in tokens)
                    inputs.append(dict(run_id=directory.name,episode_key=directory.name+'/'+path.name,episode_file=str(path.relative_to(ROOT)),episode_sha256=digest(raw),
                        request_idx=idx,round=record['round'],step_in_turn=step,n_tokens=len(ids),request_sha256=digest(record['request']),prompt_sha256=digest(prompt.encode()),input_ids_sha256=digest(ids),
                        token_in_context=exposed,first_request_in_turn=idx==first[record['round']],acts_this_step=idx==action_idx,before_first_action=action_idx is None or idx<action_idx,
                        action_request_idx=action_idx,valid_for_comparison=lab['valid_for_comparison'],family_id=str(meta['family_id']),scenario=scenario,condition=meta['peer_condition'],tactic_id=meta.get('tactic_id','T0'),
                        target_completed_ordinal=ordinal.get(idx),first_token_read_request=lab['first_token_read_request'],first_action_target_request=action,shared_branch_history=False))
                counts[scenario]+=1;epnotes.append(dict(episode_file=str(path.relative_to(ROOT)),sha256=digest(raw),scenario=scenario,condition=meta['peer_condition'],family_id=meta['family_id'],label=lab))
        assert len({(r['run_id'],r['episode_file'],r['request_idx']) for r in inputs})==len(inputs)
        order=np.argsort([r['n_tokens'] for r in inputs]);chosen=set(int(order[k]) for k in np.linspace(0,len(order)-1,25,dtype=int))
        for filename,rows in [('all.jsonl',inputs),('benchmark.jsonl',[r for i,r in enumerate(inputs) if i in chosen]),('remaining.jsonl',[r for i,r in enumerate(inputs) if i not in chosen])]:
            (run.dir/filename).write_text(''.join(json.dumps(r)+'\n' for r in rows))
        (run.dir/'episodes.json').write_text(json.dumps(epnotes,indent=2));(run.dir/'run-list.txt').write_bytes(RUN_LIST.read_bytes())
        summary=dict(source_run_folders=len(paths),complete_episodes=len(epnotes),by_scenario=dict(counts),requests=len(inputs),real_requests=len(inputs),shared_histories=0,
                     prompt_tokens=sum(r['n_tokens'] for r in inputs),token_quantiles=np.quantile([r['n_tokens'] for r in inputs],[0,.5,.9,.99,1]).tolist(),benchmark_requests=len(chosen),
                     benchmark_tokens=sum(r['n_tokens'] for i,r in enumerate(inputs) if i in chosen),uncompressed_activation_bytes=len(inputs)*64*5120*4,
                     source_list_sha256=digest(RUN_LIST.read_bytes()))
        (run.dir/'summary.json').write_text(json.dumps(summary,indent=2));run.result(**summary);run.finish();print(json.dumps(summary,indent=2));print('PLAN_RUN',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':main()
