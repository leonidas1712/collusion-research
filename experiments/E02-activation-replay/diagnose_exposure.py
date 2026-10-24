"""Read-only diagnostics after the fixed last-layer exposure control missed its target."""
import json
from pathlib import Path
import numpy as np
from replay import ROOT, start_run
from plan_main import token_value
from exposure_probe import auc

main=ROOT/'runs/20261024-1018-e02-activation-replay'
old=ROOT/'runs/20261024-0751-e02-activation-replay'
probe=ROOT/'runs/20261024-1918-e02-exposure-positive-control'
run=start_run('e02-exposure-diagnostics',experiment='E02',parents=[main.name,old.name,probe.name],settings={'read_only':True,'no_refit':True})
rows=[json.loads(x) for x in (main/'index.jsonl').read_text().splitlines()]
previous={r['input_ids_sha256']:r for r in map(json.loads,(old/'index.jsonl').read_text().splitlines())}
with np.load(probe/'linear_probe.npz') as fit:
    weight=fit['weight'];bias=fit['bias'];mean=fit['mean'];scale=fit['scale']
split=json.loads((probe/'split.json').read_text());test=set(split['test'])
cache={};audit=[];overlap=[]
for row in rows:
    source=row['manifest']['episode_file']
    if source not in cache:cache[source]=token_value(json.loads((ROOT/source).read_text()))
    observed=cache[source] in (main/row['prompt_file']).read_text()
    assert observed==row['token_in_context']
    group=row['run_id']+'/'+Path(row['episode_file']).name
    with np.load(main/row['artifact']) as data:
        vector=data['residual_last'][-1]
        score=float(((vector-mean)/scale)@weight+bias)
        if row['input_ids_sha256'] in previous:
            prior=previous[row['input_ids_sha256']]
            with np.load(old/prior['artifact']) as earlier:
                assert np.array_equal(data['input_ids'],earlier['input_ids'])
                a=data['residual_last'].astype('float64');b=earlier['residual_last'].astype('float64')
                cosine=(a*b).sum(1)/(np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1))
                rel=np.linalg.norm(a-b,axis=1)/np.linalg.norm(b,axis=1)
                overlap.append(dict(episode=group,request_idx=row['request_idx'],old_artifact=prior['artifact'],new_artifact=row['artifact'],
                    min_layer_cosine=float(cosine.min()),last_layer_cosine=float(cosine[-1]),max_layer_relative_l2=float(rel.max()),
                    last_layer_relative_l2=float(rel[-1]),max_abs=float(np.abs(a-b).max())))
    audit.append(dict(episode=group,held_out=group in test,label=int(observed),score=score,condition=row['manifest']['condition'],
                      valid_for_comparison=row['valid_for_comparison'],request_idx=row['request_idx']))
result={'label_audit_rows':len(audit),'label_mismatches':0,'prompt_only_benchmark_overlap':len(overlap),
    'minimum_layer_cosine_vs_prompt_only':min(r['min_layer_cosine'] for r in overlap),
    'minimum_last_layer_cosine_vs_prompt_only':min(r['last_layer_cosine'] for r in overlap),
    'maximum_relative_l2_vs_prompt_only':max(r['max_layer_relative_l2'] for r in overlap),
    'maximum_last_layer_relative_l2_vs_prompt_only':max(r['last_layer_relative_l2'] for r in overlap)}
for held,name in ((False,'train'),(True,'test')):
    rs=[r for r in audit if r['held_out']==held]
    result[name+'_auc']=auc([r['label'] for r in rs],[r['score'] for r in rs])
    for condition in sorted({r['condition'] for r in rs}):
        subset=[r for r in rs if r['condition']==condition]
        if len({r['label'] for r in subset})==2:
            result[name+'_'+condition+'_auc']=auc([r['label'] for r in subset],[r['score'] for r in subset])
(run.dir/'summary.json').write_text(json.dumps(result,indent=2))
(run.dir/'prompt_only_comparison.json').write_text(json.dumps(overlap,indent=2))
(run.dir/'scores.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in audit))
print(json.dumps(result,indent=2));run.result(**result);run.finish();print(run.id)
