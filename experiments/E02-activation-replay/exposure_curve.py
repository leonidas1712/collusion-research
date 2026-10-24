"""Post-hoc exposure diagnostics at owner-specified layers; no model replay."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
import torch
from replay import ROOT, start_run
from exposure_probe import episode_split, fit_predict, auc
from plan_main import token_value

source=ROOT/'runs/20261024-1018-e02-activation-replay'
prior=ROOT/'runs/20261024-1918-e02-exposure-positive-control'
layers=[16,26,32,40,48]
run=start_run('e02-exposure-layer-curve',experiment='E02',parents=[source.name,prior.name],settings={'layers':layers,'seed':42,'post_hoc_diagnostic':True,'request':'Aboard #497','no_gpu':True})
torch.set_num_threads(4)
rows=[json.loads(s) for s in (source/'index.jsonl').read_text().splitlines()]
x=np.empty((len(rows),len(layers),5120),dtype=np.float32);groups=[];labels=[];cache={};audit=[]
for i,row in enumerate(rows):
    with np.load(source/row['artifact']) as data:
        indices=list(data['layer_indices']);x[i]=data['residual_last'][[indices.index(k) for k in layers]]
    groups.append(row['run_id']+'/'+Path(row['episode_file']).name);labels.append(row['token_in_context'])
    path=row['manifest']['episode_file']
    if path not in cache:cache[path]=json.loads((ROOT/path).read_text())
    ep=cache[path];token=token_value(ep);messages=ep['requests'][row['request_idx']]['request']['messages']
    flags={role:any(m.get('role')==role and token in json.dumps(m,ensure_ascii=False) for m in messages)
           for role in ('system','user','assistant','tool')}
    assert (token in (source/row['prompt_file']).read_text())==row['token_in_context']
    category='absent'
    if row['token_in_context']:
        if flags['tool'] and flags['assistant']:category='tool_and_assistant'
        elif flags['tool']:category='tool_no_assistant'
        elif flags['assistant'] and not flags['user'] and not flags['system']:category='assistant_only'
        else:category='other'
    audit.append(dict(episode=groups[-1],request_idx=row['request_idx'],token_in_context=row['token_in_context'],category=category,raw_message_role_contains_token=flags))
y=np.asarray(labels,dtype=int);held=episode_split(groups,42)
oldsplit=json.loads((prior/'split.json').read_text());assert set(np.asarray(groups)[held])==set(oldsplit['test'])
curve=[]
for j,layer in enumerate(layers):
    scores,model=fit_predict(x[~held,j],y[~held],x[held,j],42)
    train=((x[~held,j]-model['mean'])/model['scale'])@model['weight']+model['bias']
    item=dict(layer=layer,heldout_auroc=auc(y[held],scores),train_auroc=auc(y[~held],train),test_rows=int(held.sum()),test_episodes=len(oldsplit['test']))
    curve.append(item);print(json.dumps(item),flush=True)
    np.savez_compressed(run.dir/f'probe-layer-{layer}.npz',**model)
    np.savez_compressed(run.dir/f'heldout-scores-layer-{layer}.npz',scores=scores,labels=y[held])
    item['by_exposure_category']={}
    negatives=~y[held].astype(bool)
    cats=np.asarray([r['category'] for r in audit])[held]
    for category in sorted(set(cats)-{'absent'}):
        mask=negatives | (cats==category)
        if len(np.unique(y[held][mask]))==2:item['by_exposure_category'][category]=auc(y[held][mask],scores[mask])
last=json.loads((prior/'summary.json').read_text());curve.append(dict(layer=63,heldout_auroc=last['heldout_auroc'],train_auroc=1.0,test_rows=last['test_rows'],test_episodes=last['test_episodes'],source=prior.name))
counts=Counter(r['category'] for r in audit);testcounts=Counter(r['category'] for r,h in zip(audit,held) if h)
result=dict(curve=curve,exposure_counts=dict(counts),heldout_exposure_counts=dict(testcounts),label_mismatches=0,
    interpretation='Post-hoc diagnostic curve on the same held-out episodes; not an independent confirmation after layer selection. No best layer chosen for a scientific outcome.')
(run.dir/'summary.json').write_text(json.dumps(result,indent=2));(run.dir/'exposure-audit.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in audit))
(run.dir/'curve.csv').write_text('layer,heldout_auroc,train_auroc\n'+''.join(f"{r['layer']},{r['heldout_auroc']},{r['train_auroc']}\n" for r in curve))
run.result(exposure_counts=dict(counts),curve=curve);run.finish();print(json.dumps(result,indent=2));print(run.id)
