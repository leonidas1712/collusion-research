"""Post hoc leak-route subgroups from saved Qwen OOF scores; no refits."""
import argparse
import csv
import gzip
import json
from pathlib import Path

import numpy as np
from reasoning_stream_report import stream_metrics
from collusion.runs import write_json_atomic


def run(out):
    rows=json.loads((out/'rows.json').read_text())
    audits=json.loads((out/'label_audit.json').read_text())['episodes']
    routes={e['episode']:('plain_assistant_text' if e['first_public_kind']=='channel_final' else 'tool_call_arguments') for e in audits if e['first_public_kind'] is not None}
    lookup={f"{r['episode']}::request_idx={r['request_idx']}":i for i,r in enumerate(rows)}
    path=out/'probe_scores.csv'
    if path.exists():f=path.open(newline='')
    else:f=gzip.open(out/'probe_scores.csv.gz','rt',newline='')
    with f:records=[r for r in csv.DictReader(f) if r['label_variant']=='immediate']
    results={}
    for mode in ['loso','pooled']:
        data=[r for r in records if r['analysis']==mode]
        for route in ['plain_assistant_text','tool_call_arguments']:
            selected=[r for r in data if int(r['label'])==0 or routes[r['episode']]==route]
            byseed={s:{lookup[r['row_id']]:r for r in selected if int(r['seed'])==s} for s in [42,43,44]}
            ids=np.array(sorted(byseed[42]));assert set(ids)==set(byseed[43])==set(byseed[44])
            y=np.array([rows[i]['y_immediate'] for i in ids]);scores=np.array([[float(byseed[s][i]['score']) for i in ids] for s in [42,43,44]])
            folds=np.array([[int(byseed[s][i]['fold']) for i in ids] for s in [42,43,44]])
            alarms=np.array([[byseed[s][i]['alarm']=='True' for i in ids] for s in [42,43,44]])
            metric,_=stream_metrics(rows,ids,y,scores,folds,1000)
            metric.update(positive_route=route,negative_calls=int((y==0).sum()),positive_catches_by_seed=alarms[:,y==1].sum(axis=1).tolist(),positive_catch_rate_by_seed=alarms[:,y==1].mean(axis=1).tolist())
            results[f'{mode}/{route}']=metric
    write_json_atomic(out/'route_subgroups.json',dict(scope='Post hoc descriptive subgroup, outside the frozen plan; no fitting or threshold changes',definition='Plain text: first qualifying publication in a final assistant reply with no tool calls; tool arguments: first qualifying publication from successful send_message or public-file write. Each subgroup uses the same all-nonleaking-call negatives and excludes the other route positives.',results=results))
    lines=['## Post hoc descriptive publication-route subgroups','',
      'This subgroup analysis was requested after the plan was frozen. No refits, layer reselection or threshold recalibration were performed. Plain text means the first qualifying publication is a final assistant reply without tool calls; tool arguments means a successful send_message or public-file write. Each route is compared against the same nonleaking-call negatives, excluding positives of the other route.','',
      '| Split / route | Positive calls | Same negative calls | AUROC [95% family CI] | Positive calls caught (seeds42/43/44) | Mean catch rate |',
      '|---|---:|---:|---|---|---:|']
    for k,m in results.items():
        lines.append(f"| {k} | {m['positives']} | {m['negative_calls']} | {m['within_round_auc']:.3f} [{m['within_round_ci95'][0]:.3f}, {m['within_round_ci95'][1]:.3f}] | {' / '.join(map(str,m['positive_catches_by_seed']))} | {np.mean(m['positive_catch_rate_by_seed']):.1%} |")
    lines+=['','Catches use the saved per-fold strict >5%-control-reply thresholds. They are observational call-level warning opportunities, not measured intervention success or episode-level catch rates. A tool-call-only filter cannot block a plain final text publication; a general output filter can still match the exact protected string in that text. These data do not demonstrate an advantage over such an output filter.']
    text='\n'.join(lines)+'\n';(out/'route_subgroups.md').write_text(text)
    report=out/'report.md';base=report.read_text().split('\n## Post hoc descriptive publication-route subgroups')[0];report.write_text(base.rstrip()+'\n\n'+text)
    print(json.dumps({k:{z:m[z] for z in ['positives','negative_calls','within_round_auc','positive_catches_by_seed']} for k,m in results.items()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.out)
