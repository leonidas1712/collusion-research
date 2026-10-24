"""Offline manifest preflight and bounded reply-token cost estimate."""
import json
import sys
from collections import Counter
from pathlib import Path
from transformers import AutoTokenizer
from replay import ROOT, start_run, final_episodes, render
from replay_manifest import load_manifest, select_manifest
from fidelity import reply_tokens
from plan_main import MODEL, REVISION


def main():
    path=Path(sys.argv[1]); rows=load_manifest(path)
    run=start_run('e02-fidelity-plan',experiment='E02',parents=[path.parent.name],settings={'model':MODEL,'revision':REVISION,'reply_token_limit':64,'planning_only':True})
    tok=AutoTokenizer.from_pretrained(MODEL,revision=REVISION,local_files_only=True)
    episodes=final_episodes([ROOT/'runs'/name for name in dict.fromkeys(r['run_id'] for r in rows)])
    selection,metadata=select_manifest(path,episodes,tok,'from-request')
    out=[];statuses=Counter()
    for _,source,_ in episodes:
        for idx,_,record in selection[source]:
            prompt,ids,_,thinking=render(tok,record['request'],'from-request')
            reply,status=reply_tokens(tok,record['request'],record,prompt,thinking)
            statuses[status]+=1
            out.append(dict(episode_file=metadata[(source,idx)]['episode_file'],request_idx=idx,
                n_prompt_tokens=len(ids),n_full_reply_tokens=len(reply or []),n_scored_reply_tokens=min(64,len(reply or [])),status=status))
    prompt=sum(r['n_prompt_tokens'] for r in out);extra=sum(r['n_scored_reply_tokens'] for r in out)
    bench=json.loads((ROOT/'runs/20261024-1556-e02-modal-benchmark-report/results.json').read_text())
    base_seconds=bench['activation_seconds'];n_bench=bench['requests'];throughput=bench['activation_prompt_tokens_per_second']
    # Old benchmark used an extra decoder pass plus head projection: subtract the
    # measured prompt decoder pass again to bound its residual scoring overhead.
    old_extra=max(0,bench['activation_and_fidelity_seconds']-2*base_seconds)
    residual_per_call=old_extra/n_bench
    lower=(prompt+extra)/throughput+54
    upper=len(out)*base_seconds/n_bench+extra/throughput+len(out)*residual_per_call+54
    result=dict(estimated_wall_minutes=[lower/60,upper/60],estimated_compute_usd=[lower*2.9452/3600,upper*3.2012/3600],
        head_overhead_allowance_seconds=len(out)*residual_per_call,requests=len(out),prompt_tokens=prompt,extra_reply_tokens=extra,
        combined_tokens=prompt+extra,extra_token_fraction=extra/prompt,statuses=dict(statuses),
        decoder_extra_seconds_token_linear=extra/throughput,
        decoder_extra_cost_usd=extra/throughput*3.2012/3600,
        benchmark_residual_head_overhead_seconds=old_extra)
    (run.dir/'requests.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in out))
    (run.dir/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));run.result(**result);run.finish();print(run.id)

if __name__=='__main__':main()
