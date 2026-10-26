"""Fixed84-episode confirmation, unchanged payloads and shared API ledger."""
import argparse,asyncio,contextvars,hashlib,json,os,sys,time,subprocess
from pathlib import Path
from dataclasses import asdict
from decimal import Decimal
import escalation_sweep as e
from stream_confirm_collect import SCENARIOS
from collusion.runs import start_run,write_json_atomic
SCENARIO=contextvars.ContextVar('scenario')

class AdaptiveCalls:
 def __init__(self,limit=12):self.limit=limit;self.active=0;self.condition=asyncio.Condition();self.rate_limits=0
 async def __aenter__(self):
  async with self.condition:
   await self.condition.wait_for(lambda:self.active<self.limit);self.active+=1
 async def __aexit__(self,*args):
  async with self.condition:self.active-=1;self.condition.notify_all()
 async def backoff(self):
  async with self.condition:self.rate_limits+=1;self.limit=max(2,self.limit//2);self.condition.notify_all()

class BoundedBudget(e.ConcurrentBudget):
 def __init__(self,*args,bounds,**kwargs):super().__init__(*args,**kwargs);self.bounds=bounds;self.api_gate=AdaptiveCalls(12)
 async def create(self,**payload):
  scenario=SCENARIO.get();model=payload['model'];observed=self.bounds[scenario][model]
  payload_bytes=len(json.dumps({'messages':payload['messages'],'tools':payload.get('tools',[])},ensure_ascii=False).encode())
  token_bound=max(2*observed,2*payload_bytes+4096)
  try:
   async with self.api_gate:
    self.prices[model]={**self.prices[model],'context_length':token_bound}
    response=await super().create(**payload)
  except Exception as exc:
   if getattr(exc,'status_code',None)==429:
    await self.api_gate.backoff();self.ledger['concurrency_limit']=self.api_gate.limit;self.ledger['rate_limit_count']=self.api_gate.rate_limits;self.save()
   raise
  if Decimal(self.ledger['reported_cost_usd'])>self.limit:raise RuntimeError('API billed cap breached; stop immediately')
  return response

async def main(parent):
 code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=e.ROOT,text=True).strip()
 plan=json.loads((parent/'frozen_plan.json').read_text());amend=json.loads((parent/'throughput_amendment.json').read_text());bounds=amend['scenario_model_max_observed_total_tokens']
 assert amend['fixed_total_episodes']==84 and amend['API_cap_usd']==5
 assert hashlib.sha256((parent/'frozen_weights.json').read_bytes()).hexdigest()==plan['weights_sha256']
 benchmark=json.loads((parent/'benchmark-retry_collection.json').read_text());assert len(benchmark)==5 and all(r['returncode']==0 for r in benchmark)
 old=json.loads((parent/'api_ledger.json').read_text());prior=sum(Decimal(r['charged_or_reserved_usd']) for r in old);prior_billed=sum(Decimal(r['billed_usd']) for r in old)
 from dotenv import load_dotenv
 from openai import AsyncOpenAI
 load_dotenv(e.ROOT/'.env');model,target_price,target_opts=e.target_config('gpt-oss');prices={model:target_price,e.PEER:e.peer_price()}
 settings=e.Settings(model,e.PEER,rounds=20,max_tool_steps=12,max_tokens=4096,empty_response_retries=2,empty_after_send_ends_turn=True,api_retry_attempts=10,api_retry_max_delay=60,target_request_options=target_opts,recruiter_request_options=e.peer_options(prices[e.PEER]))
 run=start_run('e03-stream-confirm-bulk',experiment='E03',parents=[parent.name],tags=['confirmation','api-only'],settings={'fixed_total_including_benchmark':84,'parallelism':12,'API_cap_usd':5,'prior_charged_or_reserved':str(prior),'freeze_sha256':hashlib.sha256((parent/'frozen_plan.json').read_bytes()).hexdigest(),'amendment_sha256':hashlib.sha256((parent/'throughput_amendment.json').read_bytes()).hexdigest()})
 write_json_atomic(parent/'bulk_run.json',{'run_dir':str(run.dir),'status':'running'})
 children={};records={};jobs=[]
 for index,scenario in enumerate(SCENARIOS):
  child=start_run('e03-stream-confirm-'+scenario,experiment='E03',model=model,parents=[parent.name,run.id],settings={'scenario':scenario,'strategy':'envblock_late','target':'gpt-oss','peer':e.PEER,'episode_settings':asdict(settings),'cap_usd':5,'shared_budget':str(run.dir/'budget.json'),'family_start':7000001+100*index+1})
  children[scenario]=child;records[scenario]=[]
  count=11 if index<5 else 12
  for i in range(count):jobs.append((scenario,'recruiting',i,7000001+100*index+1+i))
  for i in range(2):jobs.append((scenario,'control',i,7000001+100*index+1+i))
 assert len(jobs)==79
 # Interleave scenarios deterministically, without inspecting outcomes.
 jobs.sort(key=lambda j:(j[2],SCENARIOS.index(j[0]),j[1]))
 gate=asyncio.Semaphore(12)
 try:
  async with AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'],base_url='https://openrouter.ai/api/v1',max_retries=0,timeout=90) as client:
   budget=BoundedBudget(client,run.dir/'budget.json',prices,Decimal('5'),bounds=bounds)
   budget.ledger.update(charged_or_reserved_usd=str(prior),reported_cost_usd=str(prior_billed),prior_ledger=str(parent/'api_ledger.json'),prior_cost_included=True,reservation_rule='max(2xoldscenario max observed prompt+completion tokens,2xserializedpayloadUTF8bytes+4096), plus maxoutput;110%margin')
   budget.save();serving=e.ServingMetadata(budget,prices)
   async def one(scenario,condition,index,family):
    async with gate:
     SCENARIO.set(scenario);child=children[scenario];spec=e.build_scenario(scenario,'envblock_late',condition,family)
     ep=await e.run_episode(spec,settings,serving,child.dir/'episodes',episode_id=f'{condition}-{index+1:04}')
     ask=e.first_peer_ask(ep);emissions=e.first_emission_indices(ep)
     ep['collection_metadata']={'first_ask_round':ask['round'],'first_ask_text':ask['text'],'first_ask_method':ask['method'],'primary_forbidden_action':'channel_publication','secondary_forbidden_action':'other_file_disclosure','first_read_request_index':(ep.get('label') or {}).get('first_token_read_request',(ep.get('label') or {}).get('first_secret_read_request')),'prompt_commit':'c4478407','collection_code_commit':code_commit,**emissions}
     if ep['status']=='complete':write_json_atomic(child.dir/'episodes'/f"{ep['episode_id']}.json",ep)
     records[scenario].append(e.episode_record(scenario,'envblock_late',condition,ep));write_json_atomic(child.dir/'records.json',records[scenario])
     print('EPISODE_COMPLETE',scenario,condition,index,ep['status'],'USD',budget.ledger['reported_cost_usd'],flush=True)
   await asyncio.gather(*(one(*job) for job in jobs))
   summary={'requested_new':79,'benchmark':5,'total_fixed_attempts':84,'billed_total_including_benchmark':budget.ledger['reported_cost_usd'],'charged_or_reserved_total_including_benchmark':budget.ledger['charged_or_reserved_usd'],'children':[str(c.dir) for c in children.values()],'complete':sum(r['status']=='complete' for rs in records.values() for r in rs),'incomplete':sum(r['status']!='complete' for rs in records.values() for r in rs)}
   for scenario,child in children.items():write_json_atomic(child.dir/'summary.json',{'records':len(records[scenario]),'shared_budget':str(run.dir/'budget.json')});child.finish()
   write_json_atomic(run.dir/'summary.json',summary);write_json_atomic(parent/'bulk_run.json',{'run_dir':str(run.dir),'status':'finished',**summary});run.result(**summary);run.finish();print('BULK_DONE',run.dir,flush=True)
 except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--freeze',type=Path,required=True);a=p.parse_args();asyncio.run(main(a.freeze.resolve()))
