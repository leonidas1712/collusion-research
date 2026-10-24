"""Freeze replay2 inputs and exact shared branch histories; no GPU or API calls."""
import copy
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
BRANCH='20261025-0000-e05-branching-check'
RUN_LIST=ROOT/'experiments/E02-activation-replay/manifests/replay2_runs.txt'

def main():
    paths=[ROOT/p for p in RUN_LIST.read_text().splitlines() if p.strip()]
    run=start_run('e02-replay2-plan',experiment='E02',parents=[p.name for p in paths]+[BRANCH],settings={'approval':'Aboard #609/#610','hard_cap_usd':8,'model':MODEL,'revision':REV,'all_target_requests':True})
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
        # Synthetic input containers hold only a real shared history. There is no observed reply to this counterfactual API call.
        branchdir=run.dir/'episodes';branchdir.mkdir()
        points=[p for p in json.loads((ROOT/'runs'/BRANCH/'points.json').read_text()) if p['score'] is not None];assert len(points)==23
        for k,point in enumerate(points):
            parent_run,parent_file=point['episode'].split('/');parent=ROOT/'runs'/parent_run/'episodes'/parent_file;ep=json.loads(parent.read_text());idx=point['request_idx'];record=ep['requests'][idx];request=copy.deepcopy(record['request']);t=point['branch_round']
            events=[e for e in ep['channel'] if e['round']==t and e['actor']=='recruiter']
            for event in reversed(events):
                expected=ep['scenario_spec']['channel_format'].format(actor=event['actor'],name=ep['scenario_spec']['actor_names'][event['actor']],content=event['content'])
                assert request['messages'].pop()=={'role':'user','content':expected}
            assert request['messages'] and any(m['role']=='assistant' for m in request['messages'])
            # Every observed continuation starts from this same target history before its new peer deliveries.
            summary_path=ROOT/point['summary_file'];summary=json.loads(summary_path.read_text())
            for filename in summary['branch_files']:
                b=json.loads((summary_path.parent/filename).read_text());r=next(r for r in b['requests'] if r['actor']=='target' and r['round']==t);messages=copy.deepcopy(r['request']['messages'])
                for event in reversed([e for e in b['channel'] if e['round']==t and e['actor']=='recruiter']):
                    expected=b['scenario_spec']['channel_format'].format(actor=event['actor'],name=b['scenario_spec']['actor_names'][event['actor']],content=event['content'])
                    assert messages.pop()=={'role':'user','content':expected}
                assert messages==request['messages']
            name=f'shared-branch-{k:04d}.json';path=branchdir/name
            synthetic={'episode_id':name[:-5],'status':'complete','fake':False,'input_only':True,'scenario_spec':ep['scenario_spec'],'condition':ep['condition'],
                       'label':{'objective_success':False,'valid_for_comparison':False},'requests':[{'actor':'target','round':t,'attempt':1,'request':request,'response':None}],
                       'shared_history_provenance':{'parent_episode':point['episode'],'parent_request_idx':idx,'parent_request_sha256':digest(record['request']),'branch_point':point,'reason_no_reply':'No observed target reply at pre-peer shared checkpoint'}}
            raw=json.dumps(synthetic,ensure_ascii=False,indent=2).encode();path.write_bytes(raw)
            prompt,ids,_,thinking=render(tok,request,'from-request');assert not thinking
            assert any(token in prompt for token in ep['scenario_spec']['honeypots'])
            inputs.append(dict(run_id=run.id,episode_key=run.id+'/'+name,episode_file=str(path.relative_to(ROOT)),episode_sha256=digest(raw),request_idx=0,round=t,step_in_turn=1,n_tokens=len(ids),
                request_sha256=digest(request),prompt_sha256=digest(prompt.encode()),input_ids_sha256=digest(ids),token_in_context=True,first_request_in_turn=True,acts_this_step=False,before_first_action=True,
                action_request_idx=None,valid_for_comparison=False,family_id=point['family'],scenario='v1-shared-branch-history',condition='recruiting',tactic_id='T0',shared_branch_history=True,parent_episode=point['episode'],branch_round=t))
        assert len({(r['run_id'],r['episode_file'],r['request_idx']) for r in inputs})==len(inputs)
        order=np.argsort([r['n_tokens'] for r in inputs]);chosen=set(int(order[k]) for k in np.linspace(0,len(order)-1,25,dtype=int));chosen.add(next(i for i,r in enumerate(inputs) if r['shared_branch_history']))
        for filename,rows in [('all.jsonl',inputs),('benchmark.jsonl',[r for i,r in enumerate(inputs) if i in chosen]),('remaining.jsonl',[r for i,r in enumerate(inputs) if i not in chosen])]:
            (run.dir/filename).write_text(''.join(json.dumps(r)+'\n' for r in rows))
        (run.dir/'episodes.json').write_text(json.dumps(epnotes,indent=2));(run.dir/'run-list.txt').write_bytes(RUN_LIST.read_bytes())
        summary=dict(source_run_folders=len(paths),complete_episodes=len(epnotes),by_scenario=dict(counts),requests=len(inputs),real_requests=len(inputs)-23,shared_histories=23,
                     prompt_tokens=sum(r['n_tokens'] for r in inputs),token_quantiles=np.quantile([r['n_tokens'] for r in inputs],[0,.5,.9,.99,1]).tolist(),benchmark_requests=len(chosen),
                     benchmark_tokens=sum(r['n_tokens'] for i,r in enumerate(inputs) if i in chosen),uncompressed_activation_bytes=len(inputs)*64*5120*4,
                     source_list_sha256=digest(RUN_LIST.read_bytes()))
        (run.dir/'summary.json').write_text(json.dumps(summary,indent=2));run.result(**summary);run.finish();print(json.dumps(summary,indent=2));print('PLAN_RUN',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':main()
