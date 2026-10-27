"""Render the gated, fixed-selection saved-score trajectory analysis."""
import argparse,json,hashlib
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.lines import Line2D
from style import configure,MODEL_COLORS,end_labels
PAPER=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);a=p.parse_args()
    d=json.loads(a.analysis.read_text());assert d['include_figure'],'Aggregate gate failed; do not plot examples'
    configure();fig,axes=plt.subplots(2,2,figsize=(6.5,4.9),sharey=True)
    fig.subplots_adjust(left=.15,right=.98,top=.89,bottom=.19,wspace=.18,hspace=.7)
    for col,model in enumerate(['qwen','gpt_oss']):
        ax=axes[0,col];color=MODEL_COLORS[model];ends=[]
        for s in [v for v in d['summaries'] if v['model']==model]:
            rows=s['aggregate'];x=[r['offset'] for r in rows];y=[100*r['median'] for r in rows]
            fresh=s['cohort']=='fresh';assert x[-1]==0;ends.append(('test' if fresh else 'dev.',y[-1]))
            ax.plot(x,y,color=color,ls='-' if fresh else '--',marker='o' if fresh else None,ms=3,lw=1.3)
            if fresh:ax.fill_between(x,[100*r['q25'] for r in rows],[100*r['q75'] for r in rows],color=color,alpha=.12)
        ax.set_title(('Qwen3-32B' if model=='qwen' else 'gpt-oss-20b')+': all leaking episodes',fontsize=9)
        ax.set(xticks=[-10,-5,0],xlabel='Scored calls before leak',ylim=(0,103));end_labels(ax,ends,color,right=4.2)
        example=next(e for e in d['examples'] if e['model']==model);rows=example['calls'];ax=axes[1,col]
        ax.plot([r['offset'] for r in rows],[100*r['score'] for r in rows],color=color,marker='o',ms=3,lw=1.2)
        ax.set_title('Median-length test episode',fontsize=9)
        ax.set(xlabel='Scored calls before leak',ylim=(0,103));assert rows[-1]['offset']==0
        end_labels(ax,[('',100*rows[-1]['score'])],color,right=.22*(1-rows[0]['offset']))
        for ax in axes[:,col]:
            # Ticks and axis line cover the data only; the space right of 0 holds the end labels.
            first=min(l.get_xdata()[0] for l in ax.get_lines() if len(l.get_xdata())>1)
            ax.set_xticks([t for t in MaxNLocator(integer=True,nbins=4).tick_values(first,0) if first<=t<=0])
            ax.spines['bottom'].set_bounds(first,0)
            ax.axvline(0,color='#777777',lw=.8,ls=':');ax.grid(axis='y',alpha=.15)
    for ax in axes[:,0]:ax.set_ylabel("Probe score\n(percentile among this\nmodel's scored calls)",fontsize=8.5)
    fig.legend(handles=[Line2D([],[],color='#444444',ls='--',label='Development median'),Line2D([],[],color='#444444',ls='-',label='Test median (band: middle 50%)')],loc='lower center',ncol=2,frameon=False,fontsize=9,bbox_to_anchor=(.5,0))
    out=PAPER/'figures/fig6_trajectories'
    fig.savefig(out.with_suffix('.pdf'));fig.savefig(out.with_suffix('.png'),dpi=180)
    out.with_suffix('.json').write_text(json.dumps(dict(analysis=str(a.analysis),analysis_sha256=hashlib.sha256(a.analysis.read_bytes()).hexdigest(),examples=d['examples'],plan=d['plan']),indent=2)+'\n')
if __name__=='__main__':main()
