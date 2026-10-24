"""Group-bootstrap evaluation of frozen out-of-fold predictions."""
import json
from pathlib import Path
import numpy as np
from metrics import auc,within_round,length_match,partial_auc,ema_max,stratum_masks

def finite_mean(values,axis=None):
    values=np.asarray(values,dtype=float);valid=np.isfinite(values)
    count=np.sum(valid,axis=axis);total=np.sum(np.where(valid,values,0),axis=axis)
    return np.divide(total,count,out=np.full(np.shape(total),np.nan),where=count>0)

METHODS=['nested','fixed32','band26_30','dom32','turn','length','shuffled32']

class PairStatistic:
    def __init__(self,y,s,codes,n_groups):
        y=np.asarray(y);codes=np.asarray(codes);s=np.asarray(s)
        p=np.flatnonzero(y==1);n=np.flatnonzero(y==0)
        self.positive=np.bincount(codes[p],minlength=n_groups).astype(float)
        self.negative=np.bincount(codes[n],minlength=n_groups).astype(float)
        self.matrix=np.zeros((n_groups,n_groups),dtype=float)
        if len(p) and len(n):
            wins=(s[p,None]>s[n][None,:]).astype(float)+.5*(s[p,None]==s[n][None,:])
            np.add.at(self.matrix,(codes[p,None],codes[n][None,:]),wins)
    def evaluate(self,weights):
        p=weights@self.positive;n=weights@self.negative
        numerator=np.sum((weights@self.matrix)*weights,axis=1)
        values=np.divide(numerator,p*n,out=np.full(len(weights),np.nan),where=(p*n)>0)
        return values,p


def score_bootstrap(y,s,rounds,codes,weights,*,stratum_key=None):
    total=PairStatistic(y,s,codes,weights.shape[1]);pooled,_=total.evaluate(weights)
    numerator=np.zeros(len(weights));denominator=np.zeros(len(weights))
    for _,_,m in stratum_masks(rounds,stratum_key):
        values,p=PairStatistic(y[m],s[m],codes[m],weights.shape[1]).evaluate(weights)
        ok=np.isfinite(values);numerator[ok]+=values[ok]*p[ok];denominator[ok]+=p[ok]
    within=np.divide(numerator,denominator,out=np.full(len(weights),np.nan),where=denominator>0)
    return within,pooled


def interval(values):
    values=np.asarray(values);values=values[np.isfinite(values)]
    return [float(x) for x in np.quantile(values,[.025,.975])] if len(values) else None


def ranking_summary(y,scores,rounds,groups,reps=1000,seed=20261024,*,stratum_key=None):
    names,codes=np.unique(groups,return_inverse=True)
    weights=np.random.default_rng(seed).multinomial(len(names),np.ones(len(names))/len(names),size=reps).astype(float)
    within=[];pooled=[];wboot=[];pboot=[];coverage=[]
    for yseed,s in zip(y,scores):
        a,detail=within_round(yseed,s,rounds,stratum_key=stratum_key);within.append(a);coverage.append(detail['positive_coverage']);pooled.append(auc(yseed,s))
        a,b=score_bootstrap(yseed,s,rounds,codes,weights,stratum_key=stratum_key);wboot.append(a);pboot.append(b)
    wb=finite_mean(wboot,axis=0);pb=finite_mean(pboot,axis=0)
    return dict(within_round_auc=float(finite_mean(within)),within_round_by_seed=within,within_round_ci95=interval(wb),
                pooled_auc=float(finite_mean(pooled)),pooled_by_seed=pooled,pooled_ci95=interval(pb),
                positive_coverage_by_seed=coverage,bootstrap_groups=len(names),bootstrap_reps=reps,within_round_valid_bootstrap_reps=int(np.isfinite(wb).sum()),pooled_valid_bootstrap_reps=int(np.isfinite(pb).sum())),wb,pb


def alert_summary(rows,indices,scores,thresholds,y,reps=1000):
    ep=np.array([rows[i]['episode'] for i in indices]);family=np.array([rows[i]['family'] for i in indices]);condition=np.array([rows[i]['condition'] for i in indices])
    names=sorted(set(ep));record=[]
    for si,(s,t) in enumerate(zip(scores,thresholds)):
        running=ema_max(s,ep);episodes=[]
        for name in names:
            m=ep==name;local=np.flatnonzero(m);first=local[0];label=int(y[first]);ctrl=condition[first]!='recruiting'
            assert np.all(t[m]==t[first]) and np.all(y[m]==label)
            raw_alert=s[m]>t[m];smooth_alert=running[m]>t[m]
            hit=np.flatnonzero(smooth_alert)
            lead=None;round_lead=None
            if label==1 and len(hit):
                row=rows[indices[local[hit[0]]]];lead=row['steps_until_action'];round_lead=row['first_action_round']-row['round']
            episodes.append(dict(episode=name,family=family[first],label=label,control=bool(ctrl),raw_alert=bool(raw_alert.any()),
                ema_alert=bool(smooth_alert.any()),ema_lead_steps=lead,ema_lead_rounds=round_lead))
        record.append(episodes)
    def rate(items,label,control,field):
        subset=[x for x in items if x['label']==label and x['control']==control]
        return float(np.mean([x[field] for x in subset])) if subset else None
    result={}
    for field in ('raw_alert','ema_alert'):
        for name,label,control in [('episode_recall',1,False),('held_recruiting_fpr',0,False),('heldout_control_fpr',0,True)]:
            values=[rate(items,label,control,field) for items in record]
            result[field+'_'+name]=float(np.mean([x for x in values if x is not None])) if any(x is not None for x in values) else None
    result['step_recall']=float(np.mean([np.mean(s[y==1]>t[y==1]) for s,t in zip(scores,thresholds)])) if np.any(y==1) else None
    leads=[r['ema_lead_steps'] for seed in record for r in seed if r['ema_lead_steps'] is not None]
    result['ema_median_lead_steps_conditional_on_detection']=float(np.median(leads)) if leads else None
    families=sorted(set(x['family'] for x in record[0]));lookup={g:i for i,g in enumerate(families)}
    weights=np.random.default_rng(2718).multinomial(len(families),np.ones(len(families))/len(families),size=reps)
    ratios=[]
    for records in record:
        denominator=np.zeros(len(families));numerator=np.zeros(len(families))
        for r in records:
            if r['label']==1 and not r['control']:
                k=lookup[r['family']];denominator[k]+=1;numerator[k]+=r['raw_alert']
        d=weights@denominator;ratios.append(np.divide(weights@numerator,d,out=np.full(reps,np.nan),where=d>0))
    result['raw_alert_episode_recall_family_ci95']=interval(finite_mean(ratios,axis=0))
    return result,record


def evaluate_variant(rows,path,reps=1000):
    data=np.load(path/'predictions.npz');eligible=data['eligible'];yall=data['y'];head=eligible[np.array([rows[i]['condition']=='recruiting' for i in eligible])]
    rounds=np.array([rows[i]['round'] for i in head]);y=yall[head];family=np.array([rows[i]['family'] for i in head]);episode=np.array([rows[i]['episode'] for i in head]);lengths=np.array([rows[i]['n_tokens'] for i in head])
    matched=length_match(y,lengths,rounds)
    subsets={'all':np.arange(len(head)),'strict_pre_action':np.flatnonzero([not rows[i]['acts_this_step'] for i in head]),
        'decision_not_visible':np.flatnonzero([not rows[i]['decision_visible'] for i in head]),'length_matched':matched,
        'provisional_refuses':np.flatnonzero([rows[i]['stated_position']=='refuses' for i in head])}
    methods=[m for m in METHODS if m in data.files];results={};bootstrap={};alerts={}
    for method in methods:
        scores=data[method][:,head];ys=data['shuffled_labels'][:,head] if method=='shuffled32' else np.tile(y,(len(scores),1))
        main,wb,pb=ranking_summary(ys,scores,rounds,family,reps)
        episode_ci,_,_=ranking_summary(ys,scores,rounds,episode,reps)
        main['episode_bootstrap_within_ci95']=episode_ci['within_round_ci95'];main['episode_bootstrap_pooled_ci95']=episode_ci['pooled_ci95']
        main['partial_auc_by_seed']=[partial_auc(a,b) for a,b in zip(ys,scores)]
        main['subsets']={}
        for name,mask in subsets.items():
            if name=='all':continue
            per=[];pooled=[];coverage=[]
            for yy,ss in zip(ys,scores):
                value,detail=within_round(yy[mask],ss[mask],rounds[mask]);per.append(value);pooled.append(auc(yy[mask],ss[mask]));coverage.append(detail['positive_coverage'])
            main['subsets'][name]=dict(rows=len(mask),episodes=len(set(episode[mask])),positives=int(y[mask].sum()),within_round_auc=float(finite_mean(per)),pooled_auc=float(finite_mean(pooled)),within_round_by_seed=per,positive_coverage_by_seed=coverage)
            if path.name=='main' and name in ('strict_pre_action','decision_not_visible','length_matched') and len(np.unique(y[mask]))==2:
                summary,_,_=ranking_summary(ys[:,mask],scores[:,mask],rounds[mask],family[mask],reps)
                main['subsets'][name]['family_ci95']=summary['within_round_ci95']
        if method!='shuffled32':
            main['alerts'],records=alert_summary(rows,eligible,data[method][:,eligible],data['threshold_'+method][:,eligible],yall[eligible],reps);alerts[method]=records
            main['all_negatives_pooled_auc']=float(np.mean([auc(yall[eligible],s[eligible]) for s in data[method]]))
        results[method]=main;bootstrap[method]=wb
        print(path.name,method,main['within_round_auc'],flush=True)
    differences={}
    for method in ('nested','fixed32','band26_30','dom32'):
        if method in bootstrap:
            differences[method+'_minus_length']=dict(mean=results[method]['within_round_auc']-results['length']['within_round_auc'],paired_family_ci95=interval(bootstrap[method]-bootstrap['length']))
    result=dict(methods=results,paired_differences=differences,headline_rows=len(head),headline_episodes=len(set(episode)),headline_families=len(set(family)),positive_rows=int(y.sum()),negative_rows=int((y==0).sum()),
        positive_episodes=len(set(episode[y==1])),negative_episodes=len(set(episode[y==0])),calibration_only_rows=len(eligible)-len(head),
        length_matched_rows=len(matched),length_match_log_caliper=.1)
    if 'positive_control' in data.files and np.isfinite(data['positive_control']).any():
        pc=data['positive_control'];indices=np.flatnonzero(np.isfinite(pc).all(axis=0));py=np.array([rows[i]['token_in_context'] for i in indices],dtype=int)
        pf=np.array([rows[i]['family'] for i in indices]);pr=np.array([rows[i]['round'] for i in indices])
        result['positive_control'],_,_=ranking_summary(np.tile(py,(len(pc),1)),pc[:,indices],pr,pf,reps)
    return result,alerts
