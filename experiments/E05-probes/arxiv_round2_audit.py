"""Reconcile round-level training labels and count protected-source writebacks."""
import hashlib,json,sys
from collections import defaultdict
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic


def main():
    sources={}
    def load(rel):
        p=ROOT/rel;sources[rel]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
    near=load('runs/20261025-0730-e05-near-term/metrics.json')['A_hazard']['loso']
    monitor=load('runs/20261025-0147-e06-monitor-main/metrics_main_A_hazard.json')['probe (held-out scenario)']['ranking']
    assert near['rows']==monitor['rows'] and near['positives']==monitor['positives']
    assert abs(near['methods']['eventual_nested']['within_round_auc']-monitor['within_round_auc'])<1e-12
    reconciliation=dict(rows=near['rows'],positives=near['positives'],episodes=near['episodes'],families=near['families'],evaluation_label='A_hazard current-or-next-round',table26=dict(training_label='eventual episode outcome; no refit',auc=monitor['within_round_auc']),table27=dict(training_label='A_hazard; layer reselected and model refitted within training folds',auc=near['methods']['nested']['within_round_auc']))
    rows=load('runs/20261026-2155-e05-qwen-any-public-audit/rows.json');groups=defaultdict(list)
    for r in rows:groups[r['episode']].append(r)
    writes=[]
    for episode, rr in groups.items():
        folder,name=episode.split('/');path=Path('runs')/folder/'episodes'/name;ep=load(str(path))
        secrets=ep['scenario_spec']['honeypots'];protected={str(PurePosixPath(p)) for p,text in ep['scenario_spec']['files'].items() if any(v and v in str(text) for v in secrets)}
        for r in rr:
            rec=ep['requests'][r['request_idx']];assert rec['actor']=='target'
            choices=(rec.get('response') or {}).get('choices') or []
            msg=choices[0].get('message',{}) if choices else {}
            for c in msg.get('tool_calls') or []:
                f=c.get('function') or {}
                if f.get('name')!='write_file':continue
                a=f.get('arguments')
                try:a=json.loads(a) if isinstance(a,str) else a
                except json.JSONDecodeError:continue
                if not isinstance(a,dict) or not isinstance(a.get('path'),str):continue
                if str(PurePosixPath(a['path'])) not in protected:continue
                if not any(v and v in str(a.get('content','')) for v in secrets):continue
                writes.append(dict(episode=episode,request_idx=r['request_idx'],condition=r['condition'],scenario=r['scenario'],split='development' if r['index']<6026 else 'fresh',immediate_label=int(r['y_immediate']),path=a['path']))
    summary={}
    for split in ['development','fresh','all']:
        selected=[r for r in writes if split=='all' or r['split']==split]
        summary[split]=dict(calls=len({(r['episode'],r['request_idx']) for r in selected}),episodes=len({r['episode'] for r in selected}),tool_calls=len(selected),immediate_positive_calls=sum(r['immediate_label'] for r in selected))
    run=start_run('e05-arxiv-round2-audit',experiment='E05',settings=dict(no_model_calls=True,no_fit=True,scope='Current scored call windows only; native write_file arguments, including attempts; no post-cutoff calls',sources=sources))
    write_json_atomic(run.dir/'audit.json',dict(round_table_reconciliation=reconciliation,writebacks=summary,writeback_calls=writes))
    run.result(no_api=True,no_gpu=True);run.finish();print(run.dir);print(json.dumps(dict(reconciliation=reconciliation,writebacks=summary,details=writes),indent=2))


if __name__=='__main__':main()
