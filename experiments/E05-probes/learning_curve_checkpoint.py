"""Report one completed learning-curve analysis while the other fits continue."""
import argparse
import json
import sys
import numpy as np
from threadpoolctl import threadpool_limits
from learning_curve import ROOT,DATA,FIT,SEEDS,FRACTIONS,labels
from evaluate import ranking_summary,interval
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run


def main(args):
    source=ROOT/'runs'/args.source
    run=start_run('e05-learning-checkpoint',experiment='E05',parents=[args.source,DATA,FIT,args.near_run],
                  settings={'label_variant':args.label,'analysis':args.analysis,'partial_report':True,'no_refits':True})
    try:
        rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
        keep,y=labels(rows,args.label);ids=np.flatnonzero(keep);rounds=np.array([rows[i]['round'] for i in ids])
        families=np.array([rows[i]['family'] for i in ids]);scenarios=[rows[i]['scenario'] for i in ids]
        plan=[c for c in json.loads((source/'sampling_plan.json').read_text()) if c['label_variant']==args.label and c['analysis']==args.analysis]
        origin=ROOT/'runs'/(FIT if args.label=='eventual' else args.near_run)
        if args.label!='eventual':origin=origin/args.label
        with np.load(origin/args.analysis/'predictions.npz') as d:full={m:d[m][:,ids] for m in ('nested','fixed32')}
        results={};boots={}
        with threadpool_limits(limits=2):
            for fraction in FRACTIONS:
                p={m:np.full((9,len(rows)),np.nan) for m in full}
                for c in plan:
                    if c['fraction']!=fraction:continue
                    slot=SEEDS.index(c['seed'])*3+c['draw']
                    if fraction==1:
                        for method in p:p[method][slot,ids]=full[method][SEEDS.index(c['seed'])]
                    else:
                        path=source/args.label/args.analysis/f"s{c['seed']}-f{c['fold']}-d{c['draw']}-p{int(fraction*100)}"
                        with np.load(path/'predictions.npz') as d:
                            assert np.array_equal(d['test'],c['test'])
                            for method in p:p[method][slot,d['test']]=d[method]
                results[str(fraction)]={};boots[fraction]={}
                for method,scores in p.items():
                    assert np.isfinite(scores[:,ids]).all()
                    m,wb,_=ranking_summary(np.tile(y[ids],(9,1)),scores[:,ids],rounds,families,1000,stratum_key=scenarios)
                    results[str(fraction)][method]=m;boots[fraction][method]=wb
                sizes=[len(c['train_families']) for c in plan if c['fraction']==fraction]
                results[str(fraction)]['training_family_counts']=dict(min=min(sizes),max=max(sizes),mean=float(np.mean(sizes)))
        results['gain_75_to_100']={m:dict(gain_75_to_100=results['1.0'][m]['within_round_auc']-results['0.75'][m]['within_round_auc'],
            paired_family_ci95=interval(boots[1.][m]-boots[.75][m])) for m in full}
        write_json(run.dir/'metrics.json',results)
        lines=[f'# Learning-curve checkpoint: {args.label}, {args.analysis}','',
               'This analysis has all three seeds and three draws at every size; other analyses in the parent run are still in progress. Fixed test rows and saved inner folds; 100% scores reused. Point estimates average nine seed×draw AUROCs; intervals are conditional 95% family-bootstrap intervals (1,000 resamples). No new fits.','',
               '| Fraction | Nested AUROC [95% CI] | Fixed32 AUROC [95% CI] |','|---|---|---|']
        for fraction in FRACTIONS:
            cells=[]
            for method in full:
                m=results[str(fraction)][method];ci=m['within_round_ci95'];cells.append(f"{m['within_round_auc']:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]")
            lines.append(f"| {fraction:.0%} | {' | '.join(cells)} |")
        lines+=['','75%→100% paired increments:','']
        for method,g in results['gain_75_to_100'].items():
            ci=g['paired_family_ci95'];lines.append(f"- {method}: {g['gain_75_to_100']:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}].")
        lines+=['','An interval spanning zero does not establish saturation. Cross-fold score shifts can affect pooled-CV ranks.']
        (run.dir/'report.md').write_text('\n'.join(lines)+'\n');run.result(complete_analysis=True);run.finish();print('LEARNING_CHECKPOINT',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--label',choices=['eventual','B_round_contrast'],required=True)
    p.add_argument('--analysis',choices=['pooled','loso'],required=True);p.add_argument('--near-run',default='20261025-0730-e05-near-term');main(p.parse_args())
