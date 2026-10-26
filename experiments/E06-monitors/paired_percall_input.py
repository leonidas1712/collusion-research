"""Paired family-bootstrap differences between frozen OOF probes and Jev."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import percall_input_monitor as m
from reasoning_stream_report import stream_metrics,SEEDS
from collusion.runs import start_run,write_json_atomic


def main(directory):
    target=json.loads((directory/'meta.json').read_text())['settings']['target'];rows,evaluation,_,_=m.inputs(target);ids=np.array(sorted(evaluation));y=np.array([rows[i]['y_immediate'] for i in ids])
    probe=m.MATCHED if target=='gpt-oss' else m.QWEN/'probe_scores.csv';monitor=directory/'probe_scores.csv'
    probes={};monitors={}
    for r in csv.DictReader(probe.open()):
        if r['label_variant']=='immediate' and (target!='gpt-oss' or r['cohort']=='matched'):probes[(r['analysis'],int(r['seed']),r['row_id'])]=r
    for r in csv.DictReader(monitor.open()):monitors[(r['analysis'],int(r['seed']),r['row_id'])]=r
    run=start_run('e06-percall-input-paired',experiment='E06',parents=[directory.name,probe.parent.name],settings={'request':'paired probe-minus-monitor comparison on identical calls','no_refit':True,'bootstrap_reps':1000,'bootstrap_seed':20261025})
    try:
        result={}
        for mode in ['pooled','loso']:
            ps=[];ms=[];folds=[]
            for seed in SEEDS:
                pp=[];mm=[];ff=[]
                for i in ids:
                    key=(mode,seed,rows[i]['row_id']);p=probes[key];q=monitors[key]
                    assert p['request_sha256']==q['request_sha256']==rows[i]['request_sha256']
                    assert int(p['label'])==int(q['label'])==rows[i]['y_immediate'] and p['fold']==q['fold']
                    pp.append(float(p['score']));mm.append(float(q['score']));ff.append(int(p['fold']))
                ps.append(pp);ms.append(mm);folds.append(ff)
            pm,pb=stream_metrics(rows,ids,y,np.array(ps),np.array(folds),1000);jm,jb=stream_metrics(rows,ids,y,np.array(ms),np.array(folds),1000)
            difference=pb['within_round']-jb['within_round'];result[mode]=dict(rows=len(ids),positives=int(y.sum()),probe_within_auc=pm['within_round_auc'],jev_within_auc=jm['within_round_auc'],probe_minus_jev=pm['within_round_auc']-jm['within_round_auc'],paired_family_ci95=np.nanquantile(difference,[.025,.975]).tolist(),valid_bootstrap_draws=int(np.isfinite(difference).sum()))
        payload=dict(target=target,comparisons=result,bootstrap_replicates=1000,seed=20261025,source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [probe,monitor]},exact_row_label_fold_request_hash_join=True,no_refit=True)
        for p in [directory,run.dir]:write_json_atomic(p/'paired_probe_difference.json',payload)
        report=directory/'report.md';text=report.read_text().split('\n## Paired probe comparison')[0];lines=['','## Paired probe comparison','','Both methods use identical calls, labels, folds, and scenario×round strata. Family-bootstrap draws are paired (1,000 draws, seed20261025), averaging seeds42/43/44. The probe is the matched immediate-label last-prompt probe. No score is reversed and no model is refitted.','','| Split | Probe AUROC | Jev AUROC | Probe minus Jev [paired95% CI] |','|---|---:|---:|---|']
        for mode,v in result.items():lines.append(f"| {mode} | {v['probe_within_auc']:.3f} | {v['jev_within_auc']:.3f} | {v['probe_minus_jev']:+.3f} [{v['paired_family_ci95'][0]:+.3f}, {v['paired_family_ci95'][1]:+.3f}] |")
        report.write_text(text+'\n'.join(lines)+'\n');run.result(**result);run.finish();print(json.dumps(payload),flush=True)
    except BaseException as e:run.finish('failed',str(e));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);main(p.parse_args().run)
