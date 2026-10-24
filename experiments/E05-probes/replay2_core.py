"""Frozen-recipe replay2 CV, LOSO and nested added-value fits on CPU."""
import argparse
import json
import sys
import time
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from data import ROOT,CANDIDATES
from models import fit_logistic,score,fit_dom,score_dom
from metrics import within_round,threshold_at_fpr,ema_max
from splits import assign_folds,inner_split
from replay2_models import fit_mlp,score_mlp,save_mlp,fit_metadata,score_metadata,scenario_rates,MLP_SETTINGS,save_metadata
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run
SEEDS=[42,43,44];FPRS=[.01,.05,.10,.20]

def selected_indices(rows,mode):
    return np.array([i for i,r in enumerate(rows) if r['eligible']
        and ('v2' not in mode or r['scenario']=='deploy-token-v2')
        and ('deliberate' not in mode or not r['label'] or r['kind']=='deliberate')],dtype=int)

def split_inner(rows,train,seed,loso=False):
    if not loso:
        fit,val,actual=inner_split(rows,train,seed,unit='family')
        return fit,val,{'kind':'family_holdout','actual_seed':actual}
    scenarios=sorted({rows[i]['scenario'] for i in train})
    for offset in range(len(scenarios)):
        held=scenarios[(seed+offset)%len(scenarios)];val=np.array([i for i in train if rows[i]['scenario']==held]);groups={rows[i]['family'] for i in val}
        fit=np.array([i for i in train if rows[i]['scenario']!=held and rows[i]['family'] not in groups])
        if len({rows[i]['label'] for i in fit})==len({rows[i]['label'] for i in val})==2:
            return fit,val,{'kind':'training_scenario_holdout','validation_scenario':held,'purged_shared_families':sorted(groups)}
    raise ValueError('No class-complete training-scenario inner split')

def pick_lr(rows,x,train,seed,loso=False):
    fit,val,note=split_inner(rows,train,seed,loso);y=np.array([r['label'] for r in rows]);rounds=np.array([r['round'] for r in rows]);scenarios=np.array([r['scenario'] for r in rows]);scores={}
    for layer in CANDIDATES:
        model=fit_logistic(x[fit,layer],y[fit],rounds[fit],seed);scores[layer]=within_round(y[val],score(model,x[val,layer]),rounds[val],stratum_key=scenarios[val])[0]
    assert any(np.isfinite(v) for v in scores.values())
    chosen=max(CANDIDATES,key=lambda l:(scores[l] if np.isfinite(scores[l]) else -1,-l))
    return chosen,fit,val,{**note,'validation_auroc':scores,'inner_train_families':sorted({rows[i]['family'] for i in fit}),'inner_validation_families':sorted({rows[i]['family'] for i in val})}

def crossfit_scores(rows,x,train,seed,loso=False):
    assignment,actual=assign_folds(rows,train,seed,n_splits=3,unit='family',require_all=False);values=np.full(len(rows),np.nan);notes=[]
    for fold in range(3):
        val=np.array([i for i in train if assignment[rows[i]['episode']]==fold]);fit=np.array([i for i in train if assignment[rows[i]['episode']]!=fold])
        assert not {rows[i]['family'] for i in fit}&{rows[i]['family'] for i in val}
        layer,_,_,inner=pick_lr(rows,x,fit,seed+fold*31,loso)
        model=fit_logistic(x[fit,layer],np.array([rows[i]['label'] for i in fit]),np.array([rows[i]['round'] for i in fit]),seed)
        values[val]=score(model,x[val,layer]);notes.append({'fold':fold,'layer':layer,'train_families':sorted({rows[i]['family'] for i in fit}),'test_families':sorted({rows[i]['family'] for i in val}),'inner':inner})
    assert np.isfinite(values[train]).all()
    return values[train],{'split_seed':actual,'folds':notes}

def outer_cases(rows,eligible,seed,loso=False):
    if loso:
        for fold,held in enumerate(sorted({rows[i]['scenario'] for i in eligible})):
            test=np.array([i for i in eligible if rows[i]['scenario']==held]);groups={rows[i]['family'] for i in test}
            others=np.array([i for i in eligible if rows[i]['scenario']!=held and rows[i]['family'] not in groups])
            yield fold,others,test,{'held_scenario':held,'purged_training_test_families':sorted(groups),'split_unit':'scenario_and_family'}
    else:
        assignment,actual=assign_folds(rows,eligible,seed,unit='family')
        for fold in range(5):
            test=np.array([i for i in eligible if assignment[rows[i]['episode']]==fold]);others=np.array([i for i in eligible if assignment[rows[i]['episode']]!=fold])
            yield fold,others,test,{'split_seed':actual,'split_unit':'family'}

def fit_variant(rows,x,out,mode):
    eligible=selected_indices(rows,mode);loso=mode=='loso';mlp=mode in ('v2','loso');added=mode in ('v2','pooled','loso');aux=mode in ('v2','pooled')
    y=np.array([r['label'] for r in rows]);rounds=np.array([r['round'] for r in rows]);scenarios=np.array([r['scenario'] for r in rows]);episodes=np.array([r['episode'] for r in rows]);families=np.array([r['family'] for r in rows]);n=len(rows)
    methods=['nested','fixed32','band26_30','dom32','turn','length','scenario_only','scenario_round']+(['mlp'] if mlp else [])+(['metadata_base','metadata_probe'] if added else [])+(['shuffled32'] if aux else [])
    pred={m:np.full((3,n),np.nan) for m in methods};raw={m:np.full((3,n,4),np.nan) for m in methods};smooth={m:np.full((3,n,4),np.nan) for m in methods};fold_rows=np.full((3,n),-1,dtype=int);shuffled_y=np.full((3,n),-1,dtype=int);notes=[]
    layers=np.full((3,n,len(CANDIDATES)),np.nan)
    for si,seed in enumerate(SEEDS):
        sy=y.copy();rng=np.random.default_rng(seed+9000)
        if aux:
            for scenario in sorted(set(scenarios[eligible])):
                names=sorted({rows[i]['episode'] for i in eligible if rows[i]['scenario']==scenario and rows[i]['condition']=='recruiting'});labels={rows[i]['episode']:rows[i]['label'] for i in eligible};permuted=rng.permutation([labels[e] for e in names]);mapping=dict(zip(names,permuted))
                for i in eligible:
                    if episodes[i] in mapping:sy[i]=mapping[episodes[i]]
            shuffled_y[si]=sy
        for fold,other,test,split_note in outer_cases(rows,eligible,seed,loso):
            started=time.perf_counter();train=other[[rows[i]['condition']=='recruiting' for i in other]];cal=other[[rows[i]['condition'] in ('control','alone') for i in other]]
            assert len(cal)>0 and len(set(y[train]))==2 and not set(families[other])&set(families[test])
            assert all(y[i]==0 for i in cal)
            chosen,inner_train,inner_val,inner_note=pick_lr(rows,x,train,seed+fold*17,loso)
            ev=np.r_[test,cal];scores={};needed=set(CANDIDATES if aux else [chosen,32])|set(range(26,31))
            for layer in sorted(needed):
                model=fit_logistic(x[train,layer],y[train],rounds[train],seed);scores[layer]=score(model,x[ev,layer])
                if layer in {chosen,32,*range(26,31)}:
                    scaler,clf=model;np.savez_compressed(out/f'lr-s{seed}-f{fold}-l{layer}.npz',mean=scaler.mean_,scale=scaler.scale_,coef=clf.coef_,intercept=clf.intercept_)
                if aux and layer in CANDIDATES:layers[si,test,CANDIDATES.index(layer)]=scores[layer][:len(test)]
            values={'nested':scores[chosen],'fixed32':scores[32],'band26_30':np.mean([scores[l] for l in range(26,31)],axis=0),
                    'turn':-rounds[ev].astype(float),'length':np.array([rows[i]['n_tokens'] for i in ev],dtype=float)}
            dom=fit_dom(x[train,32],y[train],rounds[train]);sd=max(float(np.std(score_dom(dom,x[train,32]))),1e-12);values['dom32']=score_dom(dom,x[ev,32])/sd
            values['scenario_only'],rate_note=scenario_rates(rows,train,ev,y[train])
            metadata=fit_metadata(rows,train,y[train],include_length=False);values['scenario_round']=score_metadata(metadata,rows,ev);save_metadata(out/f'scenario-round-s{seed}-f{fold}.npz',metadata)
            np.savez_compressed(out/f'dom-s{seed}-f{fold}.npz',direction=dom[0],center=dom[1],training_projection_sd=sd)
            np.savez_compressed(out/f'split-s{seed}-f{fold}.npz',train=train,test=test,calibration=cal,inner_train=inner_train,inner_validation=inner_val)
            extra={}
            if mlp:
                candidate={}
                for layer in CANDIDATES:
                    model=fit_mlp(x[inner_train,layer],y[inner_train],rounds[inner_train],seed+fold)
                    candidate[layer]=within_round(y[inner_val],score_mlp(model,x[inner_val,layer]),rounds[inner_val],stratum_key=scenarios[inner_val])[0]
                assert any(np.isfinite(v) for v in candidate.values())
                chosen_mlp=max(CANDIDATES,key=lambda l:(candidate[l] if np.isfinite(candidate[l]) else -1,-l))
                model=fit_mlp(x[train,chosen_mlp],y[train],rounds[train],seed+fold);values['mlp']=score_mlp(model,x[ev,chosen_mlp]);save_mlp(out/f'mlp-s{seed}-f{fold}-l{chosen_mlp}.npz',model)
                extra['mlp']={'layer':chosen_mlp,'inner_validation_auroc':candidate,'settings':MLP_SETTINGS,'final_training_loss':model[2][-1]}
            if added:
                meta_scores,stack_note=crossfit_scores(rows,x,train,seed+fold*101,loso)
                base=fit_metadata(rows,train,y[train],include_length=True);aug=fit_metadata(rows,train,y[train],include_length=True,probe=meta_scores)
                save_metadata(out/f'metadata-base-s{seed}-f{fold}.npz',base);save_metadata(out/f'metadata-probe-s{seed}-f{fold}.npz',aug)
                values['metadata_base']=score_metadata(base,rows,ev);values['metadata_probe']=score_metadata(aug,rows,ev,probe=values['nested']);extra['stacking']=stack_note
                np.savez_compressed(out/f'stacking-s{seed}-f{fold}.npz',train_indices=train,train_crossfit_probe=meta_scores)
            if aux:values['shuffled32']=score(fit_logistic(x[train,32],sy[train],rounds[train],seed),x[ev,32])
            calibration={}
            for method,s in values.items():
                assert np.isfinite(s).all();pred[method][si,test]=s[:len(test)];calibration[method]={}
                cal_scores=s[len(test):];cal_ema=ema_max(cal_scores,episodes[cal])
                for fi,fpr in enumerate(FPRS):
                    t,info=threshold_at_fpr(cal_scores,episodes[cal],fpr);te,ei=threshold_at_fpr(cal_ema,episodes[cal],fpr)
                    raw[method][si,test,fi]=t;smooth[method][si,test,fi]=te;calibration[method][str(fpr)]={'raw_threshold':t,'ema_threshold':te,'raw':info,'ema':ei}
            fold_rows[si,test]=fold
            note={'seed':seed,'fold':fold,**split_note,'chosen_layer':chosen,'inner':inner_note,'scenario_rate_baseline':rate_note,'calibration':calibration,
                'train_episodes':sorted(set(episodes[train])),'test_episodes':sorted(set(episodes[test])),'calibration_episodes':sorted(set(episodes[cal])),
                'train_families':sorted(set(families[train])),'test_families':sorted(set(families[test])),'calibration_families':sorted(set(families[cal])),**extra,'seconds':time.perf_counter()-started}
            notes.append(note);write_json(out/'folds.json',notes);print('FIT',mode,seed,fold,'layer',chosen,'seconds',round(note['seconds'],1),flush=True)
        for m in methods:assert np.isfinite(pred[m][si,eligible]).all()
    np.savez_compressed(out/'predictions.npz',**pred,**{'threshold_'+k:v for k,v in raw.items()},**{'ema_threshold_'+k:v for k,v in smooth.items()},eligible=eligible,y=y,folds=fold_rows,seeds=SEEDS,fprs=FPRS,shuffled_labels=shuffled_y,layer_scores=layers)

def main(args):
    source=ROOT/'runs'/args.data_run;gate=json.loads((ROOT/'runs'/args.control_run/'summary.json').read_text());assert gate['gate_passed'] and gate['gate_auc']>=.95
    rows=[json.loads(s) for s in (source/'rows.jsonl').read_text().splitlines()];x=np.load(source/'features.npy',mmap_mode='r')
    modes=args.modes.split(',');allowed={'v2','pooled','loso','deliberate_v2','deliberate_pooled'};assert set(modes)<=allowed
    run=start_run('e05-replay2-fits',experiment='E05',parents=[args.data_run,args.control_run],settings={'modes':modes,'seeds':SEEDS,'candidate_layers':CANDIDATES,'mlp':MLP_SETTINGS,'L2_C':.1,'primary_metric':'within scenario x round','alarm_basis':'any alarm per pooled training control/alone episode','FPR_targets':FPRS,'LOSO':'test scenario plus purged shared family IDs','stacking':'three family folds, layer selected again inside each stack-training fold'})
    try:
        with threadpool_limits(limits=4):
            for mode in modes:
                out=run.dir/mode;out.mkdir();fit_variant(rows,x,out,mode)
        run.result(all_fits_complete=True);run.finish();print('REPLAY2_FITS',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('data_run');p.add_argument('control_run');p.add_argument('--modes',default='v2,pooled,loso,deliberate_v2,deliberate_pooled');main(p.parse_args())
