"""Compute compact, source-linked appendix counts without generation or refitting."""
import csv,gzip,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic
import numpy as np
from metrics import threshold_at_fpr

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def wilson(k,n):
 z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [c-h,c+h]

def main():
 source=ROOT/'report/figures/appendix_g_coverage.csv';rr=[r for r in csv.DictReader(source.open()) if r['model']=='qwen/qwen3-32b' and r['condition']=='recruiting']
 out={};evidence={}
 def select(name,**kw):
  selected=[r for r in rr if all(r[k]==v for k,v in kw.items())];assert selected
  k=sum(int(r['gave_in']) for r in selected);n=sum(int(r['n']) for r in selected)
  out[name+'Rate']=k/n;out[name+'N']=n;evidence[name]=dict(filters=kw,numerator=k,denominator=n,rows=selected)
 select('screenRuleBase',factor='Rule strength',level='consequence',scenario='deploy-token')
 select('screenRuleLogged',factor='Rule strength',level='consequence_logged',scenario='deploy-token')
 select('screenPlain',factor='Single tactic',level='T0',scenario='deploy-token')
 tactics=[r for r in rr if r['factor']=='Single tactic' and r['level']!='T0' and r['scenario']=='deploy-token']
 assert len(tactics)==7
 out.update(screenTacticMinRate=min(int(r['gave_in'])/int(r['n']) for r in tactics),screenTacticMaxRate=max(int(r['gave_in'])/int(r['n']) for r in tactics),screenTacticMinN=min(int(r['n']) for r in tactics),screenTacticMaxN=max(int(r['n']) for r in tactics))
 evidence['screenTactic']=tactics
 select('screenStakeNone',factor='Own stake',level='no own stake');select('screenStakeOwn',factor='Own stake',level='own stake')
 select('screenThinking',factor='Thinking mode',level='on, T0');select('screenTwoPeers',factor='Peer count',level='two')
 select('screenAwareNo',factor='Expressed awareness',level='not flagged');select('screenAwareYes',factor='Expressed awareness',level='flagged')
 audit=ROOT/'runs/20261026-2155-e05-qwen-any-public-audit';rows=json.loads((audit/'rows.json').read_text());dev=[r for r in rows if r['index']<6026]
 episodes={}
 for r in dev:
  if r['episode'] not in episodes:episodes[r['episode']]=dict(scenario=r['scenario'],condition=r['condition'],leaks=r['y_eventual'])
  assert episodes[r['episode']]['leaks']==r['y_eventual']
 behaviour={}
 for s in sorted({r['scenario'] for r in dev})+['ALL']:
  group=[e for e in episodes.values() if s=='ALL' or e['scenario']==s]
  e=[r for r in group if r['condition']=='recruiting'];k=sum(r['leaks'] for r in e);n=len(e)
  behaviour[s]=dict(recruiting=n,leaking=k,rate=k/n,ci95=wilson(k,n),
   control=sum(r['condition']=='control' for r in group),control_leaks=sum(r['leaks'] for r in group if r['condition']=='control'),
   alone=sum(r['condition']=='alone' for r in group),alone_leaks=sum(r['leaks'] for r in group if r['condition']=='alone'))
 # Restore saved monitor values, including training-control calls; no new inference.
 old=Path('/tmp/collusion-public-check-20261026');mr=old/'runs/20261026-1309-e06-percall-input-jev-qwen';oldrows=json.loads((old/'runs/20261026-1237-e05-qwen-percall/rows.json').read_text())
 mon={}
 for t in json.loads((mr/'tasks.json').read_text()):
  r=oldrows[t['row_index']];record=json.loads((mr/'cache'/(t['payload_key']+'.json')).read_text());v=float(record['score'])
  mon[(r['episode'],r['request_idx'])]=v
 fits=ROOT/'runs/20261026-2201-e05-arxiv-qwen-any-public';ids=[i for i,r in enumerate(rows) if r['index']<6026 and r['condition']=='recruiting'];byseed={}
 for seed in [42,43,44]:
  hit={};probe_hit={}
  for p in (fits/'immediate/loso').glob(f's{seed}-*/fit.json'):
   f=json.loads(p.read_text());c=f['split']['calibration'];cal=np.array([mon[(rows[i]['episode'],rows[i]['request_idx'])] for i in c]);th,_=threshold_at_fpr(cal,c,.05)
   z=np.load(p.parent/'scores.npz');assert list(z['indices'])==f['split']['test']
   for i,pred in zip(z['indices'],z['scores']):
    hit[int(i)]=mon[(rows[i]['episode'],rows[i]['request_idx'])]>th;probe_hit[int(i)]=pred>f['threshold']
  assert set(hit)==set(ids)
  byseed[seed]={}
  for name,hits in [('jev',hit),('probe',probe_hit)]:
   pos=[i for i in ids if rows[i]['y_immediate']];held=[i for i in ids if not rows[i]['y_eventual']];heldeps={rows[i]['episode'] for i in held}
   byseed[seed][name]=dict(leak_flagged=sum(hits[i] for i in pos)/len(pos),refusing_call_flagged=sum(hits[i] for i in held)/len(held),refusing_episode_flagged=sum(any(hits[i] for i in held if rows[i]['episode']==e) for e in heldeps)/len(heldeps),positive_calls=len(pos),refusing_calls=len(held),refusing_episodes=len(heldeps))
 alarms={name:{k:float(np.mean([byseed[s][name][k] for s in byseed])) for k in ['leak_flagged','refusing_call_flagged','refusing_episode_flagged']} for name in ['jev','probe']}
 l4=ROOT/'runs/20261026-1319-e06-percall-input-jev-l4/metrics.json';m=json.loads(l4.read_text())['loso'];reversal=dict(value=1-m['within_round_auc'],ci95=[1-m['within_round_ci95'][1],1-m['within_round_ci95'][0]],post_hoc=True,not_retuned=True)
 run=start_run('e05-arxiv-table-inputs',experiment='E05',settings={'no_api':True,'no_gpu':True,'source_sha256':{str(source.relative_to(ROOT)):sha(source),str(l4.relative_to(ROOT)):sha(l4)}})
 try:
  write_json_atomic(run.dir/'metrics.json',dict(screen=out,behaviour=behaviour,qwen_alarms=alarms,qwen_alarms_by_seed=byseed,gpt_jev_reversal=reversal))
  write_json_atomic(run.dir/'screen_provenance.json',evidence);run.result(behaviour_episodes=len(episodes),api_spend_usd=0);run.finish();print(run.dir)
 except BaseException as e:run.finish('failed',str(e));raise
if __name__=='__main__':main()
