"""Join verified replay2 parts without altering their frozen labels or input hashes."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
from data import ROOT
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run

PLAN='20261025-0119-e02-replay2-plan'

def eligible_step(m):
    number=m.get('target_completed_ordinal');read=m.get('first_token_read_request');action=m.get('first_action_target_request')
    return bool(not m['shared_branch_history'] and m['valid_for_comparison'] and number is not None and read is not None and number>read and (action is None or number<action))


def main(args):
    sources=[ROOT/'runs'/name for name in args.replay_runs];plan=ROOT/'runs'/PLAN
    run=start_run('e05-replay2-data',experiment='E05',parents=[PLAN,*args.replay_runs],settings={'cache_layers':'all64','eligibility':'valid completed target request, ordinal > first read and ordinal < first action','shared_histories_excluded_from_training':True})
    try:
        wanted=[json.loads(s) for s in (plan/'all.jsonl').read_text().splitlines()];loaded={}
        frozen_labels={e['episode_file']:e['label'] for e in json.loads((plan/'episodes.json').read_text())}
        key=lambda r:(r['run_id'],Path(r['episode_file']).name,r['request_idx'])
        for source in sources:
            assert json.loads((source/'meta.json').read_text())['status']=='finished'
            provenance=json.loads((source/'provenance.json').read_text())
            assert provenance['model']=='Qwen/Qwen3-32B'
            assert provenance['revision']=='9216db5781bf21249d130ec9da846c4624c16137'
            assert provenance['precision']=='bf16' and provenance['dtype']=='bfloat16'
            for line in (source/'index.jsonl').read_text().splitlines():
                r=json.loads(line);assert key(r) not in loaded;loaded[key(r)]=(source,r)
        assert set(loaded)=={key(r) for r in wanted}
        cache=np.lib.format.open_memmap(run.dir/'features.npy',mode='w+',dtype='float32',shape=(len(wanted),64,5120));rows=[]
        for i,m in enumerate(wanted):
            source,r=loaded[key(m)];assert r['manifest_verified'] and r['manifest']==m
            for field in ('request_sha256','prompt_sha256','input_ids_sha256','n_tokens','episode_sha256'):assert r[field]==m[field]
            with np.load(source/r['artifact']) as a:
                value=a['residual_last'];assert value.shape==(64,5120) and np.isfinite(value).all();assert list(a['layer_indices'])==list(range(64));cache[i]=value
            label=r['label'];shared=m['shared_branch_history'];number=m.get('target_completed_ordinal');read=m.get('first_token_read_request');action=m.get('first_action_target_request')
            if not shared:assert label==frozen_labels[m['episode_file']]
            eligible=eligible_step(m)
            if eligible:assert m['token_in_context']
            outcome=bool(label.get('objective_success'))
            if outcome and not shared:assert action is not None
            row=dict(index=i,episode=m['episode_key'],family=m['family_id'],scenario=m['scenario'],condition=m['condition'],tactic=m['tactic_id'],round=m['round'],
                request_idx=m['request_idx'],ordinal=number,first_read=read,first_action=action,steps_until_action=(action-number) if action is not None and number is not None else None,
                label=int(outcome),kind=(label.get('semantic_judge') or {}).get('labels',{}).get('first_publication_kind'),valid=m['valid_for_comparison'],eligible=bool(eligible),
                token_in_context=m['token_in_context'],n_tokens=m['n_tokens'],shared_branch_history=shared,parent_episode=m.get('parent_episode'),branch_round=m.get('branch_round'),
                request_sha256=m['request_sha256'],prompt_sha256=m['prompt_sha256'],source_replay=source.name,source_artifact=r['artifact'],prompt_file=str(source/r['prompt_file']),
                action_round=None)
            rows.append(row)
        action_round={(r['episode'],r['ordinal']):r['round'] for r in rows if r['ordinal'] is not None}
        for r in rows:
            if r['first_action'] is not None:r['action_round']=action_round[(r['episode'],r['first_action'])]
        cache.flush();(run.dir/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        summary=dict(rows=len(rows),real_episodes=len({r['episode'] for r in rows if not r['shared_branch_history']}),eligible_rows=sum(r['eligible'] for r in rows),eligible_episodes=len({r['episode'] for r in rows if r['eligible']}),shared_histories=sum(r['shared_branch_history'] for r in rows))
        exclusions={}
        for episode in sorted({r['episode'] for r in rows if not r['shared_branch_history']}):
            records=[r for r in rows if r['episode']==episode]
            if any(r['eligible'] for r in records):continue
            first=records[0]
            reason='invalid' if not first['valid'] else 'never_read' if first['first_read'] is None else 'no_completed_step_in_strict_window'
            exclusions[episode]=reason
        summary['excluded_episode_reasons']={reason:list(exclusions.values()).count(reason) for reason in sorted(set(exclusions.values()))}
        (run.dir/'excluded-episodes.json').write_text(json.dumps(exclusions,indent=2))
        (run.dir/'summary.json').write_text(json.dumps(summary,indent=2));run.result(**summary);run.finish();print(json.dumps(summary));print('DATA_RUN',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('replay_runs',nargs='+');main(p.parse_args())
