"""Summarize existing group coverage, alarm decisions, and sampling settings."""
import argparse,csv,gzip,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic
from near_term import label_rows
from arxiv_text_workflow import source_data

def read(p):
    with (gzip.open(p,'rt') if p.suffix=='.gz' else p.open()) as f:return list(csv.DictReader(f))
def main(restore):
    sources={};sets={}
    def load(rel):
        p=ROOT/rel if (ROOT/rel).exists() else restore/rel;assert p.exists(),p;sources[rel]=hashlib.sha256(p.read_bytes()).hexdigest();return read(p)
    for target,rel in [('Qwen','runs/20261026-2201-e05-arxiv-qwen-any-public/probe_scores.csv.gz'),('GPT','runs/20261026-1304-e05-lastprompt-label-ladder/probe_scores.csv.gz')]:
      for r in load(rel):
        if r['analysis']=='loso' and r['seed']=='42':sets.setdefault(target+'/development/'+r['label_variant'],[]).append(r)
    for r in load('runs/20261026-1221-e05-lastprompt-percall-6013/probe_scores.csv.gz'):
        if r['analysis']=='loso' and r['seed']=='42' and r['cohort']=='matched' and r['label_variant'] in ['immediate','strict1']:sets.setdefault('GPT/development/'+r['label_variant'],[]).append(r)
    for target,rel in [('Qwen','runs/20261026-2212-e05-arxiv-qwen-fresh-percall/probe_scores.csv.gz'),('GPT','runs/20261026-2222-e05-arxiv-gpt-fresh-percall/probe_scores.csv.gz')]:sets[target+'/fresh/immediate']=load(rel)
    strict=load('runs/20261026-2223-e05-arxiv-qwen-strict-next/probe_scores.csv.gz');sets['Qwen/development/strict_next']=[r for r in strict if r['seed']=='42']
    rel='runs/20261025-1026-e05-replay3-data/rows.jsonl';p=restore/rel;sources[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    original=[json.loads(line) for line in p.read_text().splitlines()];keep,labels=label_rows(original,'A_hazard')
    assert int(keep.sum())==1787 and int(labels[keep].sum())==82
    sets['Qwen/fresh/original_round_A']=[dict(row_id=f"{r['episode']}::{r['ordinal']}",scenario=r['scenario'],round=r['round'],label=int(labels[i])) for i,r in enumerate(original) if keep[i]]
    summary={};groups=[]
    for key,rows in sets.items():
        assert len({r['row_id'] for r in rows})==len(rows);strata=defaultdict(list)
        for r in rows:strata[(r['scenario'],int(r['round']))].append(int(r['label']))
        retained_positive=retained_calls=retained_groups=0
        for (scenario,round_),labels in sorted(strata.items()):
            pos=sum(labels);neg=len(labels)-pos;keep=pos>0 and neg>0
            groups.append(dict(test=key,scenario=scenario,round=round_,calls=len(labels),positive=pos,negative=neg,retained=keep))
            if keep:retained_positive+=pos;retained_calls+=len(labels);retained_groups+=1
        summary[key]=dict(calls=len(rows),positives=sum(int(r['label']) for r in rows),retained_calls=retained_calls,retained_positives=retained_positive,groups=len(strata),retained_groups=retained_groups)
    qrows=json.loads((ROOT/'runs/20261026-2155-e05-qwen-any-public-audit/rows.json').read_text());fresh={f"{r['episode']}::request_idx={r['request_idx']}":r for r in qrows if r['index']>=6026 and r['condition']=='recruiting'}
    threshold_file=ROOT/'runs/20261026-1309-e06-percall-input-jev-qwen/thresholds.json';thresholds={(str(r['seed']),str(r['fold'])):r['threshold'] for r in json.loads(threshold_file.read_text())['loso']}
    alarms={}
    for seed in ['42','43','44']:
        calls=[r for r in load('runs/20261026-1309-e06-percall-input-jev-qwen/probe_scores.csv') if r['analysis']=='loso' and r['seed']==seed and r['row_id'] in fresh]
        assert len(calls)==1825;hits={r['row_id']:float(r['score'])>thresholds[(seed,r['fold'])] for r in calls};pos=[k for k,v in fresh.items() if v['y_immediate']];held=[k for k,v in fresh.items() if not v['y_eventual']];eps={fresh[k]['episode'] for k in held}
        alarms[seed]=dict(caught=sum(hits[k] for k in pos),leaking_calls=len(pos),refusing_alarm=sum(hits[k] for k in held),refusing_calls=len(held),refusing_episode_alarms=sum(any(hits[k] for k in held if fresh[k]['episode']==e) for e in eps),refusing_episodes=len(eps))
    rate_fields={'caught_rate':('caught','leaking_calls'),'refusing_rate':('refusing_alarm','refusing_calls'),'refusing_episode_rate':('refusing_episode_alarms','refusing_episodes')};alarm_rates={k:sum(v[a]/v[b] for v in alarms.values())/3 for k,(a,b) in rate_fields.items()}
    peer={}
    for model in ['qwen','gpt']:
        rows,_,_,_=source_data(model,restore);episodes={r['episode'] for r in rows};c=Counter()
        for episode in episodes:
            folder,name=episode.split('/');rel=Path('runs')/folder/'episodes'/name;p=ROOT/rel if (ROOT/rel).exists() else restore/rel;ep=json.loads(p.read_text())
            for record in ep['requests']:
                if not str(record.get('actor','')).startswith('recruiter'):continue
                q=record['request'];extra=q.get('extra_body',{});v={k:q.get(k) for k in ['model','temperature','max_tokens']};v['reasoning']=q.get('reasoning',extra.get('reasoning'));c[json.dumps(v,sort_keys=True)]+=1
        peer[model]=[dict(settings=json.loads(k),requests=n) for k,n in sorted(c.items())]
    run=start_run('e05-arxiv-final-records',experiment='E05',tags=['cpu-only','existing-records'],settings={'no_new_analysis_or_fit':True,'sources':sources})
    write_json_atomic(run.dir/'summary.json',dict(group_coverage=summary,qwen_fresh_jev_alarm_by_seed=alarms,qwen_fresh_jev_alarm_rates=alarm_rates,peer_sampling=peer,alarm_source='Saved LOSO control-call cutoffs from original all-data monitor analysis; not the newly frozen development-only probe threshold',fresh_gpt_reasoning_coverage='Identical594 calls/26 positives to GPT fresh immediate input probe'))
    with (run.dir/'group_counts.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(groups[0]));w.writeheader();w.writerows(groups)
    run.result(no_fit=True,no_api=True,no_gpu=True);run.finish();print(run.dir);print(json.dumps(summary,indent=2));print(json.dumps(peer,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--restore-root',type=Path,required=True);main(p.parse_args().restore_root)
