"""Round-stratified ranking and episode-level alert metrics."""
import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve
from scipy.optimize import linear_sum_assignment


def auc(y,s,w=None):
    y=np.asarray(y,dtype=int);s=np.asarray(s);w=np.ones(len(y)) if w is None else np.asarray(w)
    if not len(y):return float('nan')
    _,inv=np.unique(s,return_inverse=True)
    pos=np.bincount(inv,weights=w*y);neg=np.bincount(inv,weights=w*(1-y))
    if pos.sum()==0 or neg.sum()==0:return float('nan')
    return float((pos*(np.cumsum(neg)-neg*.5)).sum()/(pos.sum()*neg.sum()))


def within_round(y,s,rounds,w=None):
    y=np.asarray(y);s=np.asarray(s);rounds=np.asarray(rounds);w=np.ones(len(y)) if w is None else np.asarray(w)
    numerator=denominator=0.;detail=[]
    for rnd in np.unique(rounds):
        m=rounds==rnd;score=auc(y[m],s[m],w[m]);n=float((w[m]*y[m]).sum())
        if np.isfinite(score):numerator+=n*score;denominator+=n;detail.append({'round':int(rnd),'auc':score,'positive_weight':n})
    return (numerator/denominator if denominator else float('nan')),dict(rounds=detail,positive_coverage=denominator/float((w*y).sum()) if (w*y).sum() else None)


def position_weights(y,rounds):
    y=np.asarray(y);rounds=np.asarray(rounds);w=np.zeros(len(y),dtype=float)
    for rnd in np.unique(rounds):
        p=(rounds==rnd)&(y==1);n=(rounds==rnd)&(y==0)
        if p.any() and n.any():w[p]=1;w[n]=p.sum()/n.sum()
    if not w.any():raise ValueError('No position-matched training rounds')
    return w/w[w>0].mean()


def episode_max(scores,groups):
    return {g:float(np.max(scores[np.asarray(groups)==g])) for g in sorted(set(groups))}


def threshold_at_fpr(scores,groups,fpr=.05):
    values=np.asarray(list(episode_max(np.asarray(scores),np.asarray(groups)).values()))
    if len(values)==0:raise ValueError('No calibration control episodes')
    allowed=int(np.floor(fpr*len(values)))
    threshold=float(np.sort(values)[len(values)-allowed-1])
    return threshold,dict(calibration_episodes=len(values),calibration_fpr=float(np.mean(values>threshold)),comparison='strictly greater')


def length_match(y,lengths,rounds,caliper=.1):
    y=np.asarray(y);lengths=np.asarray(lengths);rounds=np.asarray(rounds);selected=[]
    for rnd in np.unique(rounds):
        pos=np.flatnonzero((rounds==rnd)&(y==1));neg=np.flatnonzero((rounds==rnd)&(y==0))
        if not len(pos) or not len(neg):continue
        cost=np.abs(np.log(lengths[pos,None])-np.log(lengths[neg][None,:]))
        a,b=linear_sum_assignment(np.where(cost<=caliper,cost,1e6))
        ok=cost[a,b]<=caliper;selected.extend(pos[a[ok]]);selected.extend(neg[b[ok]])
    return np.asarray(sorted(selected),dtype=int)


def partial_auc(y,s):
    if len(set(y))<2:return None
    fpr,tpr,_=roc_curve(y,s)
    xx=np.r_[.01,fpr[(fpr>.01)&(fpr<.2)],.2];yy=np.interp(xx,fpr,tpr)
    return {'standardized_0_to_20pct':float(roc_auc_score(y,s,max_fpr=.2)),
            'mean_tpr_1_to_20pct':float(np.trapezoid(yy,xx)/.19)}


def ema_max(scores,episodes,alpha=.5):
    out=np.zeros(len(scores));state={}
    for i,(score,ep) in enumerate(zip(scores,episodes)):
        ema,peak=state.get(ep,(float(score),float('-inf')))
        ema=alpha*float(score)+(1-alpha)*ema;peak=max(peak,ema);state[ep]=(ema,peak);out[i]=peak
    return out
