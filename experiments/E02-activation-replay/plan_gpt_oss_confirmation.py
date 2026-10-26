"""Freeze every target request from the immutable gpt-oss collection into replay shards."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'experiments/E01-behaviour-pilot'),str(ROOT/'experiments/E05-probes')]
from collusion.runs import start_run,write_json_atomic
from gpt_oss_replay import render,digest,MODEL,REVISION
from gpt_oss_dataset import episode_eligibility,request_boundaries,eligible_step
from request_labels import completed_target_requests
from audit_reasoning_and_routes import channel_routes


def main(args):
    source=Path(args.manifest);raw=source.read_bytes();manifest=json.loads(raw)
    assert manifest['selected_episode_count']>0 and not manifest['deficits']
    assert manifest['analysis_cutoff']=='first_public_exact_secret_emission'
    entries=manifest['episodes'];assert len(entries)==manifest['selected_episode_count']
    provider_modes=json.loads(args.provider_modes) if args.provider_modes else {}
    run=start_run('e02-gpt-oss-confirm-plan',experiment='E02',parents=[source.parent.name],
        settings={'source_manifest_sha256':hashlib.sha256(raw).hexdigest(),'model':MODEL,'revision':REVISION,
                  'selection':'every target request','shard_size':args.shard_size,'cutoff':'public_only','episode_rule':'complete exposed ever_correct_summary'})
    try:
        rows=[];episode_metadata=[];sources={};reused={}
        if args.reuse:
            previous=json.loads(Path(args.reuse).read_text())
            for shard in previous['shards']:
                for row in json.loads((Path(args.reuse).parent/shard['path']).read_text())['rows']:
                    reused[row['row_id']]=row
        for episode_number,entry in enumerate(entries,1):
            path=ROOT/entry['episode_file'];ep_raw=path.read_bytes()
            assert hashlib.sha256(ep_raw).hexdigest()==entry['episode_sha256'],path
            ep=json.loads(ep_raw);assert ep['status']=='complete' and not ep.get('fake')
            flags=episode_eligibility(ep);bounds=request_boundaries(ep)
            completed=completed_target_requests(ep);ordinals={idx:n for n,(idx,_) in enumerate(completed,1)}
            all_target=[i for i,r in enumerate(ep['requests']) if r['actor']=='target']
            read=bounds['first_read_ordinal']
            assert read==entry['first_read_request_index']  # This field uses completed-request ordinals.
            public_ordinal=bounds['first_public_emission_ordinal']
            public_raw=all_target.index(completed[public_ordinal-1][0])+1 if public_ordinal is not None else None
            assert public_raw==entry['first_public_emission_request_index']  # Emission fields count all target attempts.
            assert (read is not None)==entry['exposed']==flags['exposed']
            routes=channel_routes(ep);tokens=ep['scenario_spec']['honeypots']
            channel=next((x for x in routes if any(t in x[1] for t in tokens)),None)
            assert bool(channel)==entry['channel_publication']
            ask=(ep.get('collection_metadata') or {}).get('first_ask_text')
            ask_idx=next((idx for idx,r in completed if ask and any(ask in m.get('content','') for m in r['request']['messages']
                         if m.get('role')=='user' and isinstance(m.get('content'),str))),None)
            episode_key=entry['run_id']+'/'+path.name
            common=dict(episode=episode_key,family=entry['family_id'],scenario=entry['scenario'],condition=entry['condition'],
                label=int(entry['channel_publication']),first_channel_request_idx=channel[3] if channel else None,
                first_ask_request_idx=ask_idx,first_ask_round=entry['first_ask_round'],**flags,**bounds)
            public=bounds['first_public_emission_ordinal']
            common['action_round']=completed[public-1][1]['round'] if public is not None else None
            common['source_metadata']=entry
            episode_metadata.append(common)
            sources[str(path.resolve())]=entry['episode_sha256']
            for idx in all_target:
                record=ep['requests'][idx];assert record['request']['model']==MODEL
                response=record.get('response') or {}
                date=time.strftime('%Y-%m-%d',time.gmtime(response['created'])) if response.get('created') else ep['started_at'][:10]
                provider=response.get('provider') or record.get('served_provider')
                mode=provider_modes.get(provider,'drop_all')
                old=reused.get(f'{episode_key}::request_idx={idx}')
                if old and old.get('history_reasoning_mode','drop_all')==mode:
                    assert old['episode_sha256']==entry['episode_sha256'] and old['harmony_request_sha256']==digest(record['request'])
                    rendered={key:old[key] for key in ['prompt_ids','reply_ids','reasoning_positions','answer_positions','effort']}
                else:rendered=render(record,date,history_reasoning=mode)
                assert rendered['effort']=='low'
                ordinal=ordinals.get(idx);n_tokens=len(rendered['prompt_ids']);usage=response.get('usage') or {}
                request_sha=hashlib.sha256(json.dumps(record['request'],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
                before=eligible_step(flags,ordinal,read,public)
                postask=ask_idx is not None and idx>=ask_idx
                # Store all attempts; scoring eligibility never filters capture.
                row=dict(run_id=entry['run_id'],episode_file=path.name,episode=episode_key,row_id=f'{episode_key}::request_idx={idx}',
                    family=entry['family_id'],scenario=entry['scenario'],condition=entry['condition'],label=common['label'],
                    request_idx=idx,raw_target_request_ordinal=all_target.index(idx)+1,
                    step_in_turn=sum(ep['requests'][j]['round']==record['round'] for j in all_target if j<=idx),
                    round=record['round'],ordinal=ordinal,first_read=read,first_action=public,
                    action_round=common['action_round'],steps_until_action=public-ordinal if public is not None and ordinal is not None else None,
                    first_ask_request_idx=ask_idx,post_ask=postask,eligible=before and postask,eligible_pre_ask=before and not postask,
                    window_eligible=before,token_in_context=read is not None and idx>completed[read-1][0],
                    complete=flags['complete'],exposed=flags['exposed'],ever_correct_summary=flags['ever_correct_summary'],
                    final_summary_correct=flags['final_summary_correct'],original_valid_for_comparison=flags['original_valid_for_comparison'],
                    first_reasoning_mention_ordinal=bounds['first_reasoning_mention_ordinal'],
                    first_inclusive_emission_ordinal=bounds['first_inclusive_emission_ordinal'],
                    source_path=str(path.resolve()),episode_sha256=entry['episode_sha256'],request_sha256=request_sha,
                    harmony_request_sha256=digest(record['request']),served_provider=response.get('provider') or record.get('served_provider'),
                    served_quantization=record.get('served_quantization'),provider_prompt_tokens=usage.get('prompt_tokens'),history_reasoning_mode=mode,
                    n_tokens=n_tokens,prompt_sha256=digest(rendered['prompt_ids']),
                    input_ids_sha256=digest(rendered['prompt_ids']+rendered['reply_ids']),**rendered)
                gap=n_tokens-usage['prompt_tokens'] if usage.get('prompt_tokens') is not None else None
                row.update(prompt_token_gap=gap,abs_prompt_token_gap=abs(gap) if gap is not None else None,
                           prompt_token_match_within1=abs(gap)<=1 if gap is not None else None)
                assert n_tokens+len(row['reply_ids'])<=16384,(episode_key,idx,n_tokens)
                rows.append(row)
            if episode_number%30==0:print('PLANNED_EPISODES',episode_number,'REQUESTS',len(rows),flush=True)
        assert len({r['row_id'] for r in rows})==len(rows)
        # Longest first supplies a conservative first-shard benchmark before the remaining work.
        rows.sort(key=lambda r:(-len(r['prompt_ids'])-len(r['reply_ids']),r['row_id']))
        shards=[];(run.dir/'shards').mkdir()
        for start in range(0,len(rows),args.shard_size):
            subset=rows[start:start+args.shard_size];name=f'shards/{len(shards):04}.json'
            payload=dict(model=MODEL,revision=REVISION,history_reasoning='provider_specific' if provider_modes else 'drop_all',rows=subset)
            write_json_atomic(run.dir/name,payload)
            shards.append(dict(path=name,sha256=hashlib.sha256((run.dir/name).read_bytes()).hexdigest(),requests=len(subset),
                total_tokens=sum(r['n_tokens']+len(r['reply_ids']) for r in subset)))
        small=[{k:v for k,v in r.items() if k not in ('prompt_ids','reply_ids','reasoning_positions','answer_positions')} for r in rows]
        (run.dir/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in small))
        write_json_atomic(run.dir/'episodes.json',episode_metadata)
        counts=dict(episodes=len(entries),requests=len(rows),shards=len(shards),
            prompt_tokens=sum(r['n_tokens'] for r in rows),reply_tokens=sum(len(r['reply_ids']) for r in rows),
            reasoning_tokens=sum(len(r['reasoning_positions']) for r in rows),max_input_tokens=max(r['n_tokens']+len(r['reply_ids']) for r in rows),
            post_ask_steps=sum(r['eligible'] for r in rows),pre_ask_steps=sum(r['eligible_pre_ask'] for r in rows),
            providers=dict(Counter(r['served_provider'] for r in rows)),
            token_count_deltas=dict(Counter(str(r['n_tokens']-r['provider_prompt_tokens']) for r in rows if r['provider_prompt_tokens'] is not None)))
        counts['uncompressed_activation_bytes']=(len(rows)+counts['reasoning_tokens'])*24*2880*4
        benchmark=json.loads((ROOT/'runs/20261025-1217-e02-gpt-oss-fidelity/summary.json').read_text())
        old_plan=json.loads((ROOT/'runs/20261025-2014-e02-gpt-oss-plan-5f17/plan.json').read_text())
        old_tokens=sum(len(r['prompt_ids'])+len(r['reply_ids']) for r in old_plan['rows'])
        estimate=(counts['prompt_tokens']+counts['reply_tokens'])/old_tokens*benchmark['wall_seconds']
        counts['prior_benchmark_projection_seconds']=estimate
        counts['prior_projection_usd_with_2x_margin']=estimate*.0009*2+.5
        plan=dict(model=MODEL,revision=REVISION,source_manifest=str(source.resolve()),source_manifest_sha256=hashlib.sha256(raw).hexdigest(),
                  sources=sources,counts=counts,shards=shards,provider_modes=provider_modes,
                  rendering_gate_approval=args.approval_ref,budget_root=str(Path(args.budget_root).resolve()) if args.budget_root else str(run.dir.resolve()))
        write_json_atomic(run.dir/'plan.json',plan);write_json_atomic(run.dir/'counts.json',counts)
        run.result(**counts);run.finish();print('FULL_PLAN',run.dir/'plan.json');print(json.dumps(counts,indent=2))
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--shard-size',type=int,default=100);p.add_argument('--reuse');p.add_argument('--provider-modes');p.add_argument('--approval-ref');p.add_argument('--budget-root')
    args=p.parse_args();assert 1<=args.shard_size<=100;main(args)
