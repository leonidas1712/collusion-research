"""Summarize saved per-call generation settings without exposing prompt contents."""
import argparse,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic
from arxiv_text_workflow import source_data

def main(restore):
    result={}
    for model in ['qwen','gpt']:
        rows,_,_,_=source_data(model,restore);cache={};counts={k:Counter() for k in ['model','temperature','max_tokens','reasoning','requested_providers','requested_quantizations']}
        for r in rows:
            if r['episode'] not in cache:
                folder,name=r['episode'].split('/');rel=Path('runs')/folder/'episodes'/name;p=ROOT/rel if (ROOT/rel).exists() else restore/rel;cache[r['episode']]=json.loads(p.read_text())
            q=cache[r['episode']]['requests'][r['request_idx']]['request'];extra=q.get('extra_body',{});provider=extra.get('provider',{})
            vals={k:q.get(k) for k in ['model','temperature','max_tokens']};vals.update(reasoning=q.get('reasoning',extra.get('reasoning')),requested_providers=provider.get('only',provider.get('order')),requested_quantizations=provider.get('quantizations'))
            for k,v in vals.items():counts[k][json.dumps(v,sort_keys=True)]+=1
        result[model]=dict(calls=len(rows),episodes=len(cache),families=len({r['family'] for r in rows}),settings={k:dict(v) for k,v in counts.items()},source='saved requests; requested provider settings are not per-call served-provider evidence')
    run=start_run('e05-arxiv-settings-audit',experiment='E05',tags=['cpu-only'],settings={'no_api':True,'no_gpu':True})
    write_json_atomic(run.dir/'settings.json',result);run.result(all_calls_inspected=True);run.finish();print(run.dir);print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--restore-root',type=Path,required=True);main(p.parse_args().restore_root)
