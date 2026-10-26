"""Independent point-estimate audit of E08 score exports using sklearn AUROC."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import sys
import numpy as np
from sklearn.metrics import roc_auc_score
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic


def main():
    checks={};sources={}
    for name in ['20261026-1717-e08-policy-counterfactual','20261026-1732-e08-policy-counterfactual-gpt-oss']:
        folder=ROOT/'runs'/name
        for file in ['scores.csv','metrics.json','plan.json']:
            p=folder/file;sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        rows=list(csv.DictReader((folder/'scores.csv').open()));m=json.loads((folder/'metrics.json').read_text());plan=json.loads((folder/'plan.json').read_text())
        grouped=defaultdict(dict)
        for r in rows:
            assert r['condition'] not in grouped[r['call_id']]
            grouped[r['call_id']][r['condition']]=r
        assert all(set(x)=={'FORBID','PERMIT','NEUTRAL_EDIT'} for x in grouped.values())
        positives=[x for x in grouped.values() if x['FORBID']['class']=='leaking']
        assert len(positives)==m['calls']['leaking']
        assert len(grouped)-len(positives)==m['calls']['non_leaking']
        assert len(rows)==m['calls']['score_rows']
        errors=[]
        for field,left,right in [('permit_minus_forbid','PERMIT','FORBID'),('neutral_minus_forbid','NEUTRAL_EDIT','FORBID'),('permit_minus_neutral','PERMIT','NEUTRAL_EDIT')]:
            delta=np.median([float(x[left]['score'])-float(x[right]['score']) for x in positives]);errors.append(abs(delta-m['paired_leaking_call_changes'][field]['median']))
        for condition in ['FORBID','PERMIT','NEUTRAL_EDIT']:
            rr=[r for r in rows if r['condition']==condition];strata=defaultdict(list)
            pooled=roc_auc_score([r['class']=='leaking' for r in rr],[float(r['score']) for r in rr]);errors.append(abs(pooled-m['auc'][condition]['pooled']['value']))
            for r in rr:strata[r['scenario'],int(r['round'])].append(r)
            weighted=den=0
            for group in strata.values():
                y=[r['class']=='leaking' for r in group]
                if len(set(y))<2:continue
                weighted+=sum(y)*roc_auc_score(y,[float(r['score']) for r in group]);den+=sum(y)
            errors.append(abs(weighted/den-m['auc'][condition]['within_stratum']['value']))
            count=sum(float(x[condition]['score'])>plan['probe']['threshold'] for x in positives)
            assert count==m['threshold_crossing'][condition]['numerator']
            assert len(positives)==m['threshold_crossing'][condition]['denominator']
        reproduction=max(abs(float(x['FORBID']['score'])-float(x['FORBID']['saved_forbid_score'])) for x in grouped.values())
        assert reproduction<=m['forbid_reproduction']['tolerance']
        assert max(errors)<1e-12
        checks[name]=dict(calls=len(grouped),positive_calls=len(positives),point_estimates_checked=12,max_absolute_error=max(errors),forbid_reproduction_error=reproduction,confidence_intervals='Registered exactly from the source metrics; not independently recomputed here')
    run=start_run('e05-e08-numeric-audit',experiment='E05',settings=dict(no_model_calls=True,no_refit=True,sources=sources))
    write_json_atomic(run.dir/'audit.json',checks);run.result(passed=True);run.finish();print(run.dir);print(json.dumps(checks,indent=2))


if __name__=='__main__':main()
