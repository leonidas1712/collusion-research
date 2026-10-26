"""Post hoc input-only workflow-position controls for immediate-call prediction."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from reasoning_stream_data import ROOT
from reasoning_stream_report import stream_metrics
from collusion.runs import start_run,write_json_atomic


def protected_read(call,protected):
    fn=call.get('function') or {};args=fn.get('arguments') or {}
    if isinstance(args,str):
        try:args=json.loads(args)
        except json.JSONDecodeError:return False
    return fn.get('name')=='read_file' and isinstance(args,dict) and args.get('path') in protected


def structural(ep,idx):
    protected={p for p,c in ep['scenario_spec']['files'].items() if any(v in c for v in ep['scenario_spec']['honeypots'])};assert protected
    req=ep['requests'][idx];messages=req['request']['messages'];calls={c['id']:c for m in messages for c in m.get('tool_calls',[]) if 'id' in c}
    latest=messages[-1];incoming=latest.get('role')=='tool' and protected_read(calls.get(latest.get('tool_call_id'),{}),protected)
    previous=[r for r in ep['requests'][:idx] if r.get('actor')=='target']
    prior=False
    if previous:
        msg=(previous[-1].get('response') or {}).get('choices',[{}])[0].get('message',{})
        prior=any(protected_read(c,protected) for c in msg.get('tool_calls') or [])
    return bool(incoming),bool(prior)


def main(out):
    rows=json.loads((ROOT/'runs/20261026-0522-e05-reasoning-stream-data/replies.json').read_text());lookup={r['row_id']:i for i,r in enumerate(rows)}
    sources=[out/'probe_scores.csv',ROOT/'runs/20261026-1221-e05-lastprompt-percall-6013/probe_scores.csv'];groups={};last={}
    for r in csv.DictReader(sources[0].open()):
        if r['variant']=='immediate' and r['mask']=='all' and r['window']=='post_ask':groups.setdefault(r['analysis'],{}).setdefault(int(r['seed']),{})[lookup[r['row_id']]]=r
    for r in csv.DictReader(sources[1].open()):
        if r['cohort']=='matched' and r['label_variant']=='immediate':last.setdefault(r['analysis'],{}).setdefault(int(r['seed']),{})[lookup[r['row_id']]]=r
    ids=np.array(sorted(groups['loso'][42]));assert len(ids)==1995;y=np.array([rows[i]['y_immediate'] for i in ids]);assert y.sum()==121
    episodes={};details=[]
    for i in ids:
        row=rows[i];p=row['source_path']
        if p not in episodes:episodes[p]=json.loads(Path(p).read_text())
        latest,prev=structural(episodes[p],row['request_idx']);details.append(dict(row_id=row['row_id'],label=int(y[len(details)]),latest_incoming_protected_read=latest,previous_call_protected_read=prev))
    flags={k:np.array([r[k] for r in details]) for k in ['latest_incoming_protected_read','previous_call_protected_read']}
    run=start_run('e05-immediate-readstep',experiment='E05',parents=[out.name,sources[1].parent.name],settings={'request':'Aboard1990','no_refit':True,'source_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}})
    try:
        metrics={};paired={};counts={k:dict(rows=int(v.sum()),positive=int((v&(y==1)).sum()),negative=int((v&(y==0)).sum())) for k,v in flags.items()}
        for mode in ['pooled','loso']:
            assert all(set(groups[mode][s])==set(ids)==set(last[mode][s]) for s in [42,43,44])
            folds=np.array([[int(groups[mode][s][i]['fold']) for i in ids] for s in [42,43,44]])
            assert all(int(last[mode][s][i]['fold'])==int(groups[mode][s][i]['fold']) and int(last[mode][s][i]['label'])==rows[i]['y_immediate'] for s in [42,43,44] for i in ids)
            boot={};scores={k:np.tile(v,(3,1)) for k,v in flags.items()}
            scores['reasoning_MAX']=np.array([[float(groups[mode][s][i]['max_score']) for i in ids] for s in [42,43,44]])
            scores['matched_last_prompt']=np.array([[float(last[mode][s][i]['score']) for i in ids] for s in [42,43,44]])
            for name,score in scores.items():metrics[mode+'/'+name],boot[name]=stream_metrics(rows,ids,y,score,folds,1000)
            for name in ['reasoning_MAX','matched_last_prompt']:
                for flag in flags:
                    difference=boot[name]['within_round']-boot[flag]['within_round'];key=mode+'/'+name+' minus '+flag
                    paired[key]=dict(difference=metrics[mode+'/'+name]['within_round_auc']-metrics[mode+'/'+flag]['within_round_auc'],ci95=np.nanquantile(difference,[.025,.975]).tolist())
                    m=flags[flag];metrics[mode+'/'+flag+'_only/'+name]=stream_metrics(rows,ids[m],y[m],scores[name][:,m],folds[:,m],1000)[0]
        result=dict(rows=1995,positives=121,episodes=len({rows[i]['episode'] for i in ids}),counts=counts,metrics=metrics,paired=paired,details=details,definitions={'latest_incoming_protected_read':'final request message is role=tool, linked by tool_call_id to exact read_file of a scenario-initial protected source file; errors remain tool results','previous_call_protected_read':'immediately previous target API response includes exact read_file of a protected source file; malformed names excluded'},no_refit=True)
        lines=['# Does workflow position explain immediate-call prediction?','','Post hoc, input-only structural controls on the same 1,995 calls/121 first-public-emission positives. These controls use no current response. No model was refitted. The last-prompt comparator is the MATCHED immediate-label probe, not the old near-term-channel model.','','Baseline A: the last message in the current request is a tool result linked to an exact `read_file` of a protected source file. Baseline B: the preceding target call requested that read. Both exclude malformed function names; tool-error results still count. Protected source paths are defined from the initial scenario files, without inspecting future outputs.','','| Structural subset | Calls | Positives | Negatives |','|---|---:|---:|---:|']
        for k,c in counts.items():lines.append(f"| {k} | {c['rows']} | {c['positive']} | {c['negative']} |")
        lines+=['','| Split / subset / score | Calls / positives | Within scenario × round AUROC [95% CI] |','|---|---|---|']
        for k,m in metrics.items():
            ci=m['within_round_ci95'];lines.append(f"| {k} | {m['rows']} / {m['positives']} | {m['within_round_auc']:.3f} [{ci[0]:.3f}, {ci[1]:.3f}] |")
        lines+=['','## Paired differences on all calls','']
        for k,v in paired.items():lines.append(f"- {k}: {v['difference']:.3f}, 95% CI [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}].")
        lines+=['','Intervals use 1,000 paired family-bootstrap draws, seed 20261025, averaging seeds 42/43/44. Conditional AUROCs retain only strata with both classes; coverage is in JSON. These diagnostics do not identify a causal mechanism or establish general advance warning.',f'\nScript: experiments/E05-probes/reasoning_stream_immediate_readstep.py. Audit run: {run.dir}. CPU only, USD0.']
        for folder in [out,run.dir]:write_json_atomic(folder/'immediate_readstep.json',result);(folder/'immediate_readstep.md').write_text('\n'.join(lines)+'\n')
        run.result(counts=counts);run.finish();print(json.dumps(dict(counts=counts,paired=paired)),flush=True)
    except BaseException as e:run.finish('failed',str(e));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
