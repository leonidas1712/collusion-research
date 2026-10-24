"""Episode-held-out linear positive control for protected-token exposure."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from replay import start_run, digest


def auc(labels, scores):
    labels=np.asarray(labels,dtype=bool);scores=np.asarray(scores)
    if not labels.any() or labels.all():
        raise ValueError('AUROC requires both classes')
    order=np.argsort(scores,kind='stable');ranks=np.empty(len(scores),dtype=float)
    i=0
    while i<len(order):
        j=i+1
        while j<len(order) and scores[order[j]]==scores[order[i]]:j+=1
        ranks[order[i:j]]=(i+1+j)/2
        i=j
    n=labels.sum()
    return float((ranks[labels].sum()-n*(n+1)/2)/(n*(len(labels)-n)))


def episode_split(groups, seed=42, test_fraction=.3):
    names=sorted(set(groups))
    if len(names)<4:raise ValueError('Need at least four episodes')
    rng=np.random.default_rng(seed);rng.shuffle(names)
    test=set(names[:max(1,int(round(len(names)*test_fraction)))])
    return np.array([g in test for g in groups])


def fit_predict(x_train,y_train,x_test,seed=42):
    torch.manual_seed(seed)
    mean=x_train.mean(0);scale=x_train.std(0);scale[scale<1e-6]=1
    x=torch.tensor((x_train-mean)/scale,dtype=torch.float32)
    test=torch.tensor((x_test-mean)/scale,dtype=torch.float32)
    y=torch.tensor(y_train,dtype=torch.float32)
    if len(np.unique(y_train))!=2:raise ValueError('Training split needs both classes')
    weight=torch.zeros(x.shape[1],requires_grad=True);bias=torch.zeros((),requires_grad=True)
    opt=torch.optim.LBFGS([weight,bias],lr=1,max_iter=100,line_search_fn='strong_wolfe')
    pos_weight=torch.tensor(float((1-y).sum()/y.sum()))
    def closure():
        opt.zero_grad()
        loss=torch.nn.functional.binary_cross_entropy_with_logits(x@weight+bias,y,pos_weight=pos_weight)+.01*weight.square().sum()/2
        loss.backward();return loss
    opt.step(closure)
    with torch.no_grad():scores=(test@weight+bias).numpy()
    return scores,dict(weight=weight.detach().numpy(),bias=bias.detach().numpy(),mean=mean,scale=scale)


def main(args):
    torch.set_num_threads(4)
    source=Path(args.run)
    run=start_run('e02-exposure-positive-control',experiment='E02',parents=[source.name],settings=vars(args))
    try:
        rows=[json.loads(line) for line in (source/'index.jsonl').read_text().splitlines()]
        groups=[];labels=[];vectors=[];seen=set();layer=None
        for row in rows:
            if not isinstance(row.get('token_in_context'),bool):
                raise ValueError('Missing request-specific token_in_context; use a verified manifest replay')
            key=(row['run_id'],Path(row['episode_file']).name,row['request_idx'])
            if key in seen:raise ValueError('Duplicate replay request')
            seen.add(key)
            artifact=source/row['artifact']
            if not artifact.resolve().is_relative_to(source.resolve()):raise ValueError('Artifact escapes run')
            with np.load(artifact) as data:
                ids=data['input_ids'].tolist()
                if digest(ids)!=row['input_ids_sha256'] or len(ids)!=row['n_tokens']:
                    raise ValueError('Activation input IDs do not match index')
                if digest((source/row['prompt_file']).read_bytes())!=row['prompt_sha256']:
                    raise ValueError('Prompt file does not match index')
                indices=list(data['layer_indices']);chosen=indices[-1] if args.layer=='last' else int(args.layer)
                if layer is not None and chosen!=layer:raise ValueError('Inconsistent layer')
                layer=chosen;vectors.append(data['residual_last'][indices.index(chosen)])
            groups.append(row['run_id']+'/'+Path(row['episode_file']).name);labels.append(row['token_in_context'])
        x=np.stack(vectors);y=np.asarray(labels,dtype=int)
        if not np.isfinite(x).all():raise ValueError('Nonfinite vectors')
        held=episode_split(groups,args.seed)
        if len(np.unique(y[held]))!=2:raise ValueError('Held-out split needs both classes; do not tune split on AUROC')
        scores,model=fit_predict(x[~held],y[~held],x[held],args.seed)
        value=auc(y[held],scores)
        summary=dict(heldout_auroc=value,near_perfect_target_met=value>=.98,threshold=.98,layer=int(layer),
            train_episodes=len(set(np.asarray(groups)[~held])),test_episodes=len(set(np.asarray(groups)[held])),
            train_rows=int((~held).sum()),test_rows=int(held.sum()),train_positive=int(y[~held].sum()),
            test_positive=int(y[held].sum()),seed=args.seed,
            interpretation='Positive-control diagnostic only; low AUROC triggers investigation, not a unique diagnosis of extraction failure.')
        np.savez_compressed(run.dir/'linear_probe.npz',**model)
        (run.dir/'split.json').write_text(json.dumps({'train':sorted(set(np.asarray(groups)[~held])),'test':sorted(set(np.asarray(groups)[held]))},indent=2))
        (run.dir/'predictions.jsonl').write_text(''.join(json.dumps({'episode':g,'label':int(label),'score':float(score)})+'\n' for g,label,score in zip(np.asarray(groups)[held],y[held],scores)))
        (run.dir/'summary.json').write_text(json.dumps(summary,indent=2));run.result(**summary);run.finish();print(json.dumps(summary,indent=2));print(run.id)
    except BaseException as exc:
        run.finish('failed',str(exc));raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');p.add_argument('--layer',default='last');p.add_argument('--seed',type=int,default=42)
    main(p.parse_args())
