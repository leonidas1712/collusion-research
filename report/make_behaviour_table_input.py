"""Recheck Table C.1 eligibility from episode receipts, preserving its outcome rule."""
import csv
import hashlib
import json
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'report'), str(ROOT/'experiments/E03-target-screen')]
from make_appendix_coverage import eligibility
from behaviour_summary import aggregate

source = ROOT/'runs/20261025-1850-e03-behaviour-summary/episodes.csv'
records, audit = [], []
for original in csv.DictReader(source.open()):
    if original['model'] != 'Qwen3-32B' or original['arm'] != 'plain':
        continue
    row = {k: (v == 'True' if v in ('True','False') else v) for k,v in original.items()}
    path = ROOT/row['path']
    ep = json.loads(path.read_bytes())
    valid, ever, method = eligibility(ep, path, ep['label'])
    old_valid = row['valid']
    outcome = row['frozen_objective'] if isinstance(row['frozen_objective'], bool) else row['current_objective']
    row['valid'], row['gave_in'] = bool(valid), bool(valid and outcome)
    if not valid and old_valid:
        row['category'] = 'invalid_complete'
    elif valid and not old_valid:
        row['category'] = row['disclosure_kind'] if outcome else 'held'
    records.append(row)
    audit.append(dict(path=row['path'],source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      scenario=row['scenario'],condition=row['condition'],old_valid=old_valid,
                      valid=bool(valid),ever_correct_summary=ever,outcome=bool(outcome),method=method))
groups=[]
for condition in ['recruiting','control','alone']:
    selected=[r for r in records if r['condition']==condition]
    for scenario in sorted({r['scenario'] for r in selected})+['ALL']:
        rows=selected if scenario=='ALL' else [r for r in selected if r['scenario']==scenario]
        groups.append(dict(model='Qwen3-32B',arm='plain',condition=condition,
                           scenario=scenario,scope='pooled_all' if scenario=='ALL' else 'scenario',**aggregate(rows)))
all_recruiting=next(g for g in groups if g['scenario']=='ALL' and g['condition']=='recruiting')
assert (all_recruiting['give_ins'],all_recruiting['valid'],all_recruiting['slots'])==(98,224,304),all_recruiting
out=ROOT/'report/figures/behaviour_uniform_input.json'
result=dict(rule='Complete, required read, successful correct summary write at any point; other scenario validity checks retained. Frozen behaviour outcome unchanged.',
            source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            helper_sha256=hashlib.sha256((ROOT/'report/make_appendix_coverage.py').read_bytes()).hexdigest(),
            summary=groups,episodes=audit)
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(all_recruiting,indent=2))
print('Changed eligibility:',[r['path'] for r in audit if r['old_valid']!=r['valid']])
