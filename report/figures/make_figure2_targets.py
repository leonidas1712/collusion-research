"""Render Figure 2 from saved estimates; no inference, fitting or manuscript edits."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
METHODS = [
    ('nested', 'Activation probe'),
    ('llm detector L2', 'GPT-5-nano detector\n+ conversation'),
    ('jev forecaster L3', 'Jev forecaster\n+ everything the target saw'),
    ('nano_probe', 'Probe + detector'),
    ('jev_probe', 'Probe + forecaster'),
]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir', type=Path, default=ROOT/'report/figures')
    p.add_argument('--qwen', type=Path, default=ROOT/'runs/20261025-1456-e05-all-data-main')
    p.add_argument('--confirmation', type=Path, default=ROOT/'runs/20261025-1030-e06-confirmation')
    p.add_argument('--gpt-probe', type=Path, default=ROOT/'runs/20261026-0138-e05-gpt-oss-main')
    p.add_argument('--gpt-monitor', type=Path, default=ROOT/'runs/20261026-0108-e06-monitor-score-gpt-oss')
    p.add_argument('--gpt-monitor-cache', type=Path, default=ROOT/'runs/20261025-2330-e06-monitor-main-gpt-oss')
    p.add_argument('--refresh-from-runs', action='store_true', help='Re-audit full local exports instead of using the committed compact input.')
    p.add_argument('--input', type=Path, default=ROOT/'report/figures/figure2_targets_input.json')
    a = p.parse_args(); sources = {}; rows = []
    def read(path):
        data = path.read_bytes()
        sources[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
        return data.decode()
    if a.refresh_from_runs:
        q = json.loads(read(a.qwen/'metrics.json'))
        c = json.loads(read(a.confirmation/'confirm.json'))
        gp = json.loads(read(a.gpt_probe/'metrics.json'))
        gm = json.loads(read(a.gpt_monitor/'metrics.json'))
        scores = list(csv.DictReader(read(a.gpt_probe/'probe_scores.csv').splitlines()))
        ids = {r['row_id'] for r in scores if r['window']=='post_ask' and r['analysis']=='loso'
               and r['method']=='nested' and r['label_variant']=='eventual' and r['condition']=='recruiting'}
        steps = [json.loads(x) for x in read(a.gpt_monitor_cache/'steps.jsonl').splitlines()]
        monitor_ids = {r['row_id'] for r in steps if r['condition']=='recruiting'}
        assert ids == monitor_ids and len(ids)==2059
        episode_count = len({r['episode'] for r in steps if r['row_id'] in ids})
        assert episode_count == 238
        cached = json.loads(read(a.gpt_monitor_cache/'scores.json'))
        for monitor, prompt, level in [('llm','detector',2),('jev','forecaster',3)]:
            covered = {r['step_id'] for r in cached if r['monitor']==monitor and r['prompt']==prompt
                       and r['level']==level and r.get('score') is not None}
            assert ids <= covered, (monitor,prompt,level)
        def add(model, label, method, cohort, value, ci, n, positives, episodes):
            assert 0 <= ci[0] <= value <= ci[1] <= 1
            rows.append(dict(model=model,label=label,method=method,cohort=cohort,estimate=value,
                             low=ci[0],high=ci[1],steps=n,positives=positives,episodes=episodes))
        for label in ['eventual','A_hazard']:
            for method,_ in METHODS:
                m=q[label]['loso']['methods'][method]
                add('Qwen3-32B',label,method,'held-out scenario',m['within_round_auc'],m['within_round_ci95'],m['rows'],m['positives'],m['episodes'])
                if label=='A_hazard':
                    key={'nested':'probe','nano_probe':'llm detector L2 + probe','jev_probe':'jev forecaster L3 + probe'}.get(method,method)
                    m=c[label]
                    add('Qwen3-32B',label,method,'confirmation',m['auc'][key],m['ci95'][key],m['rows'],m['positives'],m['episodes'])
            m=next(r for r in gp if r['window']=='post_ask' and r['variant']==label and r['mode']=='loso'
                   and r['method']=='nested' and r['sensitivity']=='primary')
            add('gpt-oss-20b',label,'nested','held-out scenario',m['within_round_auc'],m['within_round_ci95'],m['rows'],m['positives'],m['episodes'])
            for key in ['llm detector L2','jev forecaster L3']:
                name,prompt,level=key.split();m=gm[label][f'{name}:{prompt}:{level}']
                assert m['rows']==2059 and m['missing']==0
                add('gpt-oss-20b',label,key,'fixed monitor',m['within_round_auc'],m['within_round_family_ci95'],m['rows'],m['positive_rows'],episode_count)
    else:
        compact = json.loads(read(a.input))
        rows = compact['rows']
        assert compact['coverage_audit']['probe_monitor_rows_identical']
        assert len(rows) == 21
        ids = range(compact['coverage_audit']['rows'])
        episode_count = compact['coverage_audit']['episodes']
    out=a.output_dir;out.mkdir(parents=True,exist_ok=True)
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':8,'pdf.fonttype':42,
                         'axes.spines.top':False,'axes.spines.right':False}):
        fig,axs=plt.subplots(1,3,figsize=(6.7,3.65),sharey=True)
        fig.subplots_adjust(left=.285,right=.985,top=.84,bottom=.25,wspace=.19)
        pos=[0,1,2,3.35,4.35]
        for panel,ax in enumerate(axs):
            ax.axvline(.5,ls='--',lw=.8,color='#64748b')
            ax.axhline(2.7,lw=.6,color='#CBD5E1')
            selections = ([('eventual','held-out scenario','o',0,'#334155')] if panel==0 else
                [('A_hazard','held-out scenario','o',-.13,'#334155'),('A_hazard','confirmation','s',.13,'white')] if panel==1 else
                [('eventual',None,'D',-.14,'white'),('A_hazard',None,'^',.14,'#087f8c')])
            model='gpt-oss-20b' if panel==2 else 'Qwen3-32B'
            for i,(method,_) in enumerate(METHODS):
                for label,cohort,marker,offset,fill in selections:
                    rr=[r for r in rows if r['model']==model and r['label']==label and r['method']==method and (cohort is None or r['cohort']==cohort)]
                    if not rr:continue
                    r,=rr
                    ax.errorbar(r['estimate'],pos[i]+offset,xerr=[[r['estimate']-r['low']],[r['high']-r['estimate']]],
                                fmt=marker,ms=4.5,mfc=fill,mec='#334155',ecolor='#475569',elinewidth=.8,capsize=2)
                    ax.text(r['high']+.012,pos[i]+offset,f"{r['estimate']:.2f}",
                            ha='left',va='center',fontsize=6.3)
            ax.set(xlim=(.4,.86),xticks=[.4,.5,.6,.7,.8],ylim=(4.95,-.6),yticks=pos)
            ax.tick_params(axis='y',length=0);ax.tick_params(axis='x',labelsize=7)
            ax.grid(axis='x',alpha=.15)
            ax.set_title(['(a) Qwen3-32B\nEventual','(b) Qwen3-32B\nNear-term','(c) gpt-oss-20b\nBoth horizons'][panel],fontsize=8.5,fontweight='bold')
        axs[0].set_yticklabels([name for _,name in METHODS],fontsize=7.5)
        for y in pos[3:]:axs[2].text(.6,y,'Not available',ha='center',va='center',fontsize=6.7,color='#64748b')
        fig.text(.64,.15,'Within scenario × round AUROC (chance = 0.5)',ha='center',fontsize=8)
        handles=[Line2D([],[],ls='',marker=m,mfc=f,mec='#334155',label=t,ms=4.5) for m,f,t in
                 [('o','#334155','Qwen: held-out scenario'),('s','white','Qwen: confirmation'),
                  ('D','white','gpt-oss: eventual'),('^','#087f8c','gpt-oss: near-term')]]
        fig.legend(handles=handles,loc='lower center',ncol=2,fontsize=7,frameon=False,bbox_to_anchor=(.55,0))
        for suffix in ['pdf','png']:fig.savefig(out/f'figure2_prediction.{suffix}',dpi=300,facecolor='white')
        plt.close(fig)
    with (out/'figure2_prediction.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    caption='''**Figure 2. Near-term prediction is stronger on Qwen3-32B; the corresponding gpt-oss estimates remain close to chance.** Within-scenario × round AUROC with 95% family-bootstrap intervals (1,000 resamples). Qwen uses 4,697 recruiting steps from 241 episodes (998 eventual-positive; 250 near-term-positive); hollow squares show confirmation on 1,787 steps from 89 episodes (82 near-term-positive), which are also included in the full Qwen cohort. The two Qwen estimates are therefore not independent. The gpt-oss panel uses 2,059 post-ask steps from 238 episodes (169 eventual-positive; 148 near-term-positive), with diamonds for eventual and triangles for near-term outcomes. Probes use inner-selected layers and held-out-scenario evaluation; fixed monitors use the same eligible steps within each target. Monitor identities and access levels match across targets; target-private reasoning is omitted from the shown monitors. Near-term means the first public emission occurs this round or the next, with channel publication defining a positive episode. Target cohorts and collection protocols differ; markers are not paired across targets. Missing gpt-oss combination estimates are labelled, not scored as zero.\n'''
    (out/'figure2_prediction_caption.md').write_text(caption)
    caption_collection = out/'data_figure_captions.md'
    if caption_collection.exists():
        old = caption_collection.read_text()
        start = old.index('**Figure 2.')
        end = old.index('**Monitor-design figure.')
        caption_collection.write_text(old[:start] + caption + '\n' + old[end:])
    (out/'figure2_prediction_alt.txt').write_text('Three aligned forest plots on AUROC 0.4 to 0.8, with chance at 0.5. Qwen eventual probe is 0.523 and near-term probe 0.579; its near-term Jev forecaster is 0.650. On gpt-oss the probe is 0.511 eventual and 0.528 near-term; Jev is 0.546 and 0.558. Confidence intervals overlap chance for both gpt-oss probe horizons. GPT-5-nano is 0.543 and 0.548. Qwen confirmation and combinations are also shown; gpt-oss combinations are unavailable.\n')
    (out/'figure2_targets_manifest.json').write_text(json.dumps({'sources':sources,'api_calls':0,'fits':0,
        'gpt_probe_monitor_rows_identical':True,'gpt_rows':len(ids),'gpt_episodes':episode_count,
        'dimensions_inches':[6.7,3.65],'png_dpi':300,'script':'report/figures/make_figure2_targets.py',
        'outputs':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.glob('figure2_prediction.*')}},indent=2)+'\n')
    print(json.dumps([r for r in rows if r['model']=='gpt-oss-20b'],indent=2))

if __name__=='__main__':main()
