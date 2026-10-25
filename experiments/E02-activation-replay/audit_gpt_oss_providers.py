"""Offline provider prompt-count diagnostic; no replay or token-stream substitution."""
import copy
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic
from gpt_oss_replay import render


def main():
    manifest_path=ROOT/'runs/20261025-2212-e03-gpt-oss-full-collection/manifest.json'
    raw=manifest_path.read_bytes();manifest=json.loads(raw)
    run=start_run('e02-gpt-oss-provider-template-audit',experiment='E02',parents=[manifest_path.parent.name],
        settings={'source_manifest_sha256':hashlib.sha256(raw).hexdigest(),'operation':'offline count-only variants; no GPU/API'})
    rows=[];deltas=defaultdict(Counter)
    try:
        for epnum,entry in enumerate(manifest['episodes'],1):
            path=ROOT/entry['episode_file'];raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==entry['episode_sha256']
            ep=json.loads(raw)
            for idx,record in enumerate(ep['requests']):
                if record['actor']!='target':continue
                resp=record.get('response') or {};usage=resp.get('usage') or {};provider=resp.get('provider') or record.get('served_provider')
                date=time.strftime('%Y-%m-%d',time.gmtime(resp['created']))
                base=copy.deepcopy(record);msgs=base['request']['messages']
                last_user=max((i for i,m in enumerate(msgs) if m['role']=='user'),default=-1)
                # Keep analysis only after the latest user/peer message, i.e. within this tool-use turn.
                for i,m in enumerate(msgs):
                    if i<last_user:m.pop('reasoning',None);m.pop('reasoning_details',None)
                variants={'drop_all':render(record,date),'keep_all':render(record,date,True),'current_turn':render(base,date,True)}
                row=dict(episode=entry['run_id']+'/'+path.name,request_idx=idx,provider=provider,provider_tokens=usage.get('prompt_tokens'),round=record['round'])
                row['tokens']={mode:len(value['prompt_ids']) for mode,value in variants.items()}
                rows.append(row)
                if row['provider_tokens'] is not None:
                    for mode,n in row['tokens'].items():deltas[(provider,mode)][n-row['provider_tokens']]+=1
            if epnum%60==0:print('AUDITED',epnum,len(rows),flush=True)
        summary=[]
        for (provider,mode),counts in sorted(deltas.items()):
            summary.append(dict(provider=provider,mode=mode,n=sum(counts.values()),exact=counts[0],within1=sum(v for k,v in counts.items() if abs(k)<=1),
                max_absolute=max(abs(k) for k in counts),deltas=dict(counts)))
        write_json_atomic(run.dir/'counts.json',summary);write_json_atomic(run.dir/'rows.json',rows)
        run.result(summary=summary);run.finish();print('AUDIT',run.dir)
        for r in summary:print({k:v for k,v in r.items() if k!='deltas'},'common',Counter(r['deltas']).most_common(8))
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':main()
