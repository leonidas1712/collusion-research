"""Generate registry-backed figures; pending estimates are never plotted as data."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from style import configure, MODEL_COLORS, DETECTOR_MARKERS

PAPER = Path(__file__).resolve().parents[2]
OUT = PAPER / 'figures'


def registry():
    raw = (PAPER / 'numbers.yaml').read_bytes()
    entries = json.loads(raw)['numbers']
    return {e['macro']: dict(e, key=k) for k, e in entries.items()}, hashlib.sha256(raw).hexdigest()


def get(data, macro):
    return data.get(macro, dict(macro=macro, value=None, status='pending', key='unregistered'))


def draw(ax, x, y, entry, model, kind='activation', horizontal=False, fresh=False):
    if entry.get('value') is None:
        return False
    color = MODEL_COLORS[model]
    value = entry['value']
    ci = entry.get('ci')
    error = [[value-ci[0]], [ci[1]-value]] if ci else None
    ax.errorbar(value if horizontal else x, y if horizontal else value,
                xerr=error if horizontal else None, yerr=None if horizontal else error,
                marker=DETECTOR_MARKERS[kind], color=color, markersize=6,
                markerfacecolor=color if fresh or entry['status']=='confirmed' else 'white',
                capsize=2, linewidth=1, linestyle='none', zorder=3)
    return True


def save(fig, stem, rows, sha):
    fig.savefig(OUT/f'{stem}.pdf', bbox_inches=None, facecolor='white')
    fig.savefig(OUT/f'{stem}.png', bbox_inches=None, dpi=180, facecolor='white')
    fields=['panel','label','macro','key','value','ci_low','ci_high','status','dataset','evaluation','run']
    with (OUT/f'{stem}.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for panel,label,e in rows:
            ci=e.get('ci') or [None,None]
            w.writerow(dict(panel=panel,label=label,macro=e.get('macro'),key=e['key'],value=e.get('value'),
                            ci_low=ci[0],ci_high=ci[1],**{k:e.get(k) for k in fields[7:]}))
    (OUT/f'{stem}.json').write_text(json.dumps({
        'registry_sha256':sha,'width_inches':fig.get_figwidth(),'height_inches':fig.get_figheight(),
        'pending_macros':[e.get('macro') for _,_,e in rows if e.get('value') is None],
        'uncertainty':'source-registry confidence interval, when available; no invented intervals',
        'transformation':'none; values and intervals read directly from numbers.yaml',
        'marker_fill':('filled fresh test; hollow development' if stem=='fig1_headline' else 'filled confirmed; hollow exploratory'),
    },indent=2)+'\n')
    plt.close(fig)


def headline(data,sha):
    fig,axes=plt.subplots(1,2,figsize=(6.5,3.65),sharey=True)
    fig.subplots_adjust(left=.10,right=.98,bottom=.34,top=.79,wspace=.13)
    rows=[]
    for ax,model,title in zip(axes,['qwen','gpt_oss'],['Qwen3-32B','gpt-oss-20b']):
        prefix='qwen' if model=='qwen' else 'gptoss'
        keys=[prefix+'EverProbe',prefix+'NearProbe',prefix+'CallProbe']
        values=[]
        for x,key in enumerate(keys):
            e=get(data,key);rows.append((title,['Ever','This/next round','This call'][x],e))
            if draw(ax,x,None,e,model):values.append((x,e['value']))
            else:ax.text(x,.11,'pending',ha='center',fontsize=8,color='#666666')
        # Do not bridge an unobserved rung.
        for a,b in zip(values,values[1:]):
            if b[0]==a[0]+1:ax.plot([a[0],b[0]],[a[1],b[1]],color=MODEL_COLORS[model],lw=.8,alpha=.6)
        fresh=[(2,'qwenFreshCallProbe','activation')] if model=='qwen' else [(2,'gptossFreshReasoning','activation')]
        for i,(x,key,kind) in enumerate(fresh):
            e=get(data,key);rows.append((title,'Fresh test: '+key,e))
            draw(ax,x+(.08 if kind=='text' else -.08),None,e,model,kind,fresh=True)
        ax.axhline(.5,color='#777777',ls='--',lw=.8)
        ax.set(xlim=(-.3,2.3),ylim=(0,1.03),xticks=[0,1,2],xticklabels=['Ever','This/next\nround','This call'],title=title)
        ax.grid(axis='y',alpha=.15)
    axes[0].set_ylabel('AUROC')
    fig.suptitle('The nearer the act, the more predictable the leak',fontsize=11,y=.98)
    handles=[Line2D([],[],marker='o',mfc='white',color='#333333',ls='none',label='Development'),Line2D([],[],marker='o',color='#333333',ls='none',label='Fresh test')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.005),ncol=2,frameon=False,fontsize=8)
    fig.text(.5,.13,'Fresh Qwen call test: out-of-sample, not preregistered.\nFresh gpt-oss call test: frozen reasoning probe.',ha='center',fontsize=7.5,color='#444444')
    save(fig,'fig1_headline',rows,sha)


def forest(data,sha,stem,title,panels):
    fig,axes=plt.subplots(1,len(panels),figsize=(6.5,3.5),squeeze=False)
    fig.subplots_adjust(left=.03,right=.98,bottom=.25,top=.79,wspace=.40)
    rows=[]
    for ax,(model,panel,items) in zip(axes[0],panels):
        ax.set_title(panel,fontsize=10)
        for y,(label,key,kind) in enumerate(items):
            e=get(data,key);rows.append((panel,label,e))
            if not draw(ax,None,y,e,model,kind,horizontal=True):
                ax.text(.99,y,'pending',ha='right',va='center',fontsize=8,color='#777777')
            ax.text(.02,y-.30,label,va='center',fontsize=8,transform=ax.get_yaxis_transform())
        ax.set(xlim=(0,1.03),ylim=(len(items)-.4,-.8),yticks=[],xlabel='AUROC',xticks=[0,.5,1])
        ax.axvline(.5,color='#777777',ls='--',lw=.8)
        ax.spines['left'].set_visible(False)
    fig.suptitle(title,fontsize=11,y=.98)
    note = ('Filled markers: frozen fresh-test results.' if all(e.get('status')=='confirmed' for _,_,e in rows) else 'Hollow markers: development results.')
    fig.text(.5,.035,note+' Whiskers: source confidence intervals.',ha='center',fontsize=8)
    save(fig,stem,rows,sha)


def main():
    configure();data,sha=registry();OUT.mkdir(exist_ok=True)
    headline(data,sha)
    forest(data,sha,'fig_round_confirmation','Frozen round-level confirmation', [('qwen','Qwen3-32B: original frozen label/window', [('Probe','qwenFreshNearProbe','activation'),('Jev','qwenFreshNearJev','text')])])
    forest(data,sha,'fig3_percall','Which call will leak?',[
        ('qwen','Qwen3-32B',[('Last-prompt probe','qwenCallProbe','activation'),('Jev: conversation + tool results','qwenCallJev','text')]),
        ('gpt_oss','gpt-oss-20b',[('Last-prompt probe','gptossCallProbe','activation'),('Reasoning probe','gptossCallReasoning','activation'),('Jev: including same-turn reasoning','gptossCallJev','text')])])
    forest(data,sha,'fig4_shortcuts','What can explain the signal?',[
        ('gpt_oss','gpt-oss-20b',[('Last-prompt probe','gptossCallProbe','activation'),('Reasoning probe','gptossCallReasoning','activation'),('Protected-read flag','gptossReadStep','rule')]),
        ('gpt_oss','Additional checks',[('Keywords on reasoning','gptossKeyword','rule'),('Pre-ask placebo (different calls)','gptossPlacebo','control'),('Incoming-only probe (one seed)','gptossIncomingProbe','activation')])])


if __name__=='__main__':main()
