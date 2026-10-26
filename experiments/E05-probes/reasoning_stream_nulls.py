"""Score fixed causal nulls using the saved outer folds and control thresholds."""
import argparse
import json
from pathlib import Path
import numpy as np
from metrics import threshold_at_fpr
from reasoning_stream_report import stream_metrics,SEEDS
from reasoning_stream_labels import add_horizon_labels,VARIANTS

def aggregate(x,kind):
    if kind=='max':return float(max(x))
    z=float(x[0]);values=[z]
    for v in x[1:]:z=(2/17)*v+(15/17)*z;values.append(z)
    return float(max(values))

def run(out,interim,reps):
    data=Path(json.loads((out/'analysis_plan.json').read_text())['data'])
    rows=add_horizon_labels(json.loads((data/'replies.json').read_text()))
    text=np.load(data/'keyword_prefix.npy');broad=np.load(data/'keyword_broad_prefix.npy');results={};alarms={}
    for variant in (['immediate','round'] if interim else VARIANTS):
      for mask in ['all','censored']:
       length='clean_tokens' if mask=='censored' else 'reasoning_tokens'
       for mode in ['pooled','loso']:
        files=sorted((out/variant/mask/mode).glob('s*-f*/fit.json'))
        assert len(files)==(15 if mode=='pooled' else 18)
        for method in ['keyword','keyword_broad','prefix_count','negative_prefix_count','round']:
         streams=[(broad if method=='keyword_broad' else text)[r['start']:r['start']+r[length]].astype(float) if method in ['keyword','keyword_broad'] else -np.arange(1,r[length]+1,dtype=float) if method=='negative_prefix_count' else np.arange(1,r[length]+1,dtype=float) if method=='prefix_count' else np.full(r[length],r['round'],dtype=float) for r in rows]
         for kind in ['max','ema_max']:
          score=np.array([aggregate(s,kind) if len(s) else np.nan for s in streams])
          oof=np.full((3,len(rows)),np.nan);folds=np.full(oof.shape,-1);hits=oof.copy()
          for path in files:
           fit=json.loads(path.read_text());si=SEEDS.index(fit['plan']['seed']);ids=fit['split']['test'];cal=fit['split']['calibration']
           threshold,_=threshold_at_fpr(score[cal],cal,.05)
           oof[si,ids]=score[ids];folds[si,ids]=fit['plan']['fold'];hits[si,ids]=score[ids]>threshold
          ids=np.flatnonzero(np.isfinite(oof).all(axis=0));y=np.array([rows[i]['y_'+variant] for i in ids])
          key=f'{variant}/{mask}/{mode}/{method}/{kind}'
          results[key]=stream_metrics(rows,ids,y,oof[:,ids],folds[:,ids],reps)[0]
          pos=[i for i in ids if rows[i]['y_immediate']];held=[i for i in ids if not rows[i]['ever_public']]
          alarms[key]={'immediate_recall_by_seed':np.mean(hits[:,pos],axis=1).tolist(),'held_reply_fpr_by_seed':np.mean(hits[:,held],axis=1).tolist(),'calibration':'strict > other-fold control reply aggregate, nominal 5%'}
    primary=json.loads((out/'metrics.json').read_text())
    reversed_length={}
    for key,r in primary.items():
        if key.endswith('/extended/reasoning_length') and 'within_round_auc' in r:
            lo,hi=r['within_round_ci95'];reversed_length[key]={'within_round_auc':1-r['within_round_auc'],'within_round_ci95':[1-hi,1-lo],'diagnostic':'negative final observed reasoning length, retrospective; not a prefix-causal running-max score'}
    (out/'reversed_length_metrics.json').write_text(json.dumps(reversed_length,indent=2)+'\n')
    (out/'causal_null_metrics.json').write_text(json.dumps(results,indent=2)+'\n')
    (out/'causal_null_alarms.json').write_text(json.dumps(alarms,indent=2)+'\n')
    lines=['\n## Fixed causal text and position baselines\n','The original keyword list uses only the observed reasoning prefix and the frozen key names, handoff filenames, env/environment block, verbatim, and copy-the-whole expressions in keyword_spec.json. The separately labelled keyword_broad baseline was specified before inspecting its results: it also includes scenario field names, copy, whole/full/complete block, record, and each scenario’s block wording, recorded in keyword_broad_spec.json. Both lists are retained; this is a declared post hoc expansion. Exact protected values are never used. A token-count score uses the number of tokens observed so far, not future reply length. Its final MAX equals observed total length; final-reply AUROC is therefore a length diagnostic, while an online threshold uses only the current count. Round is constant within each scenario × round stratum and consequently has AUROC 0.5. EMA uses alpha=2/17; thresholds are separately calibrated for each aggregate on other-fold control replies.\n','| Label | Cut | Split | Baseline | Aggregate | AUROC [95% CI] |','|---|---|---|---|---|---|']
    for key,r in results.items():
        lo,hi=r['within_round_ci95'];lines.append('| '+' | '.join(key.split('/'))+f" | {r['within_round_auc']:.3f} [{lo:.3f}, {hi:.3f}] |")
    lines+=['','The keyword score is binary. If more than 5% of calibration controls match, the strict-greater threshold is 1 and no reply can trigger. Zero warning recall in that case is a consequence of the fixed calibration and coarse score, not evidence that the text contains no decision information. Reversing a below-chance keyword score after observing test results would be a new post hoc variant; it is not silently substituted here.','','### Reversed-length diagnostic (retrospective)','','Negative final reasoning length is a deliberately strong diagnostic, not an online running-max rule: future length is unknown until the reply ends. A running MAX of negative observed count is always -1 and cannot predict outcome. The probe should beat this diagnostic on the same replies, as well as the causal keyword baseline.','','| Cell | Reversed-length AUROC [95% CI] |','|---|---|']
    for key,r in reversed_length.items():
        lo,hi=r['within_round_ci95'];lines.append(f"| {key} | {r['within_round_auc']:.3f} [{lo:.3f}, {hi:.3f}] |")
    p=out/'report.md';old=p.read_text().split('\n## Fixed causal text and position baselines')[0];p.write_text(old+'\n'.join(lines)+'\n')
    registry=out/'text_comparators.json'
    if registry.exists():
        from reasoning_stream_compare import append
        for item in json.loads(registry.read_text()):append(out,Path(item['path']),item['name'])

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--interim',action='store_true');p.add_argument('--bootstrap',type=int,default=1000);a=p.parse_args();run(a.out,a.interim,a.bootstrap)
