"""Summarize a downloaded replay benchmark and its Modal billing snapshot."""
import argparse
import json
import subprocess
from pathlib import Path
from statistics import median
from collusion.runs import start_run

p=argparse.ArgumentParser()
p.add_argument('replay_dir',type=Path)
p.add_argument('--apps',nargs='+',required=True)
p.add_argument('--clients',nargs='+',required=True)
a=p.parse_args()
r=start_run('e02-modal-benchmark-report',experiment='E02',parents=[a.replay_dir.name,*a.clients],settings={'apps':a.apps,'replay_dir':str(a.replay_dir)})
rows=[json.loads(line) for line in (a.replay_dir/'index.jsonl').read_text().splitlines()]
summary=json.loads((a.replay_dir/'summary.json').read_text())
provenance=json.loads((a.replay_dir/'provenance.json').read_text())
scored=[row for row in rows if 'mean_token_nll' in row['reply_fidelity']]
n=sum(row['reply_fidelity']['n_reply_tokens'] for row in scored)
prompt_tokens=sum(row['n_tokens'] for row in rows)
activation_seconds=sum(row['activation_seconds'] for row in rows)
total_seconds=sum(row['total_seconds'] for row in rows)
billing=json.loads(subprocess.check_output(['modal','billing','report','--for','today','--resolution','h','--show-resources','--json'],text=True))
billing=[row for row in billing if row['object_id'] in a.apps]
(r.dir/'billing.json').write_text(json.dumps(billing,indent=2))
rates=json.loads(subprocess.check_output(['modal','billing','rates','--json'],text=True))
rates={k:v for k,v in rates.items() if k in ['cpu_hour_cost','gpu_hour_cost_a100_80gb','mem_gib_hour_cost','volume_storage_gib_month_cost','egress_gib_cost']}
(r.dir/'rates.json').write_text(json.dumps(rates,indent=2))
result={'requests':len(rows),'prompt_tokens':prompt_tokens,'activation_seconds':activation_seconds,'activation_prompt_tokens_per_second':prompt_tokens/activation_seconds,
 'activation_and_fidelity_seconds':total_seconds,'effective_prompt_tokens_per_second_with_fidelity':prompt_tokens/total_seconds,
 'scored_requests':len(scored),'reply_tokens':n,'weighted_mean_token_nll':sum(row['reply_fidelity']['mean_token_nll']*row['reply_fidelity']['n_reply_tokens'] for row in scored)/n if n else None,
 'weighted_top5_fraction':sum(row['reply_fidelity']['top5_fraction']*row['reply_fidelity']['n_reply_tokens'] for row in scored)/n if n else None,
 'median_request_nll':median(row['reply_fidelity']['mean_token_nll'] for row in scored) if scored else None,
 'reported_billing_usd':sum(float(row['cost']) for row in billing),'billing_may_lag':True,
 'model_load_seconds':summary.get('model_load_seconds'),'peak_cuda_memory_bytes':summary.get('peak_cuda_memory_bytes'),'device_map':provenance['device_map']}
(r.dir/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));r.result(**result)
