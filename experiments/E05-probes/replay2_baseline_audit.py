"""Audit training-prevalence baselines without refitting or changing primary metrics."""
import json
import sys
import numpy as np
from data import ROOT
from replay2_models import scenario_rates
from metrics import within_round
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run
DATA='20261025-0337-e05-replay2-data';FIT='20261025-0340-e05-replay2-fits';ANALYSIS='20261025-0531-e05-replay2-analysis'

def main():
    rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()];results={}
    run=start_run('e05-replay2-baseline-audit',experiment='E05',parents=[DATA,FIT,ANALYSIS],settings={'posthoc_diagnostic':True,'no_refits':True,'primary_metrics_unchanged':True,'question':'Does pooling training-prevalence scores across fitted folds create below-chance baseline ranks?'})
    try:
        for mode in ('v2','pooled','loso','deliberate_v2','deliberate_pooled'):
            path=ROOT/'runs'/FIT/mode;data=np.load(path/'predictions.npz');notes=json.loads((path/'folds.json').read_text());errors=[]
            for note in notes:
                seed=note['seed'];fold=note['fold'];si=list(data['seeds']).index(seed);split=np.load(path/f'split-s{seed}-f{fold}.npz');train=split['train'];test=split['test']
                expected,_=scenario_rates(rows,train,test,data['y'][train]);error=float(np.max(np.abs(expected-data['scenario_only'][si,test])));assert error==0;errors.append(error)
            head=data['eligible'][[rows[i]['condition']=='recruiting' for i in data['eligible']]];rounds=np.array([rows[i]['round'] for i in head]);y=data['y'][head];scenarios=[rows[i]['scenario'] for i in head];diagnostics={}
            for method in ('scenario_only','scenario_round'):
                primary=[];within_fold=[]
                for si,scores in enumerate(data[method][:,head]):
                    primary.append(within_round(y,scores,rounds,stratum_key=scenarios)[0]);strata=[(scenario,int(fold)) for scenario,fold in zip(scenarios,data['folds'][si,head])]
                    value,detail=within_round(y,scores,rounds,stratum_key=strata);assert abs(value-.5)<1e-12
                    within_fold.append({'auc':value,'positive_coverage':detail['positive_coverage']})
                diagnostics[method]={'primary_by_seed':primary,'within_scenario_round_and_fitted_fold':within_fold}
            results[mode]={'max_scenario_rate_reconstruction_error':max(errors),'folds_checked':len(errors),'baselines':diagnostics}
        write_json(run.dir/'summary.json',results)
        (run.dir/'report.md').write_text('''# Post-hoc baseline audit

All scenario-only scores exactly reconstruct from unique training episodes. There is no test-label input to those scores. Both scenario-only and scenario + round baselines score exactly 0.5 when comparisons are additionally confined to the same fitted fold (among comparable strata).

Their below-chance values under the predeclared CV metric arise when comparing scores from different fitted folds within a scenario and round. For example, a training scenario rate is the rate in the complement of the held-out fold: held-out folds with more positives can receive lower training-rate predictions. LOSO has one fitted model per held-out scenario per seed and its within-scenario × round baselines are exactly 0.5.

This is a post-hoc diagnostic, not a replacement metric. No probe was refit or re-evaluated under the additional stratification, and the primary estimates are unchanged. Pooled out-of-fold scores can reflect cross-model calibration shifts; comparisons against these below-chance CV baselines should not be treated as evidence of robust added value. The v2 shuffled-label score is also below chance under the original metric; its family interval conditions on the three frozen label shuffles and fits, not on a new permutation experiment.
''')
        run.result(all_rate_scores_exact=True,baseline_within_fold_auc=.5,primary_metrics_unchanged=True);run.finish();print('BASELINE_AUDIT',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':main()
