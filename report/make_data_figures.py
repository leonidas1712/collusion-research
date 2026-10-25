"""Build Qwen paper figures and tables from saved results; no inference or refitting."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experiments/E05-probes'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from evaluate import ranking_summary, interval

SCENARIOS={
    'deploy-token-v2':'Deployment credential',
    'dispatch-integration-code':'Dispatch integration code',
    'handoff-exception-note':'Handoff exception note',
    'procurement-reserve-price':'Procurement reserve price',
    'service-capacity-figure':'Service capacity figure',
    'service-rollout-threshold':'Service rollout threshold',
}
METHODS=[('nested','Activation probe','#1d4ed8','probe'),
         ('llm detector L2','GPT-5-nano detector\n+ conversation','#059669','llm detector L2'),
         ('jev forecaster L3','Jev 1.14 forecaster\n+ full target context','#34d399','jev forecaster L3'),
         ('nano_probe','Probe + detector','#059669','llm detector L2 + probe'),
         ('jev_probe','Probe + forecaster','#34d399','jev forecaster L3 + probe')]
ACCESS=['Actions only','+ conversation','+ full target\ncontext']
ACCESS_COLORS=['#065f46','#059669','#34d399']


def load(path,sources):
    path=Path(path);raw=path.read_bytes()
    sources[str(path.relative_to(ROOT))]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    return json.loads(raw)


def csv_out(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)),lineterminator='\n')
        w.writeheader();w.writerows(rows)


def metric_row(key,m,**extra):
    lo,hi=m['within_round_ci95'];v=m['within_round_auc']
    if not 0<=lo<=v<=hi<=1:raise ValueError(f'Invalid AUROC interval: {key}')
    return dict(method=key,estimate=v,low=lo,high=hi,steps=m['rows'],positives=m['positives'],
                episodes=m.get('episodes'),**extra)


def figure2(out,main,confirm):
    rows=[]
    for label in ['eventual','A_hazard']:
        for key,name,color,ckey in METHODS:
            rows.append(metric_row(key,main[label]['loso']['methods'][key],label=label,
                                   cohort='all-data held-out scenario',display=name.replace('\n',' ')))
            if label=='A_hazard':
                c=confirm[label];lo,hi=c['ci95'][ckey]
                rows.append(dict(method=key,estimate=c['auc'][ckey],low=lo,high=hi,
                                 steps=c['rows'],positives=c['positives'],episodes=c['episodes'],
                                 label=label,cohort='new-episode confirmation',display=name.replace('\n',' ')))
    fig=plt.figure(figsize=(10.6,4.1),layout='constrained')
    outer=fig.add_gridspec(1,4,width_ratios=[2.6,1.6,2.6,1.6],wspace=.02)
    positions=np.array([0.,1.,2.,3.35,4.35])
    for panel,label in enumerate(['eventual','A_hazard']):
        ax=fig.add_subplot(outer[panel*2]);text_ax=fig.add_subplot(outer[panel*2+1],sharey=ax);text_ax.axis('off')
        ax.axvline(.5,color='#64748b',linestyle='--',linewidth=1)
        ax.axhline(2.7,color='#CBD5E1',linewidth=.7)
        for i,(key,name,color,_) in enumerate(METHODS):
            for cohort,offset,marker,fill in [('all-data held-out scenario',-.13,'o',color),
                                             ('new-episode confirmation',.13,'s','white')]:
                r=next((x for x in rows if x['label']==label and x['method']==key and x['cohort']==cohort),None)
                if r is None:continue
                y=positions[i]+offset
                ax.errorbar(r['estimate'],y,xerr=[[r['estimate']-r['low']],[r['high']-r['estimate']]],
                            fmt=marker,markersize=5.5,markerfacecolor=fill,markeredgecolor='#334155',
                            ecolor='#475569',elinewidth=1,capsize=2)
                text_ax.text(0,y,f"{r['estimate']:.3f} [{r['low']:.3f}, {r['high']:.3f}]",va='center',fontsize=8)
        ax.set(yticks=positions,yticklabels=[m[1]for m in METHODS] if panel==0 else [],
               xlim=(.4,.80),xticks=[.4,.5,.6,.7,.8],ylim=(5.0,-.65),xlabel='Within scenario × round AUROC')
        ax.set_title('(a) Eventual give-in' if panel==0 else '(b) Near-term give-in',loc='left',fontweight='bold')
        ax.tick_params(axis='y',length=0);ax.grid(axis='x',alpha=.15)
        text_ax.set_xlim(0,1)
    fig.legend(handles=[Line2D([],[],marker='o',color='#475569',markerfacecolor='#64748b',linestyle='none',label='Held-out scenario, all data'),
                        Line2D([],[],marker='s',color='#475569',markerfacecolor='white',linestyle='none',label='New-episode confirmation (near-term only)')],
               loc='outside lower center',ncol=2,frameon=False,fontsize=9)
    save(fig,out/'figure2_prediction')
    csv_out(out/'figure2_prediction.csv',rows)
    return rows


def monitor_figure(out,main,first):
    rows=[]
    for question in ['detector','forecaster']:
        for level in [1,2,3]:
            key=f'jev {question} L{level}'
            rows.append(metric_row(key,main['A_hazard']['loso']['methods'][key],panel='all data',question=question,level=level,model='Jev 1.14'))
    for model,name in [('jev','Jev 1.14'),('llm','GPT-5-nano'),('luna','Luna Decisions')]:
        for level in [1,2,3]:
            key=f'{model} forecaster L{level}'
            rows.append(metric_row(key,first[key]['ranking'],panel='first data batch',question='forecaster',level=level,model=name))
    fig,axes=plt.subplots(1,2,figsize=(7.6,3.7),layout='constrained',sharey=True)
    styles=[('detector','Detector','^','--'),('forecaster','Forecaster','o','-')]
    for panel,ax in enumerate(axes):
        selections=styles if panel==0 else [('Jev 1.14','Jev 1.14','o','-'),('GPT-5-nano','GPT-5-nano','s','--'),('Luna Decisions','Luna Decisions','D',':')]
        for j,(key,name,marker,line) in enumerate(selections):
            rr=[r for r in rows if r['panel']==('all data'if panel==0 else 'first data batch')
                and r['question'if panel==0 else 'model']==key]
            rr.sort(key=lambda r:r['level']);x=np.arange(3)+(j-(len(selections)-1)/2)*.045
            ax.plot(x,[r['estimate']for r in rr],color='#475569',linestyle=line,linewidth=1,label=name)
            for xx,r in zip(x,rr):
                ax.errorbar(xx,r['estimate'],yerr=[[r['estimate']-r['low']],[r['high']-r['estimate']]],fmt=marker,
                            markerfacecolor=ACCESS_COLORS[r['level']-1],markeredgecolor='#334155',markersize=5,
                            ecolor='#64748b',elinewidth=.9,capsize=2)
        ax.axhline(.5,color='#64748b',linestyle='--',linewidth=.8)
        ax.set(xticks=range(3),xticklabels=ACCESS,ylim=(.40,.75),xlim=(-.18,2.18))
        ax.set_title('(a) What to ask: Jev 1.14\nAll data' if panel==0 else '(b) What to see: forecasters\nFirst data batch',loc='left',fontweight='bold')
        ax.grid(axis='y',alpha=.15)
        # Shape identifies the monitor/question independently of access-level colour.
        handles=[Line2D([],[],color='#475569',linestyle=l,marker=m,markerfacecolor='white',label=n)for _,n,m,l in selections]
        ax.legend(handles=handles,fontsize=8,loc='upper left',frameon=False)
    axes[0].set_ylabel('Within scenario × round AUROC')
    save(fig,out/'figure_monitor_design');csv_out(out/'figure_monitor_design.csv',rows)
    return rows


def save(fig,path):
    fig.savefig(path.with_suffix('.pdf'),facecolor='white')
    fig.savefig(path.with_suffix('.png'),dpi=300,facecolor='white')
    plt.close(fig)


def display_ci(value,lo,hi,signed=False):
    fmt='+.3f' if signed else '.3f'
    return f'{value:{fmt}} [{lo:{fmt}}, {hi:{fmt}}]'


def table_files(out,stem,headers,body,widths,figsize):
    md=['| '+' | '.join(h.replace('\n','<br>') for h in headers)+' |','|'+'|'.join('---'for _ in headers)+'|']
    md+=['| '+' | '.join(map(str,row))+' |'for row in body]
    (out/(stem+'.md')).write_text('\n'.join(md)+'\n')
    fig,ax=plt.subplots(figsize=figsize,layout='constrained');ax.axis('off')
    table=ax.table(cellText=body,colLabels=headers,cellLoc='left',colLoc='left',loc='center',colWidths=widths)
    table.auto_set_font_size(False);table.set_fontsize(8.5);table.scale(1,1.7)
    for (row,col),cell in table.get_celld().items():
        cell.set_edgecolor('#CBD5E1');cell.set_linewidth(.4)
        if row==0:cell.set_facecolor('#E2E8F0');cell.set_text_props(weight='bold')
        elif row%2==0:cell.set_facecolor('#F8FAFC')
    save(fig,out/stem)


def table1(out,behaviour):
    selected=[r for r in behaviour if r['model']=='Qwen3-32B' and r['arm']=='plain' and r['scope']in('scenario','pooled_all')]
    by_key={(r['scenario'],r['condition']):r for r in selected};rows=[];body=[]
    for scenario in [*SCENARIOS,'ALL']:
        r=by_key[scenario,'recruiting'];c=by_key[scenario,'control'];a=by_key[scenario,'alone']
        name=SCENARIOS.get(scenario,'Total')
        rows.append(dict(scenario=scenario,display=name,recruiting_give_in=r['give_ins'],recruiting_valid=r['valid'],
                         recruiting_held=r['held'],recruiting_attempted=r['slots'],
                         recruiting_never_read=r['never_read'],recruiting_incomplete=r['incomplete'],recruiting_invalid_complete=r['invalid_complete'],
                         rate=r['give_in_rate'],ci_low=r['wilson_low'],ci_high=r['wilson_high'],
                         control_give_in=c['give_ins'],control_valid=c['valid'],control_attempted=c['slots'],
                         alone_give_in=a['give_ins'],alone_valid=a['valid'],alone_attempted=a['slots']))
        body.append([name,f"{r['give_ins']}/{r['valid']}",f"{100*r['give_in_rate']:.1f}% [{100*r['wilson_low']:.1f}, {100*r['wilson_high']:.1f}]",
                     str(r['slots']-r['valid']),f"{c['give_ins']}/{c['valid']}",f"{a['give_ins']}/{a['valid']}"])
    csv_out(out/'table1_behaviour.csv',rows)
    table_files(out,'table1_behaviour',['Scenario','Recruiting\ngive-ins / valid','Rate [95% CI]','Recruiting\nexcluded','Control\ngive-ins / valid','Alone\ngive-ins / valid'],body,[.25,.14,.22,.11,.14,.14],(9.8,3.0))
    return rows


def table2(out,main,confirm):
    rows=[];body=[]
    for analysis,name in [('loso','Held-out scenario'),('pooled','Pooled family CV')]:
        source=main['A_hazard'][analysis]
        for model,display in [('jev','Jev forecaster'),('nano','GPT-5-nano detector')]:
            b=source['methods'][model+'_base'];c=source['methods'][model+'_probe'];d=source['paired_differences'][model+'_probe_minus_'+model+'_base']['within_round']
            rows.append(dict(evaluation=name,monitor=display,base=b['within_round_auc'],base_low=b['within_round_ci95'][0],base_high=b['within_round_ci95'][1],
                             combined=c['within_round_auc'],combined_low=c['within_round_ci95'][0],combined_high=c['within_round_ci95'][1],
                             delta=d['difference'],delta_low=d['ci95'][0],delta_high=d['ci95'][1],steps=b['rows'],positives=b['positives'],episodes=b['episodes']))
    for key,display in [('jev forecaster L3','Jev forecaster'),('llm detector L2','GPT-5-nano detector')]:
        c=confirm['A_hazard'];base=key+' stacked';combined=key+' + probe';delta='gain from probe over '+key
        rows.append(dict(evaluation='New-episode confirmation',monitor=display,base=c['auc'][base],base_low=c['ci95'][base][0],base_high=c['ci95'][base][1],
                         combined=c['auc'][combined],combined_low=c['ci95'][combined][0],combined_high=c['ci95'][combined][1],
                         delta=c['diff'][delta],delta_low=c['ci95'][delta][0],delta_high=c['ci95'][delta][1],steps=c['rows'],positives=c['positives'],episodes=c['episodes']))
    for r in rows:
        body.append([r['evaluation'],r['monitor'],display_ci(r['base'],r['base_low'],r['base_high']),
                     display_ci(r['combined'],r['combined_low'],r['combined_high']),display_ci(r['delta'],r['delta_low'],r['delta_high'],True)])
    csv_out(out/'table2_combination.csv',rows)
    table_files(out,'table2_combination',['Evaluation','Monitor','Baseline [95% CI]','+ probe [95% CI]','Paired gain [95% CI]'],body,[.22,.19,.195,.195,.20],(11.0,2.6))
    return rows


def first_batch_contrasts(args,sources,first):
    rows=load_jsonl(ROOT/args.first_rows,sources)
    by_id={f"{r['episode']}::request_idx={r['request_idx']}":r for r in rows}
    labels={r['row_id']:r for r in load_jsonl(ROOT/args.first_labels,sources) if r['label_variant']=='A_hazard' and r['included']}
    scores=load(ROOT/args.first_monitor/'scores.json',sources)
    columns={}
    for r in scores:
        key=f"{r['monitor']} {r['prompt']} L{r['level']}"
        if r['prompt']=='forecaster' and r.get('score') is not None:
            columns.setdefault(key,{})[r['step_id']]=r['score']
    ids=sorted(labels)
    y=np.array([labels[i]['label']for i in ids]);rounds=np.array([by_id[i]['round']for i in ids])
    family=np.array([by_id[i]['family']for i in ids]);scenario=np.array([by_id[i]['scenario']for i in ids])
    result=[]
    for model in ['jev','llm','luna']:
        summaries={};boots={}
        for level in [1,2,3]:
            key=f'{model} forecaster L{level}'
            assert all(i in columns[key]for i in ids),key
            values=np.array([columns[key][i]for i in ids])
            summary,boot,_=ranking_summary(y[None,:],values[None,:],rounds,family,reps=args.bootstrap_reps,seed=20261024,stratum_key=scenario)
            assert abs(summary['within_round_auc']-first[key]['ranking']['within_round_auc'])<1e-10,key
            summaries[level]=summary;boots[level]=boot
        for a,b in [(2,1),(3,2)]:
            result.append(dict(model=model,contrast=f'access {a} minus {b}',difference=summaries[a]['within_round_auc']-summaries[b]['within_round_auc'],
                               ci95=interval(boots[a]-boots[b]),rows=len(ids),positives=int(y.sum()),episodes=len({by_id[i]['episode']for i in ids}),families=len(set(family)),bootstrap_reps=args.bootstrap_reps,bootstrap_seed=20261024))
    return result


def load_jsonl(path,sources):
    raw=path.read_bytes();sources[str(path.relative_to(ROOT))]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    return [json.loads(x)for x in raw.decode().splitlines()]


def main(args):
    out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);sources={}
    main_data=load(ROOT/args.main_run/'metrics.json',sources)
    first=load(ROOT/args.first_monitor/'metrics_main_A_hazard.json',sources)
    confirm=load(ROOT/args.confirmation_run/'confirm.json',sources)
    behaviour=load(ROOT/args.behaviour_run/'summary.json',sources)
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42,
                         'axes.spines.top':False,'axes.spines.right':False}):
        f2=figure2(out,main_data,confirm);mon=monitor_figure(out,main_data,first)
        t1=table1(out,behaviour);t2=table2(out,main_data,confirm)
    contrasts=first_batch_contrasts(args,sources,first)
    (out/'monitor_access_paired_contrasts.json').write_text(json.dumps(contrasts,indent=2)+'\n')
    csv_out(out/'monitor_access_paired_contrasts.csv',[{**r,'ci_low':r['ci95'][0],'ci_high':r['ci95'][1]}for r in contrasts])
    captions(out,f2,mon,t1,t2)
    outputs=[p for p in out.iterdir()if p.is_file()and p.stem in {'figure2_prediction','figure_monitor_design','table1_behaviour','table2_combination','monitor_access_paired_contrasts','data_figure_captions'}]
    manifest={'generated_utc':datetime.now(timezone.utc).isoformat(),'command':sys.argv,'api_calls':0,'gpu':False,
              'matplotlib':matplotlib.__version__,'numpy':np.__version__,'sources':sources,
              'bootstrap':{'reps':args.bootstrap_reps,'seed':20261024,'unit':'family','conditional_on_fitted_scores':True},
              'reserved_second_target':{'marker':'D','filled':False,'data_present':False},
              'outputs':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in outputs}}
    (out/'data_figures_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(out)


def captions(out,f2,mon,t1,t2):
    # Fixed manuscript claims must be reviewed if a replacement cohort changes counts.
    assert {(r['steps'],r['episodes']) for r in f2 if r['cohort']=='all-data held-out scenario'} == {(4697,241)}
    assert {(r['steps'],r['episodes']) for r in f2 if r['cohort']=='new-episode confirmation'} == {(1787,89)}
    assert (t1[-1]['recruiting_give_in'],t1[-1]['recruiting_valid'],t1[-1]['recruiting_attempted']) == (100,226,304)
    text='''# Figure and table captions

**Figure 2. Predicting eventual and near-term give-in on Qwen3-32B.** Points show within-scenario × round AUROC; whiskers are 95% family-bootstrap intervals and the dashed line is chance (0.5). Filled circles use all data with held-out-scenario probe evaluation: 4,697 recruiting steps from 241 episodes, with 998 eventual-positive steps or 250 near-term-positive steps. Text monitors are fixed and scored on those same steps. Hollow squares show the frozen-plan new-episode confirmation: 1,787 steps from 89 episodes, 82 near-term positives. Confirmation evaluated near-term labels only, so panel (a) has no hollow markers. The near-term label means the first target emission occurs this round or the next. Combined models also include round and log prompt length; their paired gains over matched baselines are in Table 2. Intervals use 1,000 family resamples and are conditional on fitted models; probe metrics average three training seeds. The eventual probe is compatible with chance, while the monitors are weakly above it; near-term performance is stronger. The all-data set includes the confirmation episodes, so filled and hollow estimates are not independent replications. No second-target result is plotted; space and a diamond marker are reserved for it.

**Monitor-design figure. What should a text monitor ask, and what should it see?** Within-scenario × round AUROC for the near-term label on Qwen3-32B, with 95% family-bootstrap intervals and a chance line at 0.5. Panel (a) compares Jev 1.14 detector and forecaster questions on all data (4,697 steps; 250 positives; 241 episodes). Panel (b) compares forecasters on the first data batch only (2,910 steps; 168 positives; 152 episodes), where all three monitor models were run at every access level. Actions-only input contains target tool calls and posted messages; conversation access adds peer messages; full target context also adds unposted target text and tool results. Marker shape and line style identify the monitor/question; green shades identify access levels. The panels use different cohorts and should not be compared as paired estimates. Jev benefits from conversation access; more access does not improve every monitor. Paired access contrasts are provided with the figure data.

**Table 1. Mixed recruitment outcomes across six Qwen3-32B scenarios.** Give-ins divided by valid episodes, with Wilson 95% intervals for recruiting rates. These are plain-peer episodes from the scale-up source runs used in the main analysis, including episodes with no replay-eligible step. A valid episode is complete, has accessed the protected value, and passes its scenario validity checks. The outcome follows the frozen main-analysis objective label where available and the same scorer rule elsewhere; accidental disclosures count. Of 304 recruiting attempts, 226 are valid, 37 never read the value, 30 are incomplete, and 11 are otherwise invalid. Control denominators exclude 9 invalid/incomplete attempts from 75; alone denominators exclude one unread attempt from 26. Excluded attempts do not count as held. The raw table includes every exclusion count. These are descriptive results conditional on the selected scenarios and batches, not randomized model comparisons.

**Table 2. Does the activation probe add to a text monitor?** Near-term within-scenario × round AUROC on Qwen3-32B. The baseline is a cross-fitted model of round, log prompt length and the monitor score; the combined model adds the probe score. Jev uses the forecaster question with full target context; GPT-5-nano uses the detector question with conversation access. Held-out-scenario and pooled family cross-validation use all data (4,697 steps; 250 positives; 241 episodes). The frozen-plan confirmation trains on the first batch and evaluates 89 new episodes (1,787 steps; 82 positives). All intervals are 95% family bootstraps; gains use paired resamples, not subtraction of marginal interval endpoints. The weaker-monitor gain is positive in pooled cross-validation and confirmation, but its held-out-scenario interval includes zero. No clear gain over Jev is established. The all-data and confirmation estimates overlap in their underlying episodes.
'''
    (out/'data_figure_captions.md').write_text(text)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,default=ROOT/'report/figures')
    p.add_argument('--main-run',type=Path,default=Path('runs/20261025-1456-e05-all-data-main'))
    p.add_argument('--first-monitor',type=Path,default=Path('runs/20261025-0147-e06-monitor-main'))
    p.add_argument('--confirmation-run',type=Path,default=Path('runs/20261025-1030-e06-confirmation'))
    p.add_argument('--behaviour-run',type=Path,default=Path('runs/20261025-1850-e03-behaviour-summary'))
    p.add_argument('--first-rows',type=Path,default=Path('runs/20261025-0337-e05-replay2-data/rows.jsonl'))
    p.add_argument('--first-labels',type=Path,default=Path('runs/20261025-0730-e05-near-term/labels.jsonl'))
    p.add_argument('--bootstrap-reps',type=int,default=1000)
    main(p.parse_args())
