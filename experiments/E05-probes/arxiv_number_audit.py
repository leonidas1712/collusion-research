"""Independently recalculate displayed AUROCs from committed score exports."""
import csv,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from sklearn.metrics import roc_auc_score
from collusion.runs import start_run,write_json_atomic

def read(p):
    with gzip.open(p,'rt') as f:return list(csv.DictReader(f))
def auc(rows,key):
    strata={}
    for r in rows:strata.setdefault((r['scenario'],int(r['round'])),[]).append(r)
    n=0;total=0
    for sub in strata.values():
        y=np.array([int(r['label']) for r in sub]);score=np.array([float(r[key]) for r in sub])
        if len(set(y))<2:continue
        weight=y.sum();total+=weight*roc_auc_score(y,score);n+=weight
    return total/n if n else None

def main():
    run=start_run('e05-arxiv-number-audit',experiment='E05',tags=['cpu-only','verification'],settings={'independent_implementation':'sklearn roc_auc_score per scenario-round; weight by positives; mean seeds'})
    results=[];sources={}
    try:
      for folder in ['20261026-2201-e05-arxiv-qwen-any-public','20261026-2229-e05-arxiv-qwen-any-public','20261026-2223-e05-arxiv-qwen-strict-next','20261026-2212-e05-arxiv-qwen-fresh-percall','20261026-2222-e05-arxiv-gpt-fresh-percall','20261026-2242-e05-arxiv-gpt-text-workflow','20261026-2245-e05-arxiv-qwen-text-workflow']:
        d=ROOT/'runs'/folder;p=d/('scores.csv.gz' if 'text-workflow' in folder else 'probe_scores.csv.gz');rows=read(p);m=json.loads((d/'metrics.json').read_text());sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        if 'text-workflow' in folder:
            methods=['last_prompt','full_input','latest_input','write_file','handoff_write'];groups={'same_calls':rows}
        else:
            methods=['score'];groups={}
            for r in rows:groups.setdefault(r.get('label_variant','fresh')+'/'+r.get('analysis','fresh'),[]).append(r)
        for group,sub in groups.items():
          for method in methods:
            seeds=sorted({r.get('seed','ensemble') for r in sub});points=[auc([r for r in sub if r.get('seed','ensemble')==s],method) for s in seeds];value=float(np.mean(points))
            if 'text-workflow' in folder:expected=m['metrics'][method]['within_round_auc']
            elif 'strict-next' in folder or 'fresh-percall' in folder:expected=m['within_round_auc']
            else:expected=m[group]['within_round_auc']
            assert abs(value-expected)<1e-12,(folder,group,method,value,expected)
            results.append(dict(run=folder,group=group,method=method,auc=value,stored_auc=expected,absolute_error=abs(value-expected),seeds=seeds))
      write_json_atomic(run.dir/'verification.json',dict(all_pass=True,checks=len(results),maximum_absolute_error=max(r['absolute_error'] for r in results),results=results,sources=sources,api_spend_usd=0,gpu_spend_usd=0))
      run.result(checks=len(results),all_pass=True);run.finish();print(run.dir,flush=True)
    except BaseException as e:run.finish('failed',str(e));raise
if __name__=='__main__':main()
