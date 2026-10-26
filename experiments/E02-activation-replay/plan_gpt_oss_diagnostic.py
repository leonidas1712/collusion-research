"""Input-only provider/gap-stratified paired fidelity plan, approved before provider-mode selection."""
from collections import Counter,defaultdict
import hashlib,json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic
from gpt_oss_replay import render,digest,MODEL,REVISION


def main():
    source_plan=ROOT/'runs/20261025-2226-e02-gpt-oss-full-plan'
    source=json.loads((source_plan/'plan.json').read_text());base=[json.loads(s) for s in (source_plan/'rows.jsonl').read_text().splitlines()]
    episode_cache={};buckets=defaultdict(list)
    for r in base:
        if r['episode'] not in episode_cache:
            raw=Path(r['source_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['episode_sha256']
            episode_cache[r['episode']]=json.loads(raw)
        rec=episode_cache[r['episode']]['requests'][r['request_idx']];msgs=rec['request']['messages']
        last_user=max((i for i,m in enumerate(msgs) if m['role']=='user'),default=-1)
        intra=any(m['role']=='tool' for m in msgs[last_user+1:]);gap=abs(r['n_tokens']-r['provider_prompt_tokens'])
        if r['served_provider']=='AkashML':
            band=('large' if gap>20 else 'small') if intra else ('mismatch' if gap>1 else 'matched')
            bucket=f'AkashML:{"intra" if intra else "not_intra"}:{band}'
        else:bucket=f'DekaLLM:{"intra" if intra else "not_intra"}'
        buckets[bucket].append(r)
    quotas={'AkashML:intra:large':10,'AkashML:intra:small':10,'AkashML:not_intra:mismatch':5,
            'AkashML:not_intra:matched':5,'DekaLLM:intra':10,'DekaLLM:not_intra':10}
    run=start_run('e02-gpt-oss-paired-diagnostic-plan',experiment='E02',parents=[source_plan.name],settings={
        'approval':'provider-stratified paired fidelity diagnostic','selection':'provider/intra-turn/gap only; hash order seed1182; outcomes not used',
        'quotas':quotas,'phase_ceiling_usd':1.5,'shared_total_cap_usd':20})
    try:
        selected=[]
        for bucket,n in quotas.items():
            candidates=sorted(buckets[bucket],key=lambda r:hashlib.sha256(('1182:'+r['row_id']).encode()).hexdigest())
            assert len(candidates)>=n
            selected.extend((bucket,r) for r in candidates[:n])
        rows=[];sources={}
        for bucket,r in selected:
            record=episode_cache[r['episode']]['requests'][r['request_idx']]
            date=time.strftime('%Y-%m-%d',time.gmtime(record['response']['created']))
            assert digest(record['request'])==r['harmony_request_sha256']
            for mode in ['drop_all','current_turn']:
                rendered=render(record,date,history_reasoning=mode);n_tokens=len(rendered['prompt_ids'])
                row={**r,**rendered,'source_row_id':r['row_id'],'row_id':r['row_id']+'::renderer='+mode,
                     'diagnostic_only':True,'selection_stratum':bucket,'eligible':False,'eligible_pre_ask':False,
                     'history_reasoning_mode':mode,'n_tokens':n_tokens,'prompt_sha256':digest(rendered['prompt_ids']),
                     'input_ids_sha256':digest(rendered['prompt_ids']+rendered['reply_ids'])}
                rows.append(row)
            sources[r['source_path']]=r['episode_sha256']
        assert len(rows)==100 and len({r['row_id'] for r in rows})==100
        (run.dir/'shards').mkdir();payload=dict(model=MODEL,revision=REVISION,history_reasoning='paired_diagnostic',rows=rows)
        write_json_atomic(run.dir/'shards/0000.json',payload)
        total=sum(len(r['prompt_ids'])+len(r['reply_ids']) for r in rows)
        counts=dict(episodes=len(sources),requests=len(rows),source_requests=50,shards=1,total_tokens=total,
                    prior_projection_usd_with_2x_margin=total/142324*100.668*.0009*2+.5)
        plan=dict(model=MODEL,revision=REVISION,source_manifest=source['source_manifest'],source_manifest_sha256=source['source_manifest_sha256'],
            sources=sources,counts=counts,rendering_gate_approval='provider-mode paired diagnostic only',
            budget_root=str(source_plan),phase_ceiling_usd=1.5,
            shards=[dict(path='shards/0000.json',sha256=hashlib.sha256((run.dir/'shards/0000.json').read_bytes()).hexdigest(),requests=100,total_tokens=total)])
        write_json_atomic(run.dir/'plan.json',plan);write_json_atomic(run.dir/'counts.json',counts)
        write_json_atomic(run.dir/'selection.json',[dict(stratum=bucket,row_id=r['row_id']) for bucket,r in selected])
        run.result(**counts);run.finish();print('DIAGNOSTIC_PLAN',run.dir/'plan.json');print(json.dumps(counts,indent=2))
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':main()
