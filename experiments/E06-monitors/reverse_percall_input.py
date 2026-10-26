"""Explicit post hoc score-reversal diagnostic; primary scores stay unchanged."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import percall_input_monitor as m
from reasoning_stream_report import stream_metrics,SEEDS
from collusion.runs import start_run,write_json_atomic


def main(directory):
    target=json.loads((directory/'meta.json').read_text())['settings']['target'];rows,evaluation,_,_=m.inputs(target);ids=np.array(sorted(evaluation));y=np.array([rows[i]['y_immediate'] for i in ids]);source={(r['analysis'],int(r['seed']),r['row_id']):r for r in csv.DictReader((directory/'probe_scores.csv').open())};original=json.loads((directory/'metrics.json').read_text());result={}
    probe_source=m.MATCHED if target=='gpt-oss' else m.QWEN/'probe_scores.csv'
    probe={(r['analysis'],int(r['seed']),r['row_id']):r for r in csv.DictReader(probe_source.open()) if r['label_variant']=='immediate' and (target!='gpt-oss' or r.get('cohort')=='matched')}
    run=start_run('e06-percall-reversal-diagnostic',experiment='E06',parents=[directory.name],settings={'request':'post hoc ranking-reversal diagnostic','post_hoc':True,'primary_unchanged':True,'no_refit':True})
    try:
        for mode in ['pooled','loso']:
            scores=np.array([[float(source[(mode,s,rows[i]['row_id'])]['score']) for i in ids] for s in SEEDS]);folds=np.array([[int(source[(mode,s,rows[i]['row_id'])]['fold']) for i in ids] for s in SEEDS]);reversed_metric,reversed_boot=stream_metrics(rows,ids,y,1-scores,folds,1000)
            old=original[mode];expected=[1-old['within_round_ci95'][1],1-old['within_round_ci95'][0]]
            assert abs(reversed_metric['within_round_auc']-(1-old['within_round_auc']))<1e-12
            np.testing.assert_allclose(reversed_metric['within_round_ci95'],expected,rtol=0,atol=1e-12)
            ps=np.array([[float(probe[(mode,s,rows[i]['row_id'])]['score']) for i in ids] for s in SEEDS])
            assert all(probe[(mode,s,rows[i]['row_id'])]['request_sha256']==source[(mode,s,rows[i]['row_id'])]['request_sha256'] and probe[(mode,s,rows[i]['row_id'])]['fold']==source[(mode,s,rows[i]['row_id'])]['fold'] for s in SEEDS for i in ids)
            pm,pb=stream_metrics(rows,ids,y,ps,folds,1000);diff=pb['within_round']-reversed_boot['within_round']
            result[mode]=dict(probe_minus_reversed=pm['within_round_auc']-reversed_metric['within_round_auc'],probe_minus_reversed_ci95=np.nanquantile(diff,[.025,.975]).tolist(),original_within_auc=old['within_round_auc'],post_hoc_reversed_auc=reversed_metric['within_round_auc'],reversed_ci95=reversed_metric['within_round_ci95'],complement_identity_verified=True)
        payload=dict(post_hoc=True,primary_scores_and_alarms_unchanged=True,results=result,identity='Within each eligible stratum, reversing scores exchanges wins and losses and keeps ties at0.5. Positive weights and stratum coverage do not depend on scores. Thus every weighted aggregate and each family-bootstrap draw is exactly complemented; percentile CI bounds reverse.')
        write_json_atomic(directory/'reversal_diagnostic.json',payload);write_json_atomic(run.dir/'reversal_diagnostic.json',payload)
        text=(directory/'report.md').read_text().split('\n## Post hoc reversal diagnostic')[0];r=result['loso'];text+=f"\n## Post hoc reversal diagnostic\n\nReversing Jev’s score after observing the result would give within-scenario×round AUROC **{r['post_hoc_reversed_auc']:.3f} [{r['reversed_ci95'][0]:.3f}, {r['reversed_ci95'][1]:.3f}]**. This is a post hoc diagnostic, not the declared monitor result; no primary score, threshold or alarm is changed.\n\nThe identity reversed AUROC = 1 − original AUROC holds exactly for this aggregation: reversal complements each stratum AUROC, including ties; positive weights and eligible strata remain unchanged. It also complements every paired family-bootstrap draw, so the CI is [1 − upper, 1 − lower]. Direct recomputation from reversed saved scores verifies both point and CI to1e−12. Thus below-chance ranking does not imply absence of predictive information in the text.\n";text+=f"\nThe matched last-prompt probe minus this post hoc reversed comparator is {r['probe_minus_reversed']:+.3f} [{r['probe_minus_reversed_ci95'][0]:+.3f}, {r['probe_minus_reversed_ci95'][1]:+.3f}] under LOSO, using the same paired family-bootstrap draws. This remains a post hoc direction diagnostic, not a revised primary comparator.\n";(directory/'report.md').write_text(text)
        run.result(**result);run.finish();print(json.dumps(result),flush=True)
    except BaseException as e:run.finish('failed',str(e));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);main(p.parse_args().run)
