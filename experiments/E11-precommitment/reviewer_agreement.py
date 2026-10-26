"""Join independently supplied blind yes/no judgements to the hidden sample key."""
import argparse
import csv
import json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--labels',type=Path,required=True);a=p.parse_args()
keys={r['sample_id']:r for r in json.loads((a.run/'blind_sample_key.json').read_text())}
labels=list(csv.DictReader(a.labels.open()))
assert len(labels)==len(keys) and {r['sample_id'] for r in labels}==set(keys)
for r in labels:assert r['judgement'].strip().lower() in ('yes','no')
out={}
for flag in ('jev','regex'):
    matrix={f'reviewer_{y}_flag_{f}':0 for y in ('yes','no') for f in ('yes','no')}
    for r in labels:
        y=r['judgement'].strip().lower();f='yes' if keys[r['sample_id']][flag] else 'no';matrix[f'reviewer_{y}_flag_{f}']+=1
    agrees=matrix['reviewer_yes_flag_yes']+matrix['reviewer_no_flag_no']
    out[flag]={'agreement':agrees/len(labels),'agreements':agrees,'n':len(labels),'confusion':matrix}
out['sampling_caveat']='Balanced by Jev flag, not a population prevalence sample.'
(a.run/'reviewer_agreement.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
