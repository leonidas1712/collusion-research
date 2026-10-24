"""Apply frozen family-held-out v1 probes to the shared pre-peer states."""
import argparse
import json
import sys
import numpy as np
from data import ROOT
from branching_check import statistics,FIT,BRANCH
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run


def main(args):
    source=ROOT/'runs'/args.data_run;rows=[json.loads(s) for s in (source/'rows.jsonl').read_text().splitlines()];x=np.load(source/'features.npy',mmap_mode='r')
    old=json.loads((ROOT/'runs/20261025-0000-e05-branching-check/points.json').read_text());old={(p['episode'],p['branch_round']):p for p in old if p['score'] is not None}
    folds=json.loads((ROOT/'runs'/FIT/'main/folds.json').read_text());shared=[r for r in rows if r['shared_branch_history']];assert len(shared)==len(old)==23
    original=[json.loads(s) for s in (ROOT/'runs'/FIT/'rows.jsonl').read_text().splitlines()]
    original_families={r['episode']:r['family'] for r in original}
    run=start_run('e05-replay2-branching',experiment='E05',parents=[args.data_run,FIT,BRANCH],settings={'checkpoint':'shared history before round-t peer','models':'frozen v1 family OOF; no refitting','bootstrap':'2000 family clusters'})
    try:
        points=[]
        for row in shared:
            key=(row['parent_episode'],row['branch_round']);p=old[key];scores=[];provenance=[]
            for seed in (42,43,44):
                matching=[f for f in folds if f['seed']==seed and p['episode'] in f['test_episodes']];assert len(matching)==1;f=matching[0]
                assert p['episode'] not in f['train_episodes']
                assert original_families[p['episode']] not in {original_families[e] for e in f['train_episodes']}
                layer=f['chosen_layer'];path=ROOT/'runs'/FIT/'main'/f"model-s{seed}-f{f['fold']}-l{layer}.npz"
                model=np.load(path);z=(x[row['index'],layer].astype(float)-model['mean'])/model['scale'];value=float((z@model['coef'].reshape(-1)+model['intercept'].reshape(-1)[0]));assert np.isfinite(value)
                scores.append(value);provenance.append(dict(seed=seed,fold=f['fold'],layer=layer,model=str(path.relative_to(ROOT))))
            points.append(dict(episode=p['episode'],family=p['family'],branch_round=p['branch_round'],fraction=p['fraction'],hits=p['hits'],reruns=p['reruns'],score=scores,models=provenance,prompt_sha256=row['prompt_sha256'],request_sha256=row['request_sha256']))
        summary=statistics(points,'score');write_json(run.dir/'points.json',points);write_json(run.dir/'summary.json',summary)
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(6,4));ax.scatter([np.mean(p['score']) for p in points],[p['fraction'] for p in points],s=42,alpha=.75)
        ax.set(xlabel='Mean frozen v1 OOF logit at shared state',ylabel='Give-in fraction over 5 reruns',ylim=(-.05,1.05),title=f"Shared-state branching: Spearman {summary['spearman']:.3f}")
        fig.tight_layout();fig.savefig(run.dir/'branching.png',dpi=180);fig.savefig(run.dir/'branching.svg');plt.close(fig)
        (run.dir/'report.md').write_text(f"# Shared-state branching check\n\nMatched {summary['points']} states in {summary['families']} families. Spearman = {summary['spearman']:.3f}, family-bootstrap 95% CI {summary['family_bootstrap_ci95']}.\n\nEach state ends before the new round's peer message. Frozen v1 family-held-out models were applied without refitting. Each empirical fraction has only five reruns; the interval is conditional on these frozen models and observed continuations. This is an association, not an intervention on the probe direction.\n\n![Branching](branching.png)\n")
        run.result(**summary);run.finish();print('BRANCH_RUN',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('data_run');main(p.parse_args())
