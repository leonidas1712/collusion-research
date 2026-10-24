"""Frozen joins from the verified E02 replay; no new episode scoring."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
REPLAY='20261024-1018-e02-activation-replay'
POSITION='20261024-step-position-judge'
LAYERS=sorted(set(range(0,64,4)) | {26,27,28,29,30,63})
CANDIDATES=list(range(0,64,4))+[63]

def read_data(output):
    source=ROOT/'runs'/REPLAY
    original=[json.loads(s) for s in (source/'index.jsonl').read_text().splitlines()]
    positions={r['step_id']:r for r in map(json.loads,(ROOT/'runs'/POSITION/'step_labels.jsonl').read_text().splitlines())}
    rows=[];ordinal=Counter();last={}
    features=np.lib.format.open_memmap(output/'features.npy',mode='w+',dtype='float32',shape=(len(original),len(LAYERS),5120))
    for i,r in enumerate(original):
        m=r['manifest'];ep=m['episode_key'];step_id=ep+'::request_idx='+str(r['request_idx']);p=positions[step_id]
        assert p['request_sha256']==r['request_sha256'] and r['manifest_verified']
        semantic=(r['label'].get('semantic_judge') or {}).get('labels',{})
        kind=semantic.get('first_publication_kind')
        boundary=bool(m['label_will_violate'])
        y=1 if kind in ('deliberate','accidental') else (-1 if boundary else 0)
        assert y!=1 or boundary
        row=dict(index=i,episode=ep,family=str(m['family_id']),condition=m['condition'],tactic=m['tactic_id'],
            round=r['round'],request_idx=r['request_idx'],step_in_turn=r['step_in_turn'],ordinal=ordinal[ep],
            n_tokens=r['n_tokens'],kind=kind,label=y,boundary_label=int(boundary),
            token_in_context=r['token_in_context'],valid=r['valid_for_comparison'],acts_this_step=r['acts_this_step'],
            before_first_action=r['before_first_action'],decision_visible=p['share_signal_so_far'],
            stated_position=p['stated_position'],position_provisional=p['provisional'],
            first_action_round=m['first_boundary_violation_round'],request_sha256=r['request_sha256'])
        rows.append(row);ordinal[ep]+=1
        if r['acts_this_step']:last[ep]=row['ordinal']
        with np.load(source/r['artifact']) as a:
            assert list(a['layer_indices'])==list(range(64))
            features[i]=a['residual_last'][LAYERS]
    features.flush()
    for r in rows:r['steps_until_action']=last[r['episode']]-r['ordinal'] if r['episode'] in last else None
    (output/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (output/'layers.json').write_text(json.dumps(LAYERS))
    counts=Counter((r['condition'],r['label']) for r in rows if r['valid'] and r['token_in_context'])
    summary=dict(rows=len(rows),episodes=len(ordinal),families=len({r['family'] for r in rows}),
                 eligible_rows_by_condition_label={str(k):v for k,v in counts.items()},
                 excluded_unknown_outcome_episodes=sorted({r['episode'] for r in rows if r['label']==-1}),
                 position_sha256=hashlib.sha256((ROOT/'runs'/POSITION/'step_labels.jsonl').read_bytes()).hexdigest())
    (output/'data-summary.json').write_text(json.dumps(summary,indent=2))
    return rows,features
