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


def draw(ax, x, y, entry, model, kind='activation', horizontal=False, fresh=False, marker=None):
    if entry.get('value') is None:
        return False
    color = MODEL_COLORS[model]
    value = entry['value']
    ci = entry.get('ci')
    error = [[value-ci[0]], [ci[1]-value]] if ci else None
    ax.errorbar(value if horizontal else x, y if horizontal else value,
                xerr=error if horizontal else None, yerr=None if horizontal else error,
                marker=marker or DETECTOR_MARKERS[kind], color=color, markersize=8 if fresh else 6, markeredgewidth=1.5,
                markeredgecolor='#222222' if fresh else color,
                markerfacecolor=color if fresh or entry['status']=='confirmed' else 'white',
                capsize=2, linewidth=1, linestyle='none', zorder=3)
    return True


def save(fig, stem, rows, sha):
    fig.savefig(OUT/f'{stem}.pdf', bbox_inches=None, facecolor='white')
    fig.savefig(OUT/f'{stem}.png', bbox_inches=None, dpi=180, facecolor='white')
    fields=['panel','label','macro','key','value','ci_low','ci_high','status','dataset','evaluation','run']
    with (OUT/f'{stem}.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
        for panel,label,e in rows:
            ci=e.get('ci') or [None,None]
            w.writerow(dict(panel=panel,label=label,macro=e.get('macro'),key=e['key'],value=e.get('value'),
                            ci_low=ci[0],ci_high=ci[1],**{k:e.get(k) for k in fields[7:]}))
    (OUT/f'{stem}.json').write_text(json.dumps({
        'registry_sha256':sha,'width_inches':fig.get_figwidth(),'height_inches':fig.get_figheight(),
        'pending_macros':[e.get('macro') for _,_,e in rows if e.get('value') is None],
        'uncertainty':'source-registry confidence interval, when available; no invented intervals',
        'transformation':'none; values and intervals read directly from numbers.yaml',
        'marker_fill':('not applicable: bars' if stem=='fig3_percall' else ('filled fresh test; hollow development' if stem=='fig1_headline' else 'filled confirmed; hollow exploratory')),
    },indent=2)+'\n')
    plt.close(fig)


def headline(data,sha):
    fig,axes=plt.subplots(1,2,figsize=(6.5,3.65),sharey=True)
    fig.subplots_adjust(left=.10,right=.98,bottom=.29,top=.79,wspace=.13)
    rows=[]
    for ax,model,title in zip(axes,['qwen','gpt_oss'],['Qwen3-32B','gpt-oss-20b']):
        prefix='qwen' if model=='qwen' else 'gptoss'
        keys=[prefix+'EverProbe',prefix+'NearProbe',prefix+'CallProbe']
        values=[]
        for x,key in enumerate(keys):
            e=get(data,key);rows.append((title,['Ever','This/next round','This call'][x],e))
            position = x - .18 if x == 2 else x
            if draw(ax,position,None,e,model):values.append((position,e['value']))
        # Do not bridge an unobserved rung.
        for a,b in zip(values,values[1:]):
            if .8 <= b[0]-a[0] <= 1:ax.plot([a[0],b[0]],[a[1],b[1]],color=MODEL_COLORS[model],lw=.8,alpha=.6)
        fresh=[(2,'qwenFreshCallProbe','activation')] if model=='qwen' else [(2,'gptossFreshCallProbe','activation'),(2,'gptossFreshReasoning','activation')]
        for i,(x,key,kind) in enumerate(fresh):
            e=get(data,key);rows.append((title,'Fresh test: '+key,e))
            fresh_x=x+(0 if model=='gpt_oss' and i==0 else .18)
            draw(ax,fresh_x,None,e,model,kind,fresh=True,
                 marker='D' if key=='gptossFreshReasoning' else 'o')
            if e.get('value') is not None:
                ax.annotate('Fresh last-prompt' if key=='gptossFreshCallProbe' else ('Fresh reasoning' if model=='gpt_oss' else 'Fresh test'),
                            xy=(fresh_x,e['value']),xytext=(x-.50,.56 if model=='gpt_oss' and i==0 else .78),
                            ha='right' if model=='gpt_oss' else 'center',fontsize=8,
                            bbox=dict(facecolor='white',edgecolor='none',pad=1),arrowprops=dict(arrowstyle='-',color='#555555',lw=.7))
        ax.axhline(.5,color='#777777',ls='--',lw=.8)
        ax.set(xlim=(-.3,2.3),ylim=(0,1.03),xticks=[0,1,2],xticklabels=['Will it\never leak?','This round\nor next?','This call?'],title=title)
        ax.grid(axis='y',alpha=.15)
    axes[0].set_ylabel('AUROC')
    fig.suptitle('The nearer the act, the more predictable the leak',fontsize=11,y=.98)
    handles=[
        Line2D([],[],marker='o',mfc='white',color='#333333',ls='none',label='Last-prompt probe: development'),
        Line2D([],[],marker='o',color='#333333',ls='none',label='Last-prompt probe: fresh test'),
        Line2D([],[],marker='D',color=MODEL_COLORS['gpt_oss'],ls='none',label='Reasoning probe: fresh gpt-oss test')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,0),ncol=1,frameon=False,fontsize=9)
    save(fig,'fig1_headline',rows,sha)


def marker_legend(fig, kinds, fresh=False, y=.015):
    names={'activation':'Activation probe', 'text':'Text monitor', 'rule':'Rule', 'control':'Pre-ask control'}
    handles=[Line2D([],[],marker=DETECTOR_MARKERS[k],mfc='#555555' if fresh else 'white',
                    color='#555555',ls='none',label=names[k]) for k in kinds]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,y),
               ncol=len(kinds),frameon=False,fontsize=9)


def forest(data,sha,stem,title,panels):
    compact=stem=='fig_round_confirmation'
    fig,axes=plt.subplots(1,len(panels),figsize=(3.9,3.0) if compact else (6.5,3.8),squeeze=False)
    fig.subplots_adjust(left=.06,right=.97,bottom=.38 if compact else .31,top=.77,wspace=.40)
    rows=[]
    for ax,(model,panel,items) in zip(axes[0],panels):
        ax.set_title(panel,fontsize=10)
        for y,(label,key,kind) in enumerate(items):
            e=get(data,key);rows.append((panel,label,e))
            draw(ax,None,y,e,model,kind,horizontal=True)
            ax.text(.02,y-.30,label,va='center',fontsize=10 if compact else 9,
                    bbox=dict(facecolor='white',edgecolor='none',pad=1.5),
                    transform=ax.get_yaxis_transform())
        ax.set(xlim=(0,1.03),ylim=(len(items)-.4,-.8),yticks=[],xlabel='AUROC',xticks=[0,.5,1])
        ax.axvline(.5,color='#777777',ls='--',lw=.8)
        if not compact:
            ax.text(.5,.02,'chance',ha='center',va='bottom',fontsize=9,
                    bbox=dict(facecolor='white',edgecolor='none',pad=1),transform=ax.get_xaxis_transform())
        ax.spines['left'].set_visible(False)
    fig.suptitle(title,fontsize=11,y=.98)
    kinds=list(dict.fromkeys(kind for _,_,items in panels for _,_,kind in items))
    marker_legend(fig,kinds,fresh=compact)
    fig.text(.5,.13,'Whiskers: 95% CI; dashed line: chance',ha='center',fontsize=9)
    save(fig,stem,rows,sha)


def shortcuts(data,sha):
    fig,ax=plt.subplots(figsize=(6.5,4.2))
    fig.subplots_adjust(left=.43,right=.97,bottom=.28,top=.84)
    items=[
        ('Last-prompt probe','gptossCallProbe','activation',0),
        ('Reasoning probe','gptossCallReasoning','activation',1),
        ('Call reads the protected file','gptossReadStep','rule',2),
        ('Keywords in reasoning','gptossKeyword','rule',3),
        ('Before the peer asks\n(other calls)','gptossPlacebo','control',4),
        ('Probe reading only incoming\nmessages and tool results','gptossIncomingProbe','activation',6)]
    rows=[]
    for label,key,kind,y in items:
        e=get(data,key);rows.append(('gpt-oss-20b',label,e))
        draw(ax,None,y,e,'gpt_oss',kind,horizontal=True)
    ax.set(xlim=(0,1.03),ylim=(6.7,-.7),yticks=[i[3] for i in items],
           yticklabels=[i[0] for i in items],xlabel='AUROC',xticks=[0,.5,1])
    ax.tick_params(axis='y',length=0,labelsize=9)
    ax.axvline(.5,color='#777777',ls='-',lw=.8)
    reference=get(data,'gptossCallProbe').get('value')
    if reference is not None:ax.axvline(reference,color=MODEL_COLORS['gpt_oss'],ls=(0,(6,3)),lw=1)
    ax.axhline(5,color='#bbbbbb',lw=.6)
    ax.spines['left'].set_visible(False)
    fig.suptitle('gpt-oss-20b: what can explain the signal?',fontsize=11,y=.98)
    lines=[Line2D([],[],color='#777777',lw=.8,label='Chance'),
           Line2D([],[],color=MODEL_COLORS['gpt_oss'],ls=(0,(6,3)),label='Last-prompt probe')]
    fig.legend(handles=lines,loc='lower center',bbox_to_anchor=(.5,.12),ncol=2,frameon=False,fontsize=9)
    marker_legend(fig,['activation','rule','control'],y=.045)
    fig.text(.5,.005,'Whiskers: 95% CI',ha='center',fontsize=9)
    save(fig,'fig4_shortcuts',rows,sha)


def percall(data, sha):
    panels = [
        ('qwen', 'Qwen3-32B', [
            ('Last-prompt probe', 'qwenCallProbe'),
            ('Trained text: latest input', 'qwenTextLatest'),
            ('Zero-shot Jev', 'qwenCallJev')]),
        ('gpt_oss', 'gpt-oss-20b', [
            ('Last-prompt probe', 'gptossCallProbe'),
            ('Reasoning probe', 'gptossCallReasoning'),
            ('Trained text: full input', 'gptossTextFull'),
            ('Zero-shot Jev (with reasoning)', 'gptossCallJev')])]
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 4.35), sharex=True)
    fig.subplots_adjust(left=.07, right=.97, bottom=.18, top=.73, wspace=.22)
    rows = []
    for ax, (model, title, items) in zip(axes, panels):
        ax.set_title(title, fontsize=10)
        for y, (label, key) in enumerate(items):
            e = get(data, key)
            assert e.get('value') is not None, key
            rows.append((title, label, e))
            value, ci = e['value'], e.get('ci')
            ax.barh(y, value, height=.30, color=MODEL_COLORS[model], alpha=.55)
            if ci:
                ax.errorbar(value, y, xerr=[[value-ci[0]], [ci[1]-value]],
                            fmt='none', ecolor='#222222', capsize=3, linewidth=1)
            ax.text(0, y-.31, label, fontsize=9, va='center',
                    bbox=dict(facecolor='white', edgecolor='none', pad=1))
        ax.axvline(.5, color='#777777', ls='--', lw=.8, zorder=0)
        ax.set(xlim=(0,1.03), ylim=(3.5,-.75), yticks=[], xticks=[0,.5,1], xlabel='AUROC')
        ax.spines['left'].set_visible(False)
    fig.suptitle('A probe picks out the call that leaks; a zero-shot monitor\ndoes not, and a trained text classifier comes close.', fontsize=11, y=.98)
    fig.text(.5,.025,'Development episodes; whiskers: 95% CI; dashed line: chance',ha='center',fontsize=9)
    save(fig, 'fig3_percall', rows, sha)


def main():
    configure();data,sha=registry();OUT.mkdir(exist_ok=True)
    headline(data,sha)
    forest(data,sha,'fig_round_confirmation','Qwen test on fresh episodes', [('qwen','Will it leak this round or next?', [('Probe','qwenFreshNearProbe','activation'),('Jev','qwenFreshNearJev','text')])])
    percall(data,sha)
    shortcuts(data,sha)


if __name__=='__main__':main()
