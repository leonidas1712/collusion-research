"""Audit and refit the arXiv Qwen ladder with the GPT-OSS exact-emission rule."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'experiments/E01-behaviour-pilot')]
from collusion.runs import start_run,write_json_atomic
from request_labels import request_index_labels,completed_target_requests

DATA=ROOT/'runs/20261025-1026-e05-replay3-data-1d95'
SOURCE=ROOT/'runs/20261026-1237-e05-qwen-percall'
MAIN=ROOT/'runs/20261025-1456-e05-all-data-main'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def audit(restore_root, feature_path):
    base=[json.loads(s) for s in (DATA/'rows.jsonl').read_text().splitlines()]
    previous=json.loads((SOURCE/'label_audit.json').read_text())
    episodes={e['episode']:e for e in previous['episodes']}
    assert len(episodes)==338
    run=start_run('e05-qwen-any-public-audit',experiment='E05',parents=[DATA.name,SOURCE.name],settings={
        'phase':'label_and_feature_coverage_audit','no_gpu':True,'no_api':True,
        'source_rows_sha256':sha(DATA/'rows.jsonl'),'old_audit_sha256':sha(SOURCE/'label_audit.json')})
    try:
        labels=[];changes=[];missing=[]
        for episode,old in episodes.items():
            folder,name=episode.split('/')
            rel=Path('runs')/folder/'episodes'/name
            path=ROOT/rel
            if not path.exists():
                source=restore_root/rel
                assert sha(source)==old['episode_sha256'],str(source)
                path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,path)
            assert sha(path)==old['episode_sha256']
            ep=json.loads(path.read_text());b=request_index_labels(ep,ep.get('label'))
            action=b['first_action_target_request'];read=b['first_token_read_request']
            cached=[r for r in base if r['episode']==episode]
            idxmap={r['request_idx']:r for r in cached}
            expected=[]
            for ordinal,(idx,rec) in enumerate(completed_target_requests(ep),1):
                if read is not None and ordinal>read and (action is None or ordinal<=action):expected.append(idx)
            selected=sorted([r for r in cached if not r['shared_branch_history'] and r['valid'] and r['ordinal'] is not None
                and read is not None and r['ordinal']>read and (action is None or r['ordinal']<=action)],key=lambda r:r['ordinal'])
            absent=sorted(set(expected)-{r['request_idx'] for r in selected})
            if absent:missing.append(dict(episode=episode,request_indices=absent))
            action_round=next((rec['round'] for ordinal,(_,rec) in enumerate(completed_target_requests(ep),1) if ordinal==action),None)
            for r in selected:
                assert r['first_read']==read
                labels.append(dict(**r,y_immediate=int(r['ordinal']==action),y_eventual=int(action is not None),
                    y_round_near=int(action is not None and 0<=action_round-r['round']<=1),
                    public_ordinal=action,public_round=action_round))
            changes.append(dict(episode=episode,scenario=old['scenario'],condition=old['condition'],
                old_first_public=old['first_public_ordinal'],new_first_public=action,
                changed=old['first_public_ordinal']!=action,first_read=read,calls=len(selected),
                immediate_positives=sum(r['ordinal']==action for r in selected),episode_sha256=sha(path)))
        labels.sort(key=lambda r:r['index'])
        # Feature access is read-only; the old checkout is only a local activation source.
        import numpy as np
        x=np.load(feature_path,mmap_mode='r')
        assert x.shape[0]==len(base) and x.shape[1:]==(64,5120),x.shape
        indices=np.array([r['index'] for r in labels])
        assert len(set(indices))==len(indices)
        finite=True
        for layer in list(range(0,64,4))+[63]:finite &= bool(np.isfinite(x[indices,layer]).all())
        assert finite and not missing,missing
        split_path=MAIN/'split_plan.json.gz'
        if not split_path.exists():shutil.copyfile(restore_root/split_path.relative_to(ROOT),split_path)
        oldplans=json.loads(gzip.decompress(split_path.read_bytes()))
        plans=[]
        for p in oldplans:
            if p['variant']!='eventual' or p['mode'] not in ['loso','pooled']:continue
            split={}
            for key,ids in p['split'].items():
                eps={base[i]['episode'] for i in ids}
                split[key]=[i for i,r in enumerate(labels) if r['episode'] in eps and r['condition']=='recruiting']
            train_f={labels[i]['family'] for i in split['train']};test_f={labels[i]['family'] for i in split['test']}
            train_s={labels[i]['scenario'] for i in split['train']}
            split['calibration']=[i for i,r in enumerate(labels) if r['condition']=='control' and r['family'] not in test_f
                and (p['mode']!='loso' or r['scenario'] in train_s) and (p['mode']=='loso' or r['family'] in train_f)]
            for a,b in [('train','test'),('inner_train','inner_validation'),('calibration','test')]:
                assert not {labels[i]['family'] for i in split[a]} & {labels[i]['family'] for i in split[b]}
            plans.append(dict(**{k:v for k,v in p.items() if k!='split'},split=split))
        assert len(plans)==33
        counts={}
        for cond in ['recruiting','control','alone']:
            rr=[r for r in labels if r['condition']==cond]
            counts[cond]=dict(calls=len(rr),episodes=len({r['episode'] for r in rr}),
                **{label:sum(r['y_'+label] for r in rr) for label in ['immediate','round_near','eventual']})
        result=dict(counts=counts,changed_episodes=[r for r in changes if r['changed']],missing_features=missing,
            feature_shape=list(x.shape),finite_candidates=finite,feature_path=str(feature_path),
            feature_source_metadata= json.loads((DATA/'meta.json').read_text()),
            labels='Same exact-value answer/tool-argument first-emission detector as GPT-OSS; includes failed tool calls; excludes private reasoning.',
            snapshots='after first required read through first exact emission inclusive; fixed old 241 recruiting + 97 benign episode IDs',
            frozen_confirmations_modified=False,gpu_spend_usd=0)
        for name,value in [('audit.json',result),('episode_audit.json',changes),('rows.json',labels),('split_plan.json',plans)]:write_json_atomic(run.dir/name,value)
        write_json_atomic(run.dir/'analysis_plan.json',dict(labels=['eventual','round_near','immediate'],
            candidate_layers=list(range(0,64,4))+[63],seeds=[42,43,44],primary_split='loso',secondary_split='pooled',
            C=.1,scaling='train_only',weights='round_balanced',inner_splits='unchanged saved family/scenario partitions',
            metric='within scenario x round AUROC',bootstrap=dict(unit='family',reps=1000,seed=20261025),
            source_hashes={name:sha(run.dir/name) for name in ['rows.json','split_plan.json']},
            feature_path=str(feature_path),phase='audit before any new outcome fit',status='exploratory'))
        run.result(**counts,gpu_spend_usd=0);run.finish();print(run.dir);print(json.dumps(result,indent=2))
    except BaseException as e:run.finish('failed',str(e));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--restore-root',type=Path,required=True);p.add_argument('--features',type=Path,required=True)
    a=p.parse_args();audit(a.restore_root,a.features)
