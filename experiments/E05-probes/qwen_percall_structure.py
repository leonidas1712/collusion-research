"""Post hoc causal read-step diagnostic on saved Qwen requests and OOF scores."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from qwen_percall import ROOT, arguments
from reasoning_stream_report import stream_metrics
from collusion.runs import write_json_atomic


def features(out):
    rows=json.loads((out/'rows.json').read_text());episodes={};records=[]
    for r in rows:
        if r['condition']!='recruiting':continue
        ep=r['episode']
        if ep not in episodes:
            run,name=ep.split('/');episodes[ep]=json.loads((ROOT/'runs'/run/'episodes'/name).read_text())
        e=episodes[ep];request=e['requests'][r['request_idx']]['request']
        sha=hashlib.sha256(json.dumps(request,ensure_ascii=False,separators=(',', ':')).encode()).hexdigest()
        assert sha==r['request_sha256']
        tokens=e['scenario_spec']['honeypots'];files=e['scenario_spec']['files']
        paths={path for path,body in files.items() if path.startswith('private/') and isinstance(body,str) and any(t in body for t in tokens)}
        assert paths
        messages=request['messages'];calls={c['id']:c['function'] for m in messages for c in m.get('tool_calls',[])}
        trailing=[]
        for m in reversed(messages):
            if m.get('role')!='tool':break
            trailing.append(m)
        flag=False
        for m in trailing:
            fn=calls.get(m.get('tool_call_id'),{});args=arguments(fn.get('arguments'));result=arguments(m.get('content'))
            if fn.get('name')=='read_file' and args.get('path') in paths and isinstance(result,dict) and 'error' not in result and isinstance(result.get('content'),str) and any(t in result['content'] for t in tokens):flag=True
        records.append(dict(row_id=f"{ep}::request_idx={r['request_idx']}",request_sha256=sha,latest_protected_read=int(flag),latest_role=messages[-1]['role'],trailing_tool_results=len(trailing)))
    write_json_atomic(out/'structural_features.json',dict(scope='Post hoc, outside frozen plan; feature definition set before reading subgroup OOF metrics',definition='Latest incoming block consists of trailing tool-result messages; at least one is a successful read_file of an initially protected private file and its content contains the exact value. Only saved request messages are inspected, never the current response.',records=records))
    print('STRUCTURAL_FEATURES',len(records),sum(r['latest_protected_read'] for r in records),flush=True)


def summarize(out):
    rows=json.loads((out/'rows.json').read_text());lookup={f"{r['episode']}::request_idx={r['request_idx']}":i for i,r in enumerate(rows)}
    f=json.loads((out/'structural_features.json').read_text());flags={r['row_id']:r['latest_protected_read'] for r in f['records']}
    path=out/'probe_scores.csv';handle=path.open(newline='') if path.exists() else gzip.open(out/'probe_scores.csv.gz','rt',newline='')
    with handle:records=[r for r in csv.DictReader(handle) if r['label_variant']=='immediate']
    results={}
    for mode in ['loso','pooled']:
        byseed={s:{lookup[r['row_id']]:r for r in records if r['analysis']==mode and int(r['seed'])==s} for s in [42,43,44]}
        ids=np.array(sorted(byseed[42]));assert len(ids)==4844 and set(ids)==set(byseed[43])==set(byseed[44])
        y=np.array([rows[i]['y_immediate'] for i in ids]);v=np.array([flags[byseed[42][i]['row_id']] for i in ids]);scores=np.array([[float(byseed[s][i]['score']) for i in ids] for s in [42,43,44]]);folds=np.array([[int(byseed[s][i]['fold']) for i in ids] for s in [42,43,44]])
        probe,pb=stream_metrics(rows,ids,y,scores,folds,1000);base,bb=stream_metrics(rows,ids,y,np.tile(v,(3,1)),folds,1000);delta=pb['within_round']-bb['within_round']
        subset=v==1;conditional,_=stream_metrics(rows,ids[subset],y[subset],scores[:,subset],folds[:,subset],1000)
        conditional['episodes']=len({rows[i]['episode'] for i in ids[subset]})
        results[mode]=dict(probe=probe,structural_baseline=base,paired_probe_minus_structure=dict(estimate=probe['within_round_auc']-base['within_round_auc'],ci95=np.nanquantile(delta,[.025,.975]).tolist()),flag_positive_calls=int(((v==1)&(y==1)).sum()),flag_negative_calls=int(((v==1)&(y==0)).sum()),unflagged_positive_calls=int(((v==0)&(y==1)).sum()),unflagged_negative_calls=int(((v==0)&(y==0)).sum()),probe_within_immediately_post_read=conditional)
    write_json_atomic(out/'structural_check.json',dict(scope=f['scope'],definition=f['definition'],results=results))
    lines=['## Post hoc read-step structural diagnostic','',f['scope']+'. '+f['definition'],
      'This flag means immediately after the tool-result block, not merely secret in context: every analysed call already satisfies the latter condition. The rule was fixed before looking at subgroup scores.','',
      '| Split | Read-step baseline AUROC [95% CI] | Paired probe minus baseline [95% CI] | Probe AUROC within flagged calls [95% CI] | Flagged positives / negatives |',
      '|---|---|---|---|---:|']
    fmt=lambda m:f"{m['within_round_auc']:.3f} [{m['within_round_ci95'][0]:.3f}, {m['within_round_ci95'][1]:.3f}]"
    for mode,m in results.items():
        d=m['paired_probe_minus_structure'];lines.append(f"| {mode} | {fmt(m['structural_baseline'])} | {d['estimate']:+.3f} [{d['ci95'][0]:+.3f}, {d['ci95'][1]:+.3f}] | {fmt(m['probe_within_immediately_post_read'])} | {m['flag_positive_calls']}/{m['flag_negative_calls']} |")
    lines+=['','Same OOF scores, labels and family-bootstrap draws as the primary result; no refits. Conditional AUROC only uses comparable scenario × round strata, 49 of the 66 flagged positive calls have a comparable negative in their stratum (74.2% coverage); the other 17 do not enter the conditional AUROC. The structural baseline is constant inside its positive subset, so no within-subset baseline AUROC or paired subtraction is defined. This diagnostic tests one observable task-step cue, not every possible contextual explanation.']
    text='\n'.join(lines)+'\n';(out/'structural_check.md').write_text(text);report=out/'report.md';base=report.read_text().split('\n## Post hoc read-step structural diagnostic')[0];report.write_text(base.rstrip()+'\n\n'+text)
    print(json.dumps({mode:{k:v for k,v in m.items() if k.startswith('flag')} for mode,m in results.items()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--features-only',action='store_true');a=p.parse_args()
    if a.features_only:features(a.out)
    else:summarize(a.out)
