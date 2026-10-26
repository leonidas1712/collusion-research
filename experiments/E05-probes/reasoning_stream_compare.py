"""Join independently scored text comparators without refitting or recalibration."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
import numpy as np
from collusion.runs import write_json_atomic

def append(out,monitor,name='Jev 1.14'):
    plan=json.loads((out/'analysis_plan.json').read_text());data=Path(plan['data']);rows=json.loads((data/'replies.json').read_text())
    wanted={r['row_id']:r for r in rows if r['condition']=='recruiting' and r['stream_window']=='post_ask' and r['reasoning_tokens']>0}
    tasks=json.loads((monitor/'tasks.json').read_text());seen={t['row_id'] for t in tasks if t['evaluation']}
    assert seen==set(wanted) and len(seen)==1995
    assert all(t['request_sha256']==wanted[t['row_id']]['request_sha256'] for t in tasks if t['evaluation'])
    mm=json.loads((monitor/'metrics.json').read_text());ma=json.loads((monitor/'alarms.json').read_text())
    pm=json.loads((out/'metrics.json').read_text());pa=json.loads((out/'alarms.json').read_text());nm=json.loads((out/'causal_null_metrics.json').read_text());na=json.loads((out/'causal_null_alarms.json').read_text());lm=json.loads((out/'reversed_length_metrics.json').read_text())
    records=[]
    for mask in ['all','censored']:
      for mode in ['pooled','loso']:
        key=f'immediate/{mask}/{mode}'
        assert mm[key]['rows']==1995 and mm[key]['positives']==121 and mm[key]['episodes']==238
        def add(method,m,a=None):
            records.append({'method':method,'cut':mask,'split':mode,'rows':1995,'positives':121,'within_auc':m['within_round_auc'],'ci95':m['within_round_ci95'],'warning':float(np.mean(a.get('before_tool_alarm_fraction_by_seed',a.get('immediate_recall_by_seed')))) if a else None,'held_alarm':float(np.mean(a.get('held_reply_alarm_fraction_by_seed',a.get('held_reply_fpr_by_seed')))) if a else None,'crossing_q25_median_q75':a.get('crossing_fraction_q25_median_q75') if a else None})
        add('Reasoning probe MAX',pm[key+'/extended/token_max'],pa[key])
        add('Frozen last-prompt A',pm[key+'/extended/frozen_last_prompt_A'])
        add('Broad keyword MAX',nm[key+'/keyword_broad/max'],na[key+'/keyword_broad/max'])
        add('Reversed final length (retrospective)',lm[key+'/extended/reasoning_length'])
        add(name+' sampled-prefix MAX',mm[key],ma[key])
    tag=name.lower().replace(' ','-').replace('.','-');write_json_atomic(out/('comparison-'+tag+'.json'),{'monitor_source':str(monitor),'exact_row_and_hash_match':True,'redacted_prefix_tasks':sum(t['redacted'] for t in tasks),'records':records})
    lines=['\n## Immediate-reply probe and text comparison: '+name,'','All rows use the identical 1,995 replies, 121 immediate any-public positives, and 238 recruiting episodes. Row IDs and request hashes match exactly. Intervals use the same family bootstrap; alarms retain each method’s own saved-fold control-reply threshold with strict > at nominal 5%. No recalibration is performed by this join.','','| Cut | Split | Method | Within scenario × round AUROC [95% CI] | Leak warning | Held-reply alarm |','|---|---|---|---|---:|---:|']
    for r in records:
        lo,hi=r['ci95'];rate=lambda v:'Not evaluated' if v is None else f'{v:.1%}'
        lines.append(f"| {r['cut']} | {r['split']} | {r['method']} | {r['within_auc']:.3f} [{lo:.3f}, {hi:.3f}] | {rate(r['warning'])} | {rate(r['held_alarm'])} |")
    lines+=['','The text monitor reads up to six cumulative prefixes per reply; the activation probe scores every saved reasoning token. This makes text crossing times coarser and can also miss score peaks, potentially changing MAX ranking; equal ranking resolution has not been established. Crossing fractions are conditional on alarms and should not be treated as matched latency measurements. Exact-value suffixes were redacted in text; all and censored text scores coincide in this run, but redaction is not identical to the activation intervention. The value of a semantic text comparison is not exhausted by the fixed keyword baseline.','','The keyword rule’s zero alarms arise from its binary score and control threshold of 1. Reversed final length is a retrospective diagnostic, not an online alarm. The frozen last-prompt comparator has a different training label. These distinctions prevent interpreting the entire table as an isolated test of activation position.','','Source: `'+str(monitor)+'/report.md`; exact billed costs, prompt hash, cache and prefix sampling are recorded there. This analysis is post hoc; no paper result is replaced.']
    if name=='GPT-5-nano':
        lines+=['','Nano-specific deviation: the canonical run uses minimal reasoning and strict score JSON. The paper-style low-reasoning attempt exhausted its completion allowance and is excluded from performance estimates. Canonical billed cost USD0.11473730 plus discarded-attempt USD0.03575890 gives USD0.15049620 total. Scores are retained in their original direction; the below-chance result is not reversed after seeing outcomes.']
    heading='\n## Immediate-reply probe and text comparison: '+name
    p=out/'report.md';old=p.read_text();old=old.split(heading)[0] if heading in old else old
    p.write_text(old+'\n'.join(lines)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--monitor',type=Path,required=True);p.add_argument('--name',default='Jev 1.14');a=p.parse_args();append(a.out,a.monitor,a.name)
