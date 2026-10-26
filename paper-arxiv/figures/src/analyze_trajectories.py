"""Descriptive alignment of saved last-prompt scores; no fitting or new inference."""
import argparse,csv,gzip,hashlib,json
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import rankdata

ROOT=Path(__file__).resolve().parents[3]

def read(path):
    with (gzip.open(path,'rt') if path.suffix=='.gz' else path.open()) as f:return list(csv.DictReader(f))

def main():
    p=argparse.ArgumentParser();p.add_argument('--saved-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    plan=dict(transform='Within each saved seed/fold, rank all evaluation scores to percentiles, then average seed percentiles per call. Descriptive, uses evaluation distribution; not an online score.',alignment='Scored calls before first positive call; unscored calls may intervene.',gate='Median paired leak-minus-previous-scored-call percentile increase has family-bootstrap 95% lower bound > 0 in every model/cohort.',examples='One fresh leaking episode per model, upper median of scored sequence length, episode path tie-break; requires at least five scored calls.',bootstrap=1000,seed=20261026)
    (a.output/'analysis_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    specs=[('qwen','development',ROOT/'runs/20261026-2201-e05-arxiv-qwen-any-public/probe_scores.csv.gz'),('qwen','fresh',ROOT/'runs/20261026-2212-e05-arxiv-qwen-fresh-percall/probe_scores.csv.gz'),('gpt_oss','development',a.saved_root/'runs/20261026-1221-e05-lastprompt-percall-6013/probe_scores.csv.gz'),('gpt_oss','fresh',ROOT/'runs/20261026-2222-e05-arxiv-gpt-fresh-percall/probe_scores.csv.gz')]
    summaries=[];export=[];examples=[];sources={};rng=np.random.default_rng(plan['seed'])
    for model,cohort,path in specs:
        sources[str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path.relative_to(a.saved_root))]=hashlib.sha256(path.read_bytes()).hexdigest()
        rows=read(path)
        if cohort=='development':rows=[r for r in rows if r['analysis']=='loso' and r['label_variant']=='immediate' and (model=='qwen' or r['cohort']=='matched')]
        groups=defaultdict(list)
        for r in rows:groups[(r.get('seed','ensemble'),r.get('fold','0'))].append(r)
        bycall=defaultdict(list)
        for group in groups.values():
            ranks=(rankdata([float(r['score']) for r in group],method='average')-.5)/len(group)
            for r,v in zip(group,ranks):bycall[r['row_id']].append((r,float(v)))
        episodes=defaultdict(list)
        for rid,parts in bycall.items():
            r=parts[0][0];assert len({int(v[0]['label']) for v in parts})==1
            episodes[r['episode']].append(dict(row_id=rid,request_idx=int(rid.rsplit('=',1)[1]),label=int(r['label']),score=float(np.mean([v for _,v in parts])),family=r.get('family',r['episode'])))
        aligned=[];deltas=[];eligible=[]
        for episode,seq in episodes.items():
            seq.sort(key=lambda r:r['request_idx']);positive=[i for i,r in enumerate(seq) if r['label']]
            if not positive:continue
            assert len(positive)==1
            end=positive[0];seq=seq[:end+1]
            for i,r in enumerate(seq):
                rec=dict(model=model,cohort=cohort,episode=episode,offset=i-end,**r);aligned.append(rec);export.append(rec)
            if end:
                deltas.append((seq[-1]['family'],seq[-1]['score']-seq[-2]['score']))
                if len(seq)>=5:eligible.append((episode,seq))
        families=sorted({f for f,_ in deltas});fm={f:[d for ff,d in deltas if ff==f] for f in families}
        boot=[np.median([v for i in rng.integers(len(families),size=len(families)) for v in fm[families[i]]]) for _ in range(plan['bootstrap'])]
        ci=np.quantile(boot,[.025,.975]).tolist();aggregate=[]
        for offset in range(-10,1):
            values=[r['score'] for r in aligned if r['offset']==offset]
            if values:aggregate.append(dict(offset=offset,n=len(values),median=float(np.median(values)),q25=float(np.quantile(values,.25)),q75=float(np.quantile(values,.75))))
        summaries.append(dict(model=model,cohort=cohort,calls=len(bycall),episodes=len(episodes),leaking_episodes=sum(any(r['label'] for r in v) for v in episodes.values()),paired_episodes=len(deltas),paired_median_jump=float(np.median([v for _,v in deltas])),paired_jump_ci95=ci,gate_pass=ci[0]>0,aggregate=aggregate))
        if cohort=='fresh':
            eligible.sort(key=lambda x:(len(x[1]),x[0]));episode,seq=eligible[len(eligible)//2]
            examples.append(dict(model=model,episode=episode,selection_rank=len(eligible)//2,eligible_episodes=len(eligible),calls=[dict(offset=i-len(seq)+1,**r) for i,r in enumerate(seq)]))
    result=dict(plan=plan,sources=sources,summaries=summaries,examples=examples,include_figure=all(s['gate_pass'] for s in summaries))
    (a.output/'metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    with (a.output/'aligned_scores.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(export[0]),lineterminator='\n');w.writeheader();w.writerows(export)
    print(json.dumps([{k:v for k,v in s.items() if k!='aggregate'} for s in summaries],indent=2))
    print('INCLUDE_FIGURE',result['include_figure'])
if __name__=='__main__':main()
