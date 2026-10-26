"""Render the gated, fixed-selection saved-score trajectory analysis."""
import argparse,json,hashlib
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.lines import Line2D
from style import configure,MODEL_COLORS
PAPER=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);a=p.parse_args()
    d=json.loads(a.analysis.read_text());assert d['include_figure'],'Aggregate gate failed; do not plot examples'
    configure();fig,axes=plt.subplots(2,2,figsize=(6.5,4.9),sharey=True)
    fig.subplots_adjust(left=.12,right=.98,top=.89,bottom=.19,wspace=.18,hspace=.7)
    for col,model in enumerate(['qwen','gpt_oss']):
        ax=axes[0,col];color=MODEL_COLORS[model]
        for s in [v for v in d['summaries'] if v['model']==model]:
            rows=s['aggregate'];x=[r['offset'] for r in rows];y=[100*r['median'] for r in rows]
            fresh=s['cohort']=='fresh'
            ax.plot(x,y,color=color,ls='-' if fresh else '--',marker='o' if fresh else None,ms=3,lw=1.3)
            if fresh:ax.fill_between(x,[100*r['q25'] for r in rows],[100*r['q75'] for r in rows],color=color,alpha=.12)
        ax.set_title(('Qwen3-32B' if model=='qwen' else 'gpt-oss-20b')+': all leaking episodes',fontsize=9)
        ax.set(xticks=[-10,-5,0],xlabel='Scored calls before leak',ylim=(0,103))
        example=next(e for e in d['examples'] if e['model']==model);rows=example['calls'];ax=axes[1,col]
        ax.plot([r['offset'] for r in rows],[100*r['score'] for r in rows],color=color,marker='o',ms=3,lw=1.2)
        ax.set_title('Median-length fresh episode',fontsize=9)
        ax.set(xlabel='Scored calls before leak',ylim=(0,103))
        for ax in axes[:,col]:
            ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
            ax.axvline(0,color='#777777',lw=.8,ls=':');ax.grid(axis='y',alpha=.15)
    for ax in axes[:,0]:ax.set_ylabel('Score percentile')
    fig.legend(handles=[Line2D([],[],color='#444444',ls='--',label='Development median'),Line2D([],[],color='#444444',ls='-',label='Fresh median (band: middle 50%)')],loc='lower center',ncol=2,frameon=False,fontsize=9,bbox_to_anchor=(.5,0))
    out=PAPER/'figures/fig6_trajectories'
    fig.savefig(out.with_suffix('.pdf'));fig.savefig(out.with_suffix('.png'),dpi=180)
    out.with_suffix('.json').write_text(json.dumps(dict(analysis=str(a.analysis),analysis_sha256=hashlib.sha256(a.analysis.read_bytes()).hexdigest(),examples=d['examples'],plan=d['plan']),indent=2)+'\n')
if __name__=='__main__':main()
