"""Offline DekaLLM tool-argument serialization diagnostic."""
import copy
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic
from gpt_oss_replay import render


def main():
    source=ROOT/'runs/20261025-2229-e02-gpt-oss-provider-template-audit/rows.json'
    selected=[r for r in json.loads(source.read_text()) if r['provider']=='DekaLLM']
    run=start_run('e02-gpt-oss-tool-format-audit',experiment='E02',parents=[source.parent.name],settings={'offline':True})
    cache={};rows=[];counts=defaultdict(Counter)
    modes={'spaces':{},'sorted':{'sort_keys':True},'compact':{'separators':(',',':')},'indent2':{'indent':2}}
    try:
        for r in selected:
            run_id,name=r['episode'].split('/');path=ROOT/'runs'/run_id/'episodes'/name
            if r['episode'] not in cache:cache[r['episode']]=json.loads(path.read_text())
            record=cache[r['episode']]['requests'][r['request_idx']];date=time.strftime('%Y-%m-%d',time.gmtime(record['response']['created']))
            out=dict(episode=r['episode'],request_idx=r['request_idx'],provider_tokens=r['provider_tokens'],tokens={})
            for mode,options in modes.items():
                rec=copy.deepcopy(record)
                for msg in rec['request']['messages']:
                    for call in msg.get('tool_calls') or []:
                        fn=call['function']
                        try:fn['arguments']=json.dumps(json.loads(fn['arguments']),ensure_ascii=False,**options)
                        except (ValueError,TypeError):pass
                n=len(render(rec,date)['prompt_ids']);out['tokens'][mode]=n;counts[mode][n-r['provider_tokens']]+=1
            rows.append(out)
        summary={mode:dict(exact=c[0],within1=sum(n for d,n in c.items() if abs(d)<=1),max_absolute=max(abs(d) for d in c),deltas=dict(c)) for mode,c in counts.items()}
        write_json_atomic(run.dir/'counts.json',summary);write_json_atomic(run.dir/'rows.json',rows);run.result(**summary);run.finish();print(run.dir)
        for mode,r in summary.items():print(mode,{k:v for k,v in r.items() if k!='deltas'},Counter(r['deltas']).most_common(8))
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':main()
