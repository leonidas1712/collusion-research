"""Independent sklearn check of positive-weighted scenario/round AUROC."""
import csv
import json
import sys
from pathlib import Path
from collections import defaultdict
from sklearn.metrics import roc_auc_score
run=Path(sys.argv[1]);rows=list(csv.DictReader((run/'flags.csv').open()));saved=json.loads((run/'metrics.json').read_text());checks=[]
for model in ('qwen','gpt-oss'):
    base=[r for r in rows if r['model']==model]
    variants=[('all',base,'score')]+[(f'no_{flag}',[r for r in base if r[flag]=='False'],'score') for flag in ('regex','jev')]+[(f'{flag}_detector',base,flag) for flag in ('regex','jev')]
    for name,kept,field in variants:
        groups=defaultdict(list)
        for r in kept:groups[(r['scenario'],r['round'])].append(r)
        weighted=0.;denominator=0
        for group in groups.values():
            y=[int(r['label']) for r in group]
            if len(set(y))<2:continue
            s=[float(r[field]) if field=='score' else float(r[field]=='True') for r in group]
            weighted+=sum(y)*roc_auc_score(y,s);denominator+=sum(y)
        actual=weighted/denominator if denominator else None
        expected=saved[model][name].get('within_round_auc')
        if actual is not None:assert abs(actual-expected)<1e-12,(model,name,actual,expected)
        checks.append(dict(model=model,variant=name,auc=actual,scored_positive_denominator=denominator,calls=len(kept)))
(run/'metrics_audit.json').write_text(json.dumps(checks,indent=2));print('PASS',len(checks),'independent estimates')
