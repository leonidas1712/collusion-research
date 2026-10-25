"""Audit saved peer-to-target message projection without issuing API calls."""
import argparse
import hashlib
import json
from pathlib import Path
from gemma_gate import ROOT
from collusion.runs import start_run, write_json_atomic


def audit(ep):
    spec=ep['scenario_spec'];channel=ep['channel']
    public=[e['content'] for e in channel]
    expected={spec['channel_format'].format(actor='recruiter',name=spec['actor_names']['recruiter'],content=e['content'])
              for e in channel if e['actor']=='recruiter'}
    target_messages=[m for r in ep['requests'] if r['actor']=='target' for m in r['request']['messages']]
    unexpected=[m for m in target_messages if m['role']=='user' and m['content']!=spec['target_task'] and m['content'] not in expected]
    fields=[]
    for i,r in enumerate(ep['requests']):
        if r['actor']!='recruiter' or not r.get('response'):continue
        m=r['response']['choices'][0]['message']
        parts=[m.get('reasoning')]+[d.get('text') for d in m.get('reasoning_details') or []]
        for text in set(p for p in parts if isinstance(p,str) and p.strip()):
            fields.append(dict(request_idx=i,characters=len(text),sha256=hashlib.sha256(text.encode()).hexdigest(),
                               appears_in_public=any(text in x for x in public),
                               informative_public_match=any(text in x and (len(text)>=32 or text.strip()==x.strip()) for x in public),
                               appears_in_target=any(text in json.dumps(x,ensure_ascii=False) for x in target_messages),
                               informative_target_match=any(text in json.dumps(x,ensure_ascii=False) and
                                   (len(text)>=32 or text.strip()==str(x.get('content','')).strip()) for x in target_messages)))
    return dict(status=ep['status'],rounds_completed=ep.get('rounds_completed'),
                unexpected_target_user_messages=len(unexpected),peer_reasoning_segments=len(fields),
                peer_reasoning=fields,reasoning_observed=bool(fields),passed=not unexpected and not any(
                    x['informative_public_match'] or x['informative_target_match'] for x in fields))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('episode');a=p.parse_args()
    source=Path(a.episode).resolve();ep=json.loads(source.read_text())
    run=start_run('e03-peer-reasoning-isolation',experiment='E03',parents=[source.parent.parent.name],settings={'episode':str(source.relative_to(ROOT))})
    result=audit(ep);write_json_atomic(run.dir/'audit.json',result)
    run.result(passed=result['passed'],segments=result['peer_reasoning_segments']);run.finish();print(run.dir);print(result['passed'])
