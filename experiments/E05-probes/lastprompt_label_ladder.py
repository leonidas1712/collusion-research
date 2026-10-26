"""Post hoc matched gpt-oss last-prompt round/eventual any-public labels."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits
from lastprompt_percall import load, run_fit, SEEDS, STREAM, DATA, FITS, ROOT
from reasoning_stream_report import stream_metrics
from collusion.runs import start_run, write_json_atomic


def summarize(out,rows,x):
    results={};exports=[];source=np.array([r['index'] for r in rows])
    for label in ['round_any','eventual_any']:
      for mode in ['loso','pooled']:
        files=sorted((out/'matched'/label/mode).glob('s*-f*/fit.json'));assert len(files)==(18 if mode=='loso' else 15)
        scores=np.full((3,len(rows)),np.nan);baseline=scores.copy();fold=np.full(scores.shape,-1);alarm=np.zeros(scores.shape,bool)
        for path in files:
            f=json.loads(path.read_text());seed=f['plan']['seed'];si=SEEDS.index(seed);fo=f['plan']['fold'];z=np.load(path.parent/'scores.npz');ids=z['indices']
            assert np.isnan(scores[si,ids]).all();scores[si,ids]=z['scores'];fold[si,ids]=fo;alarm[si,ids]=z['scores']>f['threshold']
            p=FITS/'post_ask/A_hazard'/mode/f's{seed}-f{fo}';bf=json.loads((p/'fit.json').read_text());bl=bf['layer']
            with np.load(p/f'lr-l{bl}.npz') as b:
                direction=b['coef'][0]/b['scale'];bias=float(b['intercept'][0])-b['mean']@direction
                baseline[si,ids]=np.asarray(x[source[ids],bl],dtype=float)@direction+bias
        ids=np.flatnonzero(np.isfinite(scores).all(axis=0));assert len(ids)==1995
        y=np.array([rows[i]['y_'+label] for i in ids]);metrics,boot=stream_metrics(rows,ids,y,scores[:,ids],fold[:,ids],1000);bm,bb=stream_metrics(rows,ids,y,baseline[:,ids],fold[:,ids],1000)
        held=np.array([not rows[i]['ever_public'] for i in ids]);delta=boot['within_round']-bb['within_round']
        metrics.update(frozen_paper_A=bm,minus_frozen_A=dict(estimate=metrics['within_round_auc']-bm['within_round_auc'],ci95=np.nanquantile(delta,[.025,.975]).tolist()),held_reply_alarms_by_seed=alarm[:,ids][:,held].mean(axis=1).tolist())
        results[f'{label}/{mode}']=metrics;write_json_atomic(out/'metrics.json',results)
        for si,seed in enumerate(SEEDS):
            for j,i in enumerate(ids):
                exports.append(dict(label_variant=label,analysis=mode,seed=seed,fold=int(fold[si,i]),row_id=rows[i]['row_id'],request_sha256=rows[i]['request_sha256'],label=int(y[j]),score=float(scores[si,i]),frozen_A_score=float(baseline[si,i]),alarm=bool(alarm[si,i]),episode=rows[i]['episode'],scenario=rows[i]['scenario'],round=rows[i]['round']))
        print('METRIC',label,mode,metrics['within_round_auc'],flush=True)
    with (out/'probe_scores.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(exports[0]));w.writeheader();w.writerows(exports)
    lines=['# Post hoc last-prompt label ladder on gpt-oss-20b','',
      'These fits were requested after the immediate and strict-next-call ablation. They use the identical 1,995 nonempty-reasoning recruiting calls from 238 episodes, including 121 first-public-emission calls, and the same saved family/scenario partitions, 17 candidate layers, training-only scaling, round weights, C=0.1 and seeds 42/43/44. Neither model consumes generated reasoning. Round-any-public is positive when the first public emission occurs in this round or the next; eventual-any-public is positive for every retained call of an episode that eventually publishes. Both use any-publication rather than the paper\u2019s channel-only episode outcome.','',
      '| Label / split | Rows / positives | Refit last-prompt AUROC [95% CI] | Frozen paper A AUROC [95% CI] | Paired gain [95% CI] | Held-reply alarms |',
      '|---|---:|---|---|---|---:|']
    fmt=lambda m:f"{m['within_round_auc']:.3f} [{m['within_round_ci95'][0]:.3f}, {m['within_round_ci95'][1]:.3f}]"
    for k,m in results.items():
        d=m['minus_frozen_A'];lines.append(f"| {k} | {m['rows']}/{m['positives']} | {fmt(m)} | {fmt(m['frozen_paper_A'])} | {d['estimate']:+.3f} [{d['ci95'][0]:+.3f}, {d['ci95'][1]:+.3f}] | {np.mean(m['held_reply_alarms_by_seed']):.1%} |")
    lines+=['','Metrics are within scenario × round, with 1,000 paired family bootstrap draws at seed 20261025 conditional on fitted choices. Held-reply alarms use training-side no-ask control-reply thresholds at nominal 5%, strict >; they are not episode-level intervention rates. The frozen A model is evaluated on identical rows with each new label, but was trained on its original channel-outcome near-term label. This contrast changes the training task and includes emitting calls absent from the original fitting cohort. Do not interpret differences between ladder labels as a paired effect of temporal distance alone.','',
      'The previous immediate refit on these same 1,995 rows is in runs/20261026-1221-e05-lastprompt-percall-6013. Its strict-next refit excludes own-leak calls and uses 1,874 rows, so that rung has a different cohort. Sources: runs/20261026-0522-e05-reasoning-stream-data; runs/20261025-2305-e05-gpt-oss-full-data; runs/20261026-0138-e05-gpt-oss-main. Reusable fitting code: experiments/E05-probes/lastprompt_percall.py; wrapper: experiments/E05-probes/lastprompt_label_ladder.py.']
    (out/'report.md').write_text('\n'.join(lines)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);a=p.parse_args();run=None
    if a.out:out=a.out
    else:
        run=start_run('e05-lastprompt-label-ladder',experiment='E05',parents=['20261026-1221-e05-lastprompt-percall-6013',DATA.name,FITS.name],settings={'post_hoc':True,'threads':2,'no_gpu':True,'no_api':True,'labels':['round_any','eventual_any'],'cohort':'matched1995'})
        out=run.dir
    print('OUTPUT',out,flush=True);rows,base,x,plans=load()
    for r in rows:
        r['y_round_any']=int(bool(r['ever_public']) and bool(r['y_near']))
        r['y_eventual_any']=int(bool(r['ever_public']))
    write_json_atomic(out/'analysis_plan.json',dict(post_hoc=True,labels={'round_any':'first public emission this round or next, inclusive','eventual_any':'episode eventually publishes, any-public'},source_plans=str(FITS/'plans.json'),cohort='same1995 calls as immediate matched run, including emitting calls',recipe_source='experiments/E05-probes/lastprompt_percall.py',jobs=66))
    try:
      with threadpool_limits(limits=2):
        for label in ['round_any','eventual_any']:
            for plan in sorted(plans,key=lambda v:(v['mode']!='loso',v['seed'],v['fold'])):run_fit(out,rows,base,x,plan,label,'matched')
        summarize(out,rows,x)
      if run:run.finish(status='complete')
    except BaseException as e:
      if run:run.finish(status='failed',error=str(e))
      raise


if __name__=='__main__':main()
