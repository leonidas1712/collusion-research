"""Prepare saved Harmony reasoning residuals for the exploratory streaming study."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'experiments/E02-activation-replay')]
from collusion.runs import start_run, write_json_atomic
from gpt_oss_replay import harmony_encoding, digest

DATA = ROOT/'runs/20261025-2305-e05-gpt-oss-full-data'
PLAN = ROOT/'runs/20261025-2251-e02-gpt-oss-full-plan'
FITS = ROOT/'runs/20261026-0138-e05-gpt-oss-main'


def first_mention_cutoff(enc, ids, values):
    text = enc.decode(ids)
    starts = [text.find(v) for v in values if v in text]
    if not starts:
        return len(ids), False
    start = min(starts)
    # Drop the token containing the FIRST character, not merely the token that
    # completes the value: activations are saved after consuming each token.
    for j in range(len(ids)):
        if len(enc.decode(ids[:j+1])) > start:
            return j, True
    raise AssertionError('Mention is not covered by decoded token prefixes')


def prepare():
    rows = [json.loads(s) for s in (DATA/'rows.jsonl').read_text().splitlines()]
    episodes = {r['episode']: r for r in json.loads((PLAN/'episodes.json').read_text())}
    cohort = {r['episode'] for r in rows if r['eligible'] and r['condition']=='recruiting'}
    assert len(cohort)==238
    frozen = [r for r in rows if r['eligible'] and r['condition']=='recruiting']
    assert len(frozen)==2059
    appended = {r['index'] for r in rows if r['episode'] in cohort and r['post_ask']
                and r['first_action'] is not None and r['ordinal']==r['first_action']
                and r['ordinal']>r['first_read']}
    assert len(appended)==146
    selected = [r for r in rows if
                (r['episode'] in cohort and (r['eligible'] or r['eligible_pre_ask'] or r['index'] in appended))
                or (r['condition']=='control' and (r['eligible'] or r['eligible_pre_ask']))]
    run = start_run('e05-reasoning-stream-data', experiment='E05',
        parents=[DATA.name, PLAN.name, FITS.name], tags=['exploratory','cpu-only'],
        settings={'cohort_episodes':238,'frozen_replies':2059,'appended_replies':146,
                  'after_consuming_token':True,'primary':'any first public emission',
                  'no_new_inference':True})
    try:
        expected = {}
        for shard in sorted((PLAN/'shards').glob('*.json')):
            for r in json.loads(shard.read_text())['rows']:
                expected[r['row_id']] = r
        enc = harmony_encoding()
        source_eps = {}
        metadata = []
        offset = 0
        for row in selected:
            r = expected[row['row_id']]
            if row['episode'] not in source_eps:
                source_eps[row['episode']] = json.loads(Path(row['source_path']).read_text())
            ep = source_eps[row['episode']]
            record = ep['requests'][row['request_idx']]
            assert digest(record['request'])==row['harmony_request_sha256']
            values = ep['scenario_spec']['honeypots']
            assert values and all(isinstance(v,str) and v for v in values)
            ids = r['prompt_ids']+r['reply_ids']
            rp = r['reasoning_positions']
            ap = r['answer_positions']
            # Reasoning must precede every answer/tool-body token. The Harmony
            # header itself is also before the body and is excluded below.
            public_start = min(ap) if ap else len(ids)
            end_header = enc.encode('<|start|>', allowed_special='all')[0]
            headers = [i for i in range(len(r['prompt_ids']),public_start) if ids[i]==end_header]
            last_reason = max(rp) if rp else -1
            later_headers = [i for i in headers if i>last_reason]
            first_public_header = min(later_headers) if later_headers else public_start
            keep = [j for j,p in enumerate(rp) if p<first_public_header]
            assert len(keep)==len(rp), ('Reasoning after public output',row['row_id'])
            reason_ids = [ids[p] for p in rp]
            cutoff, mentions = first_mention_cutoff(enc,reason_ids,values)
            raw_reason = ((record.get('response') or {}).get('choices') or [{}])[0].get('message',{}).get('reasoning') or ''
            assert enc.decode(reason_ids)==raw_reason, ('Reasoning token/text mismatch',row['row_id'])
            e = episodes[row['episode']]
            immediate = row['index'] in appended
            channel = immediate and row['request_idx']==e['first_channel_request_idx']
            near = e['first_public_emission_ordinal'] is not None and 0<=e['action_round']-row['round']<=1
            info = {**row,'stream_index':len(metadata),'start':offset,'stop':offset+len(rp),
                    'reasoning_tokens':len(rp),'clean_tokens':cutoff,'mentions_value':mentions,
                    'appended':immediate,'frozen':bool(row['eligible']),
                    'stream_window':'post_ask' if row['post_ask'] else 'pre_ask',
                    'y_immediate':int(immediate),'y_channel':int(channel),'y_near':int(near),
                    'ever_public':int(e['first_public_emission_ordinal'] is not None),
                    'first_channel_request_idx':e['first_channel_request_idx'],
                    'first_public_header_position':first_public_header,
                    'reasoning_positions':rp,'raw_reasoning_characters':len(raw_reason)}
            metadata.append(info)
            offset += len(rp)
        write_json_atomic(run.dir/'replies.json',metadata)
        feature = np.lib.format.open_memmap(run.dir/'reasoning.npy',mode='w+',dtype='float32',shape=(24,offset,2880))
        for j,r in enumerate(metadata):
            p = ROOT/'runs'/r['source_replay']/r['source_artifact']
            wanted = expected[r['row_id']]
            with np.load(p,allow_pickle=False) as a:
                assert a['layer_indices'].tolist()==list(range(24))
                assert a['input_ids'].tolist()==wanted['prompt_ids']+wanted['reply_ids']
                assert a['reasoning_positions'].tolist()==r['reasoning_positions']
                x=a['residual_reasoning']
                assert x.shape==(24,r['reasoning_tokens'],2880) and np.isfinite(x).all()
                feature[:,r['start']:r['stop']]=x
            if j%200==0:
                feature.flush()
                print('VERIFIED',j,len(metadata),flush=True)
        feature.flush()
        groups={}
        for window in ['post_ask','pre_ask']:
            group=[r for r in metadata if r['condition']=='recruiting' and r['stream_window']==window]
            groups[window]={'replies':len(group),'episodes':len({r['episode'] for r in group}),
                'reasoning_tokens':sum(r['reasoning_tokens'] for r in group),
                'empty_reasoning':sum(not r['reasoning_tokens'] for r in group),
                'immediate_positive':sum(r['y_immediate'] for r in group),
                'channel_positive':sum(r['y_channel'] for r in group),
                'near_positive':sum(r['y_near'] for r in group),
                'positive_with_reasoning':sum(r['y_immediate'] and r['reasoning_tokens']>0 for r in group),
                'leaking_reply_mentions_value':sum(r['y_immediate'] and r['mentions_value'] for r in group),
                'clean_tokens':sum(r['clean_tokens'] for r in group)}
        summary={'groups':groups,'shape':list(feature.shape),'all_selected_replies':len(metadata),
                 'source_sha256':hashlib.sha256((DATA/'rows.jsonl').read_bytes()).hexdigest(),
                 'first_emission_appended':len(appended),'frozen_reasoning_positive':0,
                 'all_artifacts_verified':True,'no_fits':True}
        write_json_atomic(run.dir/'summary.json',summary)
        run.result(**summary);run.finish();print('STREAM_DATA',run.dir,flush=True)
    except BaseException as e:
        run.finish('failed',str(e));raise


if __name__=='__main__':
    prepare()
