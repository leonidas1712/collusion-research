"""Budget-bounded collection after a committed reasoning-probe freeze."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[2]
SCENARIOS=['deploy-token-v2','dispatch-integration-code','handoff-exception-note','procurement-reserve-price','service-capacity-figure','service-rollout-threshold']

def run_one(parent,scenario,index,recruiting,control,start,cap,tag):
 log=parent/f'{tag}-{index:02}.log'
 command=[str(ROOT/'.venv/bin/python'),'experiments/E03-target-screen/escalation_sweep.py','--target','gpt-oss','--scenario',scenario,'--strategy','envblock_late','--recruiting',str(recruiting),'--control',str(control),'--family-start',str(start),'--cap-usd',str(cap),'--parallelism','1','--prompt-commit','0418116df17ec3b4c8e9ff667b1142c6b5414a17','--code-commit',subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()]
 begin=time.monotonic()
 with log.open('w') as output:proc=subprocess.run(command,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
 text=log.read_text();runlines=[line for line in text.splitlines() if line.startswith('[run] ')];assert len(runlines)==1,(log,runlines)
 folder=ROOT/runlines[0].split(' -> ',1)[1]
 budget=json.loads((folder/'budget.json').read_text())
 return {'scenario':scenario,'run_dir':str(folder.relative_to(ROOT)),'returncode':proc.returncode,'seconds':time.monotonic()-begin,'billed_usd':budget['reported_cost_usd'],'charged_or_reserved_usd':budget['charged_or_reserved_usd'],'cap_usd':cap,'family_start':start,'requested_recruiting':recruiting,'requested_control':control,'command':command,'log':str(log.relative_to(ROOT))}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--freeze',type=Path,required=True);p.add_argument('--benchmark',action='store_true',required=True);p.add_argument('--tag',default='benchmark');p.add_argument('--family-offset',type=int,default=0);a=p.parse_args();parent=a.freeze.resolve();path=parent/'frozen_plan.json';plan=json.loads(path.read_text());relative=path.relative_to(ROOT)
 committed=subprocess.check_output(['git','show','HEAD:'+str(relative)],cwd=ROOT);assert committed==path.read_bytes(),'Plan must be committed unchanged before any new episode'
 assert hashlib.sha256((parent/plan['weights_file']).read_bytes()).hexdigest()==plan['weights_sha256']
 audit=json.loads((parent/'family_disjoint_audit.json').read_text());assert audit['intersection']==[]
 assert not (parent/(a.tag+'_collection.json')).exists(),'Do not silently repeat benchmark'
 results=[]
 ledger_path=parent/'api_ledger.json';ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else []
 for i,scenario in enumerate(SCENARIOS[:5]):
  spent=sum(float(r['charged_or_reserved_usd']) for r in ledger);remaining=plan['allocation']['API_max_usd']-spent
  assert remaining>0
  result=run_one(parent,scenario,i,1,0,audit['new_scenario_family_starts'][i]+a.family_offset,remaining,a.tag)
  results.append(result);ledger.append(result);ledger_path.write_text(json.dumps(ledger,indent=2)+'\n');(parent/(a.tag+'_collection.json')).write_text(json.dumps(results,indent=2)+'\n');print('BENCHMARK',result['run_dir'],result['charged_or_reserved_usd'],flush=True)
  if result['returncode']!=0:raise RuntimeError('Benchmark episode failed; stop before further calls')
 assert len(results)==5
 billed=sum(float(r['billed_usd']) for r in results);reserved=sum(float(r['charged_or_reserved_usd']) for r in results);summary={'runs':5,'requested_episodes':5,'billed_usd':billed,'charged_or_reserved_usd':reserved,'mean_billed_per_requested_episode':billed/5,'max_billed_per_requested_episode':max(float(r['billed_usd']) for r in results),'returncodes':[r['returncode'] for r in results],'projection_108_at_max_episode_cost':max(float(r['billed_usd']) for r in results)*108,'note':'Outcome-blind cost projection; controls may run longer, account separately before scaling'}
 (parent/(a.tag+'_cost.json')).write_text(json.dumps(summary,indent=2)+'\n')
 subprocess.run(['aboard','say','--reply','1833','@codex-2 @claude: five-episode frozen confirmation cost benchmark finished; '+str(parent.relative_to(ROOT)/(a.tag+'_cost.json'))+f'; billedUSD{billed:.6f}, charged/reservedUSD{reserved:.6f}. Collection has NOT scaled automatically; review completion/cost and control allowance first.'],check=True)
