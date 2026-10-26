"""Saved-score alarm sweeps around existing control-calibrated thresholds."""
import argparse,csv,gzip,hashlib,json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from style import configure,MODEL_COLORS
ROOT=Path(__file__).resolve().parents[3]

def read(path):
    with (gzip.open(path,'rt') if path.suffix=='.gz' else path.open()) as f:return list(csv.DictReader(f))

def main():
    p=argparse.ArgumentParser();p.add_argument('--saved-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    source={}
    def src(rel):
        path=ROOT/rel
        if not path.exists():path=a.saved_root/rel
        source[rel]=hashlib.sha256(path.read_bytes()).hexdigest();return path
    def j(rel):return json.loads(src(rel).read_text())
    panels=[]
    q=read(src('runs/20261026-2212-e05-arxiv-qwen-fresh-percall/probe_scores.csv.gz'))
    ever={f"{r['episode']}::request_idx={r['request_idx']}":bool(r['y_eventual']) for r in j('runs/20261026-2155-e05-qwen-any-public-audit/rows.json')}
    threshold=j('paper-arxiv/frozen/qwen_percall_plan.json')['threshold']
    ids={r['row_id']:r for r in q};methods={'Last-prompt probe':[(float(r['score'])-threshold,int(r['label']),not ever[r['row_id']]) for r in q]}
    ts={(str(t['seed']),str(t['fold'])):t['threshold'] for t in j('runs/20261026-1309-e06-percall-input-jev-qwen/thresholds.json')['loso']}
    jev=[r for r in read(src('runs/20261026-1309-e06-percall-input-jev-qwen/probe_scores.csv')) if r['analysis']=='loso' and r['row_id'] in ids]
    assert len(jev)==3*len(q)
    methods['Jev']=[]
    for r in jev:
        ref=ids[r['row_id']];assert r['request_sha256']==ref['request_sha256'];m=float(r['score'])-ts[(r['seed'],r['fold'])];assert (m>0)==(r['alarm']=='True')
        methods['Jev'].append((m,int(ref['label']),not ever[r['row_id']]))
    panels.append(('Qwen: fresh episodes','qwen',methods))
    meta={r['row_id']:r for r in j('runs/20261026-0522-e05-reasoning-stream-data/replies.json')}
    dev=[r for r in read(src('runs/20261026-1221-e05-lastprompt-percall-6013/probe_scores.csv.gz')) if r['cohort']=='matched' and r['label_variant']=='immediate' and r['analysis']=='loso']
    assert len(dev)==1995*3;ids={r['row_id']:r for r in dev};methods={'Last-prompt probe':[]}
    ts={}
    for r in dev:
        k=(r['seed'],r['fold'])
        if k not in ts:ts[k]=j(f"runs/20261026-1221-e05-lastprompt-percall-6013/matched/immediate/loso/s{k[0]}-f{k[1]}/fit.json")['threshold']
        m=float(r['score'])-ts[k];assert (m>0)==(r['alarm']=='True')
        methods['Last-prompt probe'].append((m,int(r['label']),not bool(meta[r['row_id']]['ever_public'])))
    ts={(str(t['seed']),str(t['fold'])):t['threshold'] for t in j('runs/20261026-1319-e06-percall-input-jev-l4/thresholds.json')['loso']}
    jev=[r for r in read(src('runs/20261026-1319-e06-percall-input-jev-l4/probe_scores.csv')) if r['analysis']=='loso' and r['row_id'] in ids]
    assert len(jev)==len(dev);methods['Jev']=[]
    for r in jev:
        ref=ids[r['row_id']];assert r['request_sha256']==ref['request_sha256'];m=float(r['score'])-ts[(r['seed'],r['fold'])];assert (m>0)==(r['alarm']=='True')
        methods['Jev'].append((m,int(ref['label']),not bool(meta[r['row_id']]['ever_public'])))
    panels.append(('gpt-oss: development','gpt_oss',methods))
    fresh=[r for r in read(src('runs/20261026-1302-e05-stream-confirm-score/probe_scores.csv')) if r['condition']=='recruiting' and int(r['reasoning_tokens'])>0]
    threshold=j('runs/20261026-1139-e05-stream-confirm/frozen_plan.json')['alarm']['threshold']
    methods={'Reasoning probe':[]}
    for r in fresh:
        m=float(r['max_score'])-threshold;assert (m>0)==(r['alarm']=='True')
        methods['Reasoning probe'].append((m,int(r['y_immediate']),r['ever_public']=='False'))
    assert len(fresh)==594
    panels.append(('gpt-oss: fresh episodes','gpt_oss',methods))
    configure();fig,axes=plt.subplots(1,3,figsize=(6.5,2.9),sharey=True);fig.subplots_adjust(left=.10,right=.98,bottom=.29,top=.82,wspace=.20)
    result=[];exports=[]
    for ax,(title,model,methods) in zip(axes,panels):
        for name,rows in methods.items():
            arr=np.array(rows);score=arr[:,0];pos=arr[:,1]==1;neg=arr[:,2]==1
            offsets=np.unique(np.r_[score,0]);offsets=np.r_[np.inf,offsets[::-1],-np.inf]
            px=np.sort(score[pos]);nx=np.sort(score[neg]);tpr=(len(px)-np.searchsorted(px,offsets,side='right'))/len(px);fpr=(len(nx)-np.searchsorted(nx,offsets,side='right'))/len(nx)
            opx=float(np.mean(score[neg]>0));opy=float(np.mean(score[pos]>0));style='--' if name=='Jev' else '-';color='#666666' if name=='Jev' else MODEL_COLORS[model]
            ax.plot(fpr,tpr,ls=style,color=color,lw=1.3);ax.plot(opx,opy,marker='s' if name=='Jev' else 'o',color=color,ms=5)
            result.append(dict(panel=title,detector=name,leaking_call_alarm=opy,refusing_call_alarm=opx,positive_rows=int(pos.sum()),refusing_rows=int(neg.sum()),seed_repetitions=3 if name=='Jev' or 'development' in title else 1))
            exports.extend(dict(panel=title,detector=name,threshold_offset=None if not np.isfinite(t) else float(t),leaks_caught=float(y),refusing_alarm=float(x)) for t,x,y in zip(offsets,fpr,tpr))
        ax.set_title(title+'\n'+('Reasoning probe' if 'fresh' in title and model=='gpt_oss' else 'Last-prompt probe vs Jev'),fontsize=9)
        ax.set(xlim=(0,1),ylim=(0,1.02),xticks=[0,.5,1],xlabel='Refusing calls alarmed');ax.grid(alpha=.15)
    axes[0].set_ylabel('Leaking calls caught')
    fig.legend(handles=[Line2D([],[],color='#333333',marker='o',label='Probe (dot: saved threshold)'),Line2D([],[],color='#666666',ls='--',marker='s',label='Jev (square: saved threshold)')],loc='lower center',ncol=2,frameon=False,fontsize=8)
    out=ROOT/'paper-arxiv/figures/fig7_alarm_tradeoffs';fig.savefig(out.with_suffix('.pdf'));fig.savefig(out.with_suffix('.png'),dpi=180)
    info=dict(method='Sweep a common additive offset from each saved control-calibrated threshold; strict >. Development and Jev fold thresholds retained. Three-seed rows give equal-weight mean alarm rates, not independent samples. Rates pool calls across scenarios and rounds, unlike the stratified ranking AUROC. Negatives are calls in refusing episodes; pre-leak negative calls from leaking episodes excluded.',sources=source,operating_points=result,gpt_fresh_jev='unavailable; probe-only panel',no_refits=True)
    assert result[-1]['positive_rows']==26 and result[-1]['refusing_rows']==490
    assert abs(result[-1]['leaking_call_alarm']-14/26)<1e-12 and abs(result[-1]['refusing_call_alarm']-12/490)<1e-12
    (a.output/'metrics.json').write_text(json.dumps(info,indent=2)+'\n');out.with_suffix('.json').write_text(json.dumps(info,indent=2)+'\n')
    with (a.output/'curves.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(exports[0]),lineterminator='\n');w.writeheader();w.writerows(exports)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
