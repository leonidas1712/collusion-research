"""Paired comparisons and alarms from saved fresh-test scores; no model scoring."""
import csv,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from collusion.runs import start_run,write_json_atomic
from reasoning_stream_report import stream_metrics

def main():
 run=start_run('e05-arxiv-fresh-comparisons',experiment='E05',settings={'saved_scores_only':True,'no_api':True,'no_gpu':True})
 try:
  results={}
  for model,source,comparison in [
   ('qwen',ROOT/'runs/20261026-2212-e05-arxiv-qwen-fresh-percall',ROOT/'runs/20261026-1309-e06-percall-input-jev-qwen/probe_scores.csv'),
   ('gpt_oss',ROOT/'runs/20261026-2222-e05-arxiv-gpt-fresh-percall',Path('/Users/leo/collusion-research/runs/20261026-1302-e05-stream-confirm-score/probe_scores.csv'))]:
    with gzip.open(source/'probe_scores.csv.gz','rt') as f:rows=list(csv.DictReader(f))
    for r in rows:r['round']=int(r['round']);r['label']=int(r['label']);r['score']=float(r['score'])
    lookup={r['row_id']:r for r in csv.DictReader(comparison.open())}
    assert all(r['row_id'] in lookup and r['request_sha256']==lookup[r['row_id']]['request_sha256'] for r in rows)
    y=np.array([r['label'] for r in rows]);ids=np.arange(len(rows));fold=np.zeros((1,len(rows)),int)
    scores=np.array([r['score'] for r in rows])[None,:]
    other=np.array([float(lookup[r['row_id']]['score' if model=='qwen' else 'max_score']) for r in rows])[None,:]
    m,mb=stream_metrics(rows,ids,y,scores,fold,1000);n,nb=stream_metrics(rows,ids,y,other,fold,1000)
    d=mb['within_round']-nb['within_round'];threshold=json.loads((source/'metrics.json').read_text())['threshold'];hits=scores[0]>threshold
    if model=='qwen':
      source_rows=json.loads((ROOT/'runs/20261026-2155-e05-qwen-any-public-audit/rows.json').read_text());ever={f"{r['episode']}::request_idx={r['request_idx']}":r['y_eventual'] for r in source_rows}
    else:ever={k:int(v['ever_public']=='True') for k,v in lookup.items()}
    held=np.array([not ever[r['row_id']] for r in rows]);eps={r['episode'] for r,h in zip(rows,held) if h}
    alarms=dict(leak_caught=int(sum(hits&(y==1))),leak_total=int(y.sum()),leak_rate=float(hits[y==1].mean()),refusing_calls=int(held.sum()),refusing_alarm=int(sum(hits&held)),refusing_rate=float(hits[held].mean()),refusing_episodes=len(eps),refusing_episode_alarms=sum(any(hits[i] for i,r in enumerate(rows) if r['episode']==e) for e in eps))
    alarms['refusing_episode_rate']=alarms['refusing_episode_alarms']/len(eps)
    results[model]=dict(probe=m,comparator=n,comparator_name='Jev input' if model=='qwen' else 'frozen reasoning MAX',paired_difference=dict(value=m['within_round_auc']-n['within_round_auc'],ci95=np.nanquantile(d,[.025,.975]).tolist()),alarms=alarms,coverage=len(rows))
  write_json_atomic(run.dir/'metrics.json',results);run.result(saved_scores_only=True);run.finish();print(run.dir);print(json.dumps(results,indent=2))
 except BaseException as e:run.finish('failed',str(e));raise
if __name__=='__main__':main()
