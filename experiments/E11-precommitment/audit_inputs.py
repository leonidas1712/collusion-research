"""Reconstruct every masked input without reading monitor or outcome scores."""
import json
from pathlib import Path
import sys
from collections import Counter
from precommitment import ROOT, OLD, digest, sha, body, verified

run=Path(sys.argv[1]).resolve();plan,payloads=verified(run)
rows=json.loads((run/'rows.json').read_text());counts=Counter();eps={}
for r in rows:
    rn,nm=r['episode'].split('/');p=next(root/'runs'/rn/'episodes'/nm for root in (ROOT,OLD) if (root/'runs'/rn/'episodes'/nm).exists())
    if p not in eps:
        assert sha(p.read_bytes())==plan['episode_source_hashes'][str(p)]
        eps[p]=json.loads(p.read_text())
    ep=eps[p];record=ep['requests'][int(r['row_id'].rsplit('=',1)[1])];messages=record['request']['messages']
    last_user=max(i for i,m in enumerate(messages) if m['role']=='user')
    rebuilt=[]
    for i,m in enumerate(messages):
        if m['role']!='assistant':continue
        keep={}
        for k in ('content','tool_calls'):
            if m.get(k):keep[k]=m[k]
        retains=(r['model']=='gpt-oss' and record['served_provider']=='AkashML' and i>last_user)
        if retains and m.get('reasoning'):keep['reasoning']=m['reasoning'];counts['retained_reasoning_messages']+=1
        if keep:rebuilt.append(keep)
    text=json.dumps(rebuilt,ensure_ascii=False)
    for secret in sorted(ep['scenario_spec']['honeypots'],key=len,reverse=True):text=text.replace(secret,'[PROTECTED_VALUE]')
    assert text==r['prior_text']
    assert body(text)==payloads[r['payload_key']]
    assert digest(body(text))==r['payload_key']
    assert all(secret not in json.dumps(body(text),ensure_ascii=False) for secret in ep['scenario_spec']['honeypots'])
    counts[r['model']]+=1
    counts['calls_with_retained_reasoning']+=any('reasoning' in m for m in rebuilt)
output=dict(counts=counts,episode_files=len(eps),input_reconstruction=True,source_hashes_verified=True,exact_values_absent=True,current_reply_excluded=True,plan_commit='f329cbd',provider_reasoning_rule_source='experiments/E02-activation-replay/run_stream_confirmation.py')
(run/'input_audit.json').write_text(json.dumps(output,indent=2));print(json.dumps(output))
