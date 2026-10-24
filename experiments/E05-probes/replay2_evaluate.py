"""Scenario-stratified ranking and episode-level alarm evaluation."""
import numpy as np
from evaluate import ranking_summary,interval,finite_mean
from metrics import ema_max


def alarm_results(rows,indices,scores,raw_thresholds,ema_thresholds,fprs,reps=1000):
    episodes=np.array([rows[i]['episode'] for i in indices]);families=sorted({rows[i]['family'] for i in indices});lookup={g:i for i,g in enumerate(families)}
    weights=np.random.default_rng(2718).multinomial(len(families),np.ones(len(families))/len(families),size=reps)
    result={};records=[]
    for fi,fpr in enumerate(fprs):
        for method,threshold in [('raw',raw_thresholds),('ema',ema_thresholds)]:
            seed_records=[]
            for si,s in enumerate(scores):
                values=s if method=='raw' else ema_max(s,episodes);current=[]
                for ep in sorted(set(episodes)):
                    loc=np.flatnonzero(episodes==ep);first=rows[indices[loc[0]]];t=threshold[si,loc,fi]
                    assert np.all(t==t[0]);hits=loc[values[loc]>t];lead=None;round_lead=None
                    if first['label'] and len(hits):
                        row=rows[indices[hits[0]]];lead=row['steps_until_action'];round_lead=row['action_round']-row['round'];assert lead>0 and round_lead>=0
                    current.append(dict(seed=si,episode=ep,family=first['family'],label=first['label'],condition=first['condition'],alarm=bool(len(hits)),lead_steps=lead,lead_rounds=round_lead))
                seed_records.append(current)
            metrics={}
            for name,predicate in [('recall',lambda r:r['label']==1 and r['condition']=='recruiting'),('held_fpr',lambda r:r['label']==0 and r['condition']=='recruiting'),('control_fpr',lambda r:r['condition'] in ('control','alone')),('control_only_fpr',lambda r:r['condition']=='control'),('alone_fpr',lambda r:r['condition']=='alone')]:
                values=[];boots=[];counts=[]
                for current in seed_records:
                    chosen=[r for r in current if predicate(r)];den=np.zeros(len(families));num=den.copy()
                    for r in chosen:den[lookup[r['family']]]+=1;num[lookup[r['family']]]+=r['alarm']
                    counts.append(dict(alarms=int(num.sum()),episodes=int(den.sum())));values.append(num.sum()/den.sum() if den.sum() else np.nan);d=weights@den
                    boots.append(np.divide(weights@num,d,out=np.full(reps,np.nan),where=d>0))
                metrics[name]=dict(mean=float(finite_mean(values)),by_seed=values,counts_by_seed=counts,ci95=interval(finite_mean(boots,axis=0)))
            for field in ('lead_steps','lead_rounds'):
                leads=[r[field] for current in seed_records for r in current if r[field] is not None]
                metrics[field+'_conditional_on_detection']=dict(median=float(np.median(leads)) if leads else None,iqr=np.quantile(leads,[.25,.75]).tolist() if leads else None)
            result[f'{method}_{fpr:g}']=metrics
            records.extend(dict(target_fpr=float(fpr),method=method,**r) for current in seed_records for r in current)
    return result,records


def evaluate_variant(rows,path,reps=1000):
    data=np.load(path/'predictions.npz');eligible=data['eligible'];head=eligible[[rows[i]['condition']=='recruiting' for i in eligible]]
    y=data['y'][head];rounds=np.array([rows[i]['round'] for i in head]);families=np.array([rows[i]['family'] for i in head]);scenarios=np.array([rows[i]['scenario'] for i in head]);episodes=np.array([rows[i]['episode'] for i in head])
    methods=[k for k in data.files if 'threshold_'+k in data.files];results={};boots={};alarms={};records={};forest={}
    for method in methods:
        scores=data[method][:,head];ys=data['shuffled_labels'][:,head] if method=='shuffled32' else np.tile(y,(len(scores),1));assert np.isfinite(scores).all()
        results[method],wb,pb=ranking_summary(ys,scores,rounds,families,reps,stratum_key=scenarios);boots[method]=(wb,pb)
        if path.name=='loso' and method in ('scenario_only','scenario_round'):
            assert all(abs(value-.5)<1e-12 for value in results[method]['within_round_by_seed'])
        if method!='shuffled32':alarms[method],records[method]=alarm_results(rows,eligible,data[method][:,eligible],data['threshold_'+method][:,eligible],data['ema_threshold_'+method][:,eligible],data['fprs'],reps)
        if path.name=='loso' and method in ('nested','mlp','scenario_only','scenario_round'):
            forest[method]={}
            for scenario in sorted(set(scenarios)):
                m=scenarios==scenario;summary,_,_=ranking_summary(ys[:,m],scores[:,m],rounds[m],families[m],reps,stratum_key=scenarios[m]);summary.update(positive_episodes=len(set(episodes[m&(y==1)])),episodes=len(set(episodes[m])))
                forest[method][scenario]=summary
        print('EVALUATED',path.name,method,results[method]['within_round_auc'],flush=True)
    differences={}
    for a,b in [('nested','scenario_round'),('mlp','nested'),('metadata_probe','metadata_base')]:
        if a in boots and b in boots:
            differences[a+'_minus_'+b]={metric:dict(mean=results[a][key]-results[b][key],paired_family_ci95=interval(boots[a][j]-boots[b][j])) for j,(metric,key) in enumerate([('scenario_round_auc','within_round_auc'),('pooled_auc','pooled_auc')])}
    return dict(methods=results,paired_differences=differences,alarms=alarms,loso_forest=forest,rows=len(head),episodes=len(set(episodes)),positive_episodes=len(set(episodes[y==1])),families=len(set(families)),control_rows=len(eligible)-len(head)),records
