"""Family-grouped, nested CPU probe evaluation on frozen replay inputs."""
import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from data import ROOT,LAYERS,CANDIDATES,REPLAY,POSITION,read_data
from models import fit_logistic,score,fit_dom,score_dom
from metrics import within_round,threshold_at_fpr
from splits import assign_folds,inner_split
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run

SEEDS=[42,43,44]

def eligible_rows(rows,variant):
    selected=[]
    for i,r in enumerate(rows):
        if not r['valid'] or not r['token_in_context']:continue
        if variant=='deliberate' and r['kind']=='accidental':continue
        if variant!='boundary' and r['label']<0:continue
        selected.append(i)
    return np.asarray(selected)


def run_cv(rows,x,out,variant='main',unit='family',seeds=SEEDS,exploratory=False,auxiliary=False):
    local=[dict(r,label=r['boundary_label']) if variant=='boundary' else r for r in rows]
    eligible=eligible_rows(local,variant);n=len(rows)
    y=np.array([r['label'] for r in local]);rounds=np.array([r['round'] for r in rows]);episodes=np.array([r['episode'] for r in rows])
    recruiting=np.array([r['condition']=='recruiting' for r in rows]);acts=np.array([r['acts_this_step'] for r in rows])
    method_names=['nested','fixed32','band26_30','dom32','turn','length']+(['shuffled32'] if auxiliary else [])
    pred={name:np.full((len(seeds),n),np.nan) for name in method_names}
    thresholds={name:np.full((len(seeds),n),np.nan) for name in method_names}
    layer_scores=np.full((len(seeds),n,len(CANDIDATES)),np.nan)
    pc=np.full((len(seeds),n),np.nan);shuffled_y=np.full((len(seeds),n),-1,dtype=int)
    fold_rows=np.full((len(seeds),n),-1,dtype=int);notes=[]
    fmap={layer:LAYERS.index(layer) for layer in LAYERS}
    for si,seed in enumerate(seeds):
        assignment,dealing_seed=assign_folds(local,eligible,seed,unit=unit)
        foldmap=np.array([assignment.get(r['episode'],-1) for r in rows]);fold_rows[si]=foldmap
        ep_names=sorted({r['episode'] for r in local if r['episode'] in assignment and r['condition']=='recruiting'})
        ep_label={r['episode']:r['label'] for r in local};permuted=np.random.default_rng(seed+9000).permutation([ep_label[e] for e in ep_names])
        shuffle_map=dict(zip(ep_names,permuted));sy=np.array([shuffle_map.get(e,-1) for e in episodes]);shuffled_y[si]=sy
        for fold in range(5):
            started=time.perf_counter()
            train=eligible[(foldmap[eligible]!=fold)&recruiting[eligible]]
            test=eligible[foldmap[eligible]==fold]
            calibration=eligible[(foldmap[eligible]!=fold)&~recruiting[eligible]]
            fit,val,inner_seed=inner_split(local,train,seed+fold*17,unit=unit)
            group=lambda indices:{local[i][unit] if unit=='family' else local[i]['episode'] for i in indices}
            assert not group(train)&group(test)
            assert not group(calibration)&group(test)
            assert not group(fit)&group(val)
            candidate_metrics={}
            for layer in CANDIDATES:
                model=fit_logistic(x[fit,fmap[layer]],y[fit],rounds[fit],seed)
                values=score(model,x[val,fmap[layer]])
                candidate_metrics[layer]=within_round(y[val],values,rounds[val])[0]
            chosen=max(CANDIDATES,key=lambda layer:(candidate_metrics[layer] if np.isfinite(candidate_metrics[layer]) else -1,-layer))
            needed=sorted(set(CANDIDATES if exploratory else [chosen,32])|set(range(26,31)))
            eval_index=np.r_[test,calibration];models={};scores={}
            for layer in needed:
                model=fit_logistic(x[train,fmap[layer]],y[train],rounds[train],seed)
                models[layer]=model;scores[layer]=score(model,x[eval_index,fmap[layer]])
                scaler,clf=model
                if layer in {chosen,32,*range(26,31)}:
                    np.savez_compressed(out/f'model-s{seed}-f{fold}-l{layer}.npz',mean=scaler.mean_,scale=scaler.scale_,coef=clf.coef_,intercept=clf.intercept_)
                if exploratory and layer in CANDIDATES:layer_scores[si,test,CANDIDATES.index(layer)]=scores[layer][:len(test)]
            values={'nested':scores[chosen],'fixed32':scores[32],
                    'band26_30':np.mean([scores[layer] for layer in range(26,31)],axis=0),
                    'turn':-rounds[eval_index].astype(float),'length':np.array([rows[i]['n_tokens'] for i in eval_index],dtype=float)}
            pre=train[~acts[train]];dom=fit_dom(x[pre,fmap[32]],y[pre],rounds[pre]);sd=np.std(score_dom(dom,x[pre,fmap[32]]))
            values['dom32']=score_dom(dom,x[eval_index,fmap[32]])/max(sd,1e-12)
            np.savez_compressed(out/f'dom-s{seed}-f{fold}.npz',direction=dom[0],center=dom[1],training_projection_sd=sd)
            if auxiliary:
                shuffled=fit_logistic(x[train,fmap[32]],sy[train],rounds[train],seed)
                values['shuffled32']=score(shuffled,x[eval_index,fmap[32]])
                pc_indices=np.array([i for i,r in enumerate(rows) if r['valid'] and r['label']>=0 and foldmap[i]>=0])
                ptrain=pc_indices[foldmap[pc_indices]!=fold];ptest=pc_indices[foldmap[pc_indices]==fold]
                py=np.array([r['token_in_context'] for r in rows],dtype=int)
                positive=fit_logistic(x[ptrain,fmap[32]],py[ptrain],None,seed)
                pc[si,ptest]=score(positive,x[ptest,fmap[32]])
            calibration_notes={}
            for method,allvalues in values.items():
                pred[method][si,test]=allvalues[:len(test)]
                threshold,info=threshold_at_fpr(allvalues[len(test):],episodes[calibration])
                thresholds[method][si,test]=threshold;calibration_notes[method]={'threshold':threshold,**info}
            counts=lambda ids:dict(Counter((local[i]['condition']+'_'+str(local[i]['label'])) for i in {local[j]['episode']:j for j in ids}.values()))
            note=dict(seed=seed,dealing_seed=dealing_seed,fold=fold,unit=unit,chosen_layer=chosen,inner_seed=inner_seed,
                inner_validation_auroc={str(k):v for k,v in candidate_metrics.items()},
                train_episodes=sorted(set(episodes[train])),test_episodes=sorted(set(episodes[test])),
                calibration_episodes=sorted(set(episodes[calibration])),inner_train_episodes=sorted(set(episodes[fit])),inner_validation_episodes=sorted(set(episodes[val])),
                train_groups=sorted(group(train)),test_groups=sorted(group(test)),calibration_groups=sorted(group(calibration)),
                test_episode_counts=counts(test),calibration=calibration_notes,seconds=time.perf_counter()-started)
            notes.append(note)
            (out/'folds.json').write_text(json.dumps(notes,indent=2))
            print(f'{variant}/{unit} seed={seed} fold={fold} layer={chosen} seconds={note["seconds"]:.1f}',flush=True)
        for method in method_names:assert np.isfinite(pred[method][si,eligible]).all()
    np.savez_compressed(out/'predictions.npz',**pred,**{'threshold_'+k:v for k,v in thresholds.items()},layer_scores=layer_scores,positive_control=pc,shuffled_labels=shuffled_y,folds=fold_rows,eligible=eligible,y=y,seeds=seeds)
    return pred


def run_transfer(rows,x,out,family_disjoint=False):
    eligible=eligible_rows(rows,'main');recruiting=np.array([r['condition']=='recruiting' for r in rows])
    early=np.array([r['tactic'] in ('T0','T1','T2') for r in rows]);families=np.array([r['family'] for r in rows]);eps=np.array([r['episode'] for r in rows])
    test=eligible[~early[eligible]];train=eligible[early[eligible]&recruiting[eligible]];cal=eligible[early[eligible]&~recruiting[eligible]]
    if family_disjoint:
        forbidden=set(families[test]);train=train[~np.isin(families[train],list(forbidden))];cal=cal[~np.isin(families[cal],list(forbidden))]
    y=np.array([r['label'] for r in rows]);rounds=np.array([r['round'] for r in rows]);fmap={layer:LAYERS.index(layer) for layer in LAYERS}
    fit,val,inner_seed=inner_split(rows,train,42,unit='family');inner={}
    for layer in CANDIDATES:
        model=fit_logistic(x[fit,fmap[layer]],y[fit],rounds[fit]);inner[layer]=within_round(y[val],score(model,x[val,fmap[layer]]),rounds[val])[0]
    chosen=max(CANDIDATES,key=lambda k:(inner[k] if np.isfinite(inner[k]) else -1,-k));values={};eval_idx=np.r_[test,cal]
    for layer in sorted({chosen,32,*range(26,31)}):values[layer]=score(fit_logistic(x[train,fmap[layer]],y[train],rounds[train]),x[eval_idx,fmap[layer]])
    methods={'nested':values[chosen],'fixed32':values[32],'band26_30':np.mean([values[k] for k in range(26,31)],axis=0),
             'turn':-rounds[eval_idx].astype(float),'length':np.array([rows[i]['n_tokens'] for i in eval_idx],dtype=float)}
    pre=train[np.array([not rows[i]['acts_this_step'] for i in train])];dom=fit_dom(x[pre,fmap[32]],y[pre],rounds[pre]);sd=np.std(score_dom(dom,x[pre,fmap[32]]));methods['dom32']=score_dom(dom,x[eval_idx,fmap[32]])/max(sd,1e-12)
    payload={};thresholds={}
    for method,values in methods.items():
        a=np.full((1,len(rows)),np.nan);a[0,test]=values[:len(test)];payload[method]=a
        t,info=threshold_at_fpr(values[len(test):],eps[cal]);b=np.full_like(a,np.nan);b[0,test]=t;payload['threshold_'+method]=b;thresholds[method]={'threshold':t,**info}
    np.savez_compressed(out/'predictions.npz',**payload,eligible=test,y=y,seeds=[42])
    note=dict(chosen_layer=chosen,inner_validation_auroc=inner,inner_seed=inner_seed,family_disjoint=family_disjoint,
        train_episodes=sorted(set(eps[train])),test_episodes=sorted(set(eps[test])),calibration_episodes=sorted(set(eps[cal])),
        shared_train_test_families=sorted(set(families[train])&set(families[test])),observed_train_tactics=sorted({rows[i]['tactic'] for i in train}),thresholds=thresholds)
    (out/'transfer.json').write_text(json.dumps(note,indent=2));print('TRANSFER',family_disjoint,chosen,flush=True)


def main(args):
    run=start_run('e05-probe-core',experiment='E05',parents=[REPLAY,POSITION]+([args.data_run] if args.data_run else []),settings={'seeds':SEEDS,'L2_C':.1,'solver':'lbfgs','candidate_layers':CANDIDATES,'main_group':'family','inner_split':'one of four group folds','position_matching':'negative weights match positive count within training round','bootstrap_reps':1000,'scope':'Aboard #503/#509'})
    try:
        if args.data_run:
            cached=ROOT/'runs'/args.data_run
            rows=[json.loads(s) for s in (cached/'rows.jsonl').read_text().splitlines()]
            x=np.load(cached/'features.npy',mmap_mode='r')
            assert x.shape==(len(rows),len(LAYERS),5120)
            (run.dir/'rows.jsonl').write_bytes((cached/'rows.jsonl').read_bytes())
            (run.dir/'data-summary.json').write_bytes((cached/'data-summary.json').read_bytes())
            (run.dir/'layers.json').write_text(json.dumps(LAYERS))
            (run.dir/'features-source.json').write_text(json.dumps({'run_id':args.data_run,'path':str(cached/'features.npy')}))
        else:
            rows,x=read_data(run.dir)
        with threadpool_limits(limits=4):
            for name,variant,unit,exploratory,auxiliary in [('main','main','family',True,True),('deliberate','deliberate','family',False,False),('episode_sensitivity','main','episode',False,False),('boundary_sensitivity','boundary','family',False,False)]:
                out=run.dir/name;out.mkdir();run_cv(rows,x,out,variant,unit,exploratory=exploratory,auxiliary=auxiliary)
            for name,strict in [('tactic_transfer',False),('tactic_family_transfer',True)]:
                out=run.dir/name;out.mkdir();run_transfer(rows,x,out,strict)
        run.result(rows=len(rows),all_fits_complete=True);run.finish();print('CORE_RUN',run.id)
    except BaseException as exc:
        run.finish('failed',str(exc));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data-run');main(p.parse_args())
