"""Offline exact-token prefix audit of the main replay input corpus."""
import json
import sys
from collections import Counter
from pathlib import Path
from transformers import AutoTokenizer
from replay import ROOT, digest, first_leak_request, render, request_rows, start_run
from plan_main import MODEL, REVISION, boundary, token_value


def action_request(episode, token):
    candidates=[]
    channel=first_leak_request(episode)
    if channel is not None:candidates.append(channel)
    _,events=boundary(episode,token)
    for event in events:
        if event['kind']!='other_file':continue
        matches=[]
        for idx,_,record in request_rows(episode):
            for choice in (record.get('response') or {}).get('choices') or []:
                if any(call.get('id')==event['call_id'] for call in choice.get('message',{}).get('tool_calls') or []):
                    matches.append(idx)
        if len(matches)!=1:raise ValueError(f'Cannot uniquely locate forbidden write {event}')
        candidates+=matches
    if events and not candidates:raise ValueError('Cannot locate forbidden action in requests')
    return min(candidates,default=None)


def common_prefix(a,b):
    for i,(x,y) in enumerate(zip(a,b)):
        if x!=y:return i
    return min(len(a),len(b))


def selected_calls(calls, action):
    return [call for call in calls if action is None or call[0] <= action]


def main():
    plan=ROOT/'runs'/sys.argv[1]
    dirs=json.loads((plan/'run_ids.json').read_text())
    run=start_run('e02-step-prefix-plan',experiment='E02',parents=[plan.name,*dirs],settings={'model':MODEL,'revision':REVISION,'scope':'include the action-producing request in independent prompt replay','planning_only':True,'step_cutoff':'request_idx <= action-producing request; includes acts-this-step row'})
    tokenizer=AutoTokenizer.from_pretrained(MODEL,revision=REVISION,local_files_only=True)
    rows=[]; pairs=[]; episodes=[]; counts=Counter(); examples=[]
    suffix_ids=tokenizer.encode('<think>\n\n</think>\n\n',add_special_tokens=False)
    assert len(suffix_ids)==4
    for epinfo in json.loads((plan/'episodes.json').read_text()):
        path=ROOT/epinfo['episode_file'];raw=path.read_bytes();assert digest(raw)==epinfo['episode_sha256']
        ep=json.loads(raw);token=token_value(ep);action=action_request(ep,token)
        calls=[]
        for idx,step,record in request_rows(ep):
            rendered,ids,changes,thinking=render(tokenizer,record['request'],'from-request')
            assert thinking is False
            calls.append((idx,step,record,rendered,ids))
        first_indices={}
        for idx,step,record,_,_ in calls:first_indices.setdefault(record['round'],idx)
        episode_pairs=[]
        for prev,nxt in zip(calls,calls[1:]):
            i=common_prefix(prev[4],nxt[4]);extends=i==len(prev[4]);strict=extends and len(nxt[4])>len(prev[4])
            item={'episode_key':epinfo['episode_key'],'from_request_idx':prev[0],'to_request_idx':nxt[0],
                'from_round':prev[2]['round'],'to_round':nxt[2]['round'],'from_n_tokens':len(prev[4]),'to_n_tokens':len(nxt[4]),
                'common_prefix_tokens':i,'prefix':extends,'strict_prefix':strict,
                'across_rounds':prev[2]['round']!=nxt[2]['round'],
                'retained_pair':action is None or nxt[0]<=action,
                'trimmed_suffix_prefix':prev[4][-4:]==suffix_ids and nxt[4][:len(prev[4])-4]==prev[4][:-4],
                'only_terminal_suffix_diverges':i==len(prev[4])-4}
            pairs.append(item);episode_pairs.append(item)
            if not extends:
                counts['nonprefix']+=1
                if not item['trimmed_suffix_prefix'] or len(examples)<12 or not any(e['across_rounds']==item['across_rounds'] for e in examples):
                    clean=lambda text:text.replace(token,'<SYNTHETIC_TOKEN>')
                    examples.append({**item,'old_tail_from_divergence':clean(tokenizer.decode(prev[4][i:i+40])),
                        'new_tail_from_divergence':clean(tokenizer.decode(nxt[4][i:i+40])),
                        'preceding_text':clean(tokenizer.decode(prev[4][max(0,i-12):i]))})
            elif not strict:counts['equal_retry']+=1
            else:counts['strict_prefix']+=1
        selected=selected_calls(calls,action)
        inclusive=[call for call in calls if action is None or call[0]<=action]
        dedup={}
        for idx,step,record,rendered,ids in selected:
            row={k:epinfo[k] for k in ('episode_key','run_id','episode_file','episode_sha256','cohort','condition','family_id','tactic_id','valid_for_comparison')}
            row.update(request_idx=idx,round=record['round'],step_in_turn=step,attempt=record.get('attempt',1),
                first_request_in_turn=idx==first_indices[record['round']],acts_this_step=idx==action,before_first_action=action is None or idx<action,request_error=record.get('error'),
                n_tokens=len(ids),token_in_context=token in rendered,action_request_idx=action,
                first_boundary_violation_round=epinfo['first_boundary_violation_round'],label_will_violate=int(action is not None),
                request_sha256=digest(record['request']),prompt_sha256=digest(rendered.encode()),input_ids_sha256=digest(ids),
                last_prompt_token_index=len(ids)-1)
            rows.append(row);dedup.setdefault(digest(ids),len(ids))
        # Equality does permit one shared forward for retry-identical inputs, despite not being strict extension.
        full_final=calls[-1]
        final_covers=sum(full_final[4][:len(call[4])]==call[4] for call in selected)
        trimmed_covers=sum(call[4][-4:]==suffix_ids and full_final[4][:len(call[4])-4]==call[4][:-4] for call in selected)
        episodes.append({'episode_key':epinfo['episode_key'],'action_request_idx':action,'selected_steps':len(selected),
            'selected_tokens_independent':sum(len(c[4]) for c in selected),'selected_steps_inclusive':len(inclusive),
            'selected_tokens_inclusive':sum(len(c[4]) for c in inclusive),
            'unique_prompt_count':len(dedup),'unique_prompt_tokens':sum(dedup.values()),
            'last_selected_prompt_tokens':len(selected[-1][4]) if selected else 0,
            'final_episode_prompt_tokens':len(full_final[4]),'selected_steps_covered_by_final_prompt':final_covers,
            'selected_steps_trimmed_suffix_covered_by_final_prompt':trimmed_covers,
            'all_adjacent_prefixes':all(p['prefix'] for p in episode_pairs),
            'all_retained_adjacent_prefixes':all(p['prefix'] for p in episode_pairs if p['retained_pair'])})
    for name,data in [('steps',rows),('prefix_pairs',pairs)]:
        with (run.dir/f'{name}.jsonl').open('w') as f:
            for row in data:f.write(json.dumps(row)+'\n')
    (run.dir/'episodes.json').write_text(json.dumps(episodes,indent=2))
    (run.dir/'prefix_examples.json').write_text(json.dumps(examples,indent=2))
    bench=json.loads((ROOT/'runs/20261024-1556-e02-modal-benchmark-report/results.json').read_text())
    tokens=sum(row['n_tokens'] for row in rows);n=len(rows)
    low=tokens/bench['activation_prompt_tokens_per_second']+54
    high=n*bench['activation_seconds']/bench['requests']+54
    counts_by_group=[]
    for cohort,condition in sorted({(r['cohort'],r['condition']) for r in rows}):
        rs=[r for r in rows if (r['cohort'],r['condition'])==(cohort,condition)]
        counts_by_group.append({'cohort':cohort,'condition':condition,'episodes':len({r['episode_key'] for r in rs}),'steps':len(rs),'tokens':sum(r['n_tokens'] for r in rs)})
    summary={'episodes':len(episodes),'selected_episodes':sum(ep['selected_steps']>0 for ep in episodes),'steps':n,'prompt_tokens_independent':tokens,
        'selected_inclusive_steps':sum(ep['selected_steps_inclusive'] for ep in episodes),
        'selected_inclusive_prompt_tokens':sum(ep['selected_tokens_inclusive'] for ep in episodes),
        'first_request_in_turn_rows':sum(row['first_request_in_turn'] for row in rows),
        'token_not_in_context':sum(not row['token_in_context'] for row in rows),
        'acts_this_step_rows':sum(row['acts_this_step'] for row in rows),
        'positive_steps':sum(row['label_will_violate'] for row in rows),
        'invalid_comparison_steps':sum(row['valid_for_comparison'] is False for row in rows),
        'prefix_pairs':len(pairs),**dict(counts),
        'suffix_token_ids':suffix_ids,
        'pairs_prefix_after_trimming_suffix':sum(p['trimmed_suffix_prefix'] for p in pairs),
        'nonprefix_not_only_terminal_suffix':sum(not p['prefix'] and not p['only_terminal_suffix_diverges'] for p in pairs),
        'selected_steps_trimmed_suffix_covered_by_final_prompt':sum(ep['selected_steps_trimmed_suffix_covered_by_final_prompt'] for ep in episodes),
        'across_round_pairs':sum(p['across_rounds'] for p in pairs),
        'across_round_failures':sum(p['across_rounds'] and not p['prefix'] for p in pairs),
        'within_round_failures':sum(not p['across_rounds'] and not p['prefix'] for p in pairs),
        'retained_pairs':sum(p['retained_pair'] for p in pairs),
        'retained_nonprefix':sum(p['retained_pair'] and not p['prefix'] for p in pairs),
        'episodes_all_adjacent_prefixes':sum(ep['all_adjacent_prefixes'] for ep in episodes),
        'episodes_all_retained_adjacent_prefixes':sum(ep['all_retained_adjacent_prefixes'] for ep in episodes),
        'hypothetical_final_prompt_tokens':sum(ep['final_episode_prompt_tokens'] for ep in episodes),
        'hypothetical_last_selected_prompt_tokens':sum(ep['last_selected_prompt_tokens'] for ep in episodes),
        'selected_steps_covered_by_final_prompt':sum(ep['selected_steps_covered_by_final_prompt'] for ep in episodes),
        'unique_prompt_count':sum(ep['unique_prompt_count'] for ep in episodes),
        'unique_prompt_tokens':sum(ep['unique_prompt_tokens'] for ep in episodes),
        'min_tokens':min(row['n_tokens'] for row in rows),'max_tokens':max(row['n_tokens'] for row in rows),
        'activation_wall_minutes':[min(low,high)/60,max(low,high)/60],
        'activation_cost_usd':[min(low,high)*2.9452/3600,max(low,high)*3.2012/3600],
        'activation_budget_50pct_headroom':((max(low,high)-54)*1.5+54)*3.2012/3600,
        'raw_activation_bytes_by_layers':{str(l):n*l*5120*4 for l in (64,16,8)},'groups':counts_by_group}
    (run.dir/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
    print('PREFIX_EXAMPLES',json.dumps(examples[:3],indent=2))
    run.result(episodes=len(episodes),steps=n,tokens=tokens,nonprefix_pairs=counts['nonprefix'],planning_only=True)
    print('STEP_PLAN_RUN',run.id)

if __name__=='__main__':main()
