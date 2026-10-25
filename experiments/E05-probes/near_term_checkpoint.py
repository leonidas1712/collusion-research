"""Evaluate a fully fitted near-term variant while other variants continue."""
import argparse
import json
import sys
import numpy as np
from threadpoolctl import threadpool_limits
from near_term import ROOT,DATA,FIT,MODES,METHODS,SEEDS,label_rows,evaluate
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run


def main(args):
    rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
    keep,y=label_rows(rows,args.variant);ids=np.flatnonzero(keep);source=ROOT/'runs'/args.source
    run=start_run('e05-near-term-checkpoint',experiment='E05',parents=[DATA,FIT,args.source],settings={'variant':args.variant,'partial_report':True,'no_refits':True})
    try:
        result={}
        with threadpool_limits(limits=2):
            for mode in MODES:
                preds={m:np.full((3,len(rows)),np.nan) for m in METHODS};folds=np.full((3,len(rows)),-1,dtype=int)
                with np.load(ROOT/'runs'/FIT/mode/'predictions.npz') as old:
                    for m in ('nested','fixed32'):preds['eventual_'+m][:,ids]=old[m][:,ids]
                    for si,seed in enumerate(SEEDS):
                        for fold in range(5 if mode=='pooled' else 6):
                            with np.load(source/args.variant/mode/f's{seed}-f{fold}'/'scores.npz') as d:
                                test=d['test'];assert (folds[si,test]==-1).all();folds[si,test]=fold
                                for m in METHODS:
                                    if not m.startswith('eventual_'):preds[m][si,test]=d[m]
                        assert np.array_equal(folds[si,ids],old['folds'][si,ids])
                assert all(np.isfinite(s[:,ids]).all() for s in preds.values())
                result[mode]=evaluate(rows,y,ids,{m:s[:,ids] for m,s in preds.items()},folds[:,ids],1000)
                write_json(run.dir/'metrics.json',result);print('CHECKPOINT',mode,flush=True)
        text=['# Near-term checkpoint: '+args.variant,'','This variant is fully fitted; the other variants in the parent run are still in progress. No new fits. All figures use the same 1,000 family-bootstrap resamples and saved test folds as the final report.','',
              '| Analysis | Method | Scenario × round AUROC [95% CI] | Fold sensitivity [95% CI] |','|---|---|---|---|']
        for mode,r in result.items():
            for m,v in r['methods'].items():
                ci=v['within_round_ci95'];s=v['fold_sensitivity'];sc=s['ci95']
                text.append(f"| {mode} | {m} | {v['within_round_auc']:.3f} [{ci[0]:.3f}, {ci[1]:.3f}] | {s['auc']:.3f} [{sc[0]:.3f}, {sc[1]:.3f}] |")
        (run.dir/'report.md').write_text('\n'.join(text)+'\n');run.result(variant=args.variant,complete_variant=True);run.finish();print('CHECKPOINT_RUN',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--variant',default='A_hazard');main(p.parse_args())
