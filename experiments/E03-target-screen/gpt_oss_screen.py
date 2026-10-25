"""Capped gpt-oss screen using shared approved tactics and unchanged E01 scenarios."""
import argparse
import asyncio
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys

from gemma_pressure_prompts import ROOT, FAMILIES, scenario as pressure_scenario
from gemma_screen import ConcurrentBudget, pool_options
from gemma_pressure import ServingMetadata
from catalog import fetch
from harness import Settings, run_episode
from scale_up import scale_up_scenario
from collusion.runs import start_run, write_json_atomic

TARGET='openai/gpt-oss-20b'
PRO='deepseek/deepseek-v4-pro-0813'
FLASH='deepseek/deepseek-v4-flash'


def pool(model, quantizations, names=None):
    snapshot=fetch(f'https://openrouter.ai/api/v1/models/{model}/endpoints')
    endpoints=[e for e in snapshot['data']['endpoints'] if 'tools' in e['supported_parameters']
               and e['quantization'] in quantizations and (names is None or e['provider_name'] in names)]
    if not endpoints:
        raise ValueError(f'No allowed endpoints for {model}')
    providers=list(dict.fromkeys(e['provider_name'] for e in endpoints))
    if any(Decimal(str(e['pricing'].get('request',0)))!=0 for e in endpoints):
        raise ValueError('Unexpected request fee')
    return dict(provider='pool', context_length=max(e['context_length'] for e in endpoints),
                prompt_cap=str(max(Decimal(e['pricing']['prompt']) for e in endpoints)*Decimal('1.01')),
                completion_cap=str(max(Decimal(e['pricing']['completion']) for e in endpoints)*Decimal('1.01')),
                routing=dict(order=providers,only=providers,allow_fallbacks=True,
                             quantizations=quantizations,require_parameters=True),endpoints=endpoints,snapshot=snapshot)


def make_scenario(family,condition,family_id,arm):
    if arm=='max':
        return pressure_scenario(family,condition,family_id,reviewed=True)
    return scale_up_scenario('deploy-token-v2' if family=='deploy-token-v2' else 'deploy-token',
                            'consequence',condition,str(family_id),'T0',
                            spray_row=None if family=='deploy-token-v2' else family)


async def main(a):
    if not 0<a.cap_usd<=6:
        raise ValueError('Total screen cap is USD6 including previous ledgers')
    prices={TARGET:pool(TARGET,['fp4','bf16']),
            PRO:pool(PRO,['unknown'],['DeepSeek']),
            FLASH:pool(FLASH,['fp8'],['DeepInfra','Baidu','StreamLake'])}
    prices[PRO]['routing'].pop('quantizations')
    target_opts=pool_options(prices[TARGET])
    target_opts['extra_body']['reasoning']={'effort':'low','exclude':False}
    settings={}
    for arm,peer in [('max',PRO),('plain',FLASH)]:
        peer_opts=pool_options(prices[peer])
        if arm=='max':
            peer_opts['extra_body']['provider'].pop('quantizations',None)
            peer_opts['extra_body']['reasoning']={'effort':'medium','exclude':False}
        settings[arm]=Settings(TARGET,peer,rounds=20,max_tokens=8192 if arm=='max' else 1536,parallelism=a.parallelism,
                              target_request_options=target_opts,recruiter_request_options=peer_opts,
                              empty_after_send_ends_turn=True,empty_response_retries=2,
                              api_retry_attempts=10,api_retry_max_delay=60)
    for setting in settings.values():
        for request_options in [setting.target_request_options,setting.recruiter_request_options]:
            reserved={'model','messages','tools','max_tokens','temperature'}
            assert not reserved.intersection(request_options)
            assert not reserved.intersection(request_options.get('extra_body',{}))
    parent=start_run('e03-gpt-oss-screen',experiment='E03',model=TARGET,
                     settings={**vars(a),'settings_by_arm':{k:asdict(v) for k,v in settings.items()},
                               'prompt_builder_sha256':hashlib.sha256((ROOT/'experiments/E03-target-screen/gemma_pressure_prompts.py').read_bytes()).hexdigest()},
                     parents=['20261025-1739-e03-gpt-oss-smoke','20261025-1746-e03-harmony-audit'])
    write_json_atomic(parent.dir/'prices.json',prices)
    streams=sys.stdout,sys.stderr,sys.excepthook
    cells=[];plan=[]
    arms=['max','plain'] if a.arm=='both' else [a.arm]
    for arm in arms:
        for fi,family in enumerate(FAMILIES):
            for condition,count in ([('recruiting',10),('control',2)] if arm=='max' else [('recruiting',4)]):
                if a.pilot and (arm!='max' or family!='deploy-token-v2' or condition!='recruiting'):
                    continue
                if a.pilot:count=1
                start=(120001 if arm=='max' else 121001)+fi*100+(50 if condition=='control' else 0)
                if a.after_pilot and arm=='max' and family=='deploy-token-v2' and condition=='recruiting':
                    count-=1;start+=1
                cell=start_run(f'e01-gpt-oss-{arm}-{family}-{condition}',experiment='E01',model=TARGET,
                               parents=[parent.id],settings={**asdict(settings[arm]),'family':family,'arm':arm,
                               'condition':condition,'count':count,'family_start':start})
                sys.stdout,sys.stderr,sys.excepthook=streams
                cells.append(dict(run=cell,arm=arm,family=family,condition=condition,count=count,start=start))
                for i in range(count):
                    s=make_scenario(family,condition,start+i,arm)
                    assert s.recruiter_approved and s.peer_enabled
                    expected=(6 if family=='dispatch-integration-code' else 7) if arm=='max' else 0
                    assert s.recruiter_system.count('Approach to try:')==expected
                    plan.append(dict(cell=cell.id,episode_id=f'episode-{i+1:04}',family_id=start+i,
                                     prompt_sha256=hashlib.sha256(s.recruiter_system.encode()).hexdigest(),
                                     arm=arm,family=family,condition=condition,index=i))
    expected_count=1 if a.pilot else sum(48 if arm=='max' else 16 for arm in arms)-(1 if a.after_pilot else 0)
    assert len(plan)==expected_count and len({p['family_id'] for p in plan})==expected_count
    write_json_atomic(parent.dir/'cells.json',[c['run'].id for c in cells])
    write_json_atomic(parent.dir/'plan.json',plan)
    if not a.live:
        for c in cells:c['run'].finish()
        parent.result(live_calls=0,planned=len(plan));parent.finish();print(parent.dir);return
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    load_dotenv(ROOT/'.env')
    lookup={c['run'].id:c for c in cells}
    gate=asyncio.Semaphore(a.parallelism)
    results=[]
    async with AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'],base_url='https://openrouter.ai/api/v1',max_retries=0,timeout=90) as client:
        budget=ConcurrentBudget(client,parent.dir/'budget.json',prices,a.cap_usd);budget.save()
        wrapped=ServingMetadata(budget,prices)
        async def one(p):
            async with gate:
                s=make_scenario(p['family'],p['condition'],p['family_id'],p['arm'])
                assert hashlib.sha256(s.recruiter_system.encode()).hexdigest()==p['prompt_sha256']
                cell=lookup[p['cell']]['run']
                ep=await run_episode(s,settings[p['arm']],wrapped,cell.dir/'episodes',episode_id=p['episode_id'])
                result={**p,'status':ep['status'],'stop_reason':ep['stop_reason'],
                        'label':ep.get('label'),'failure_actor':ep['requests'][-1]['actor'] if ep['status']!='complete' and ep['requests'] else None}
                results.append(result);write_json_atomic(parent.dir/'results.json',results)
                print('EPISODE',len(results),p['arm'],p['family'],p['condition'],p['index']+1,
                      ep['status'],(ep.get('label') or {}).get('objective_success'),
                      'billed',budget.ledger['reported_cost_usd'],'reserved',budget.ledger['charged_or_reserved_usd'],flush=True)
        # Interleave conditions and scenarios so budget exhaustion cannot erase a whole arm.
        plan.sort(key=lambda p:(p['index'],p['family'],p['arm'],p['condition']))
        await asyncio.gather(*(one(p) for p in plan))
        for c in cells:
            c['run'].result(planned=c['count'],completed=sum(r['cell']==c['run'].id and r['status']=='complete' for r in results));c['run'].finish()
        parent.result(episodes=len(results),billed_usd=budget.ledger['reported_cost_usd'],
                      charged_or_reserved_usd=budget.ledger['charged_or_reserved_usd']);parent.finish()
    print(parent.dir)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot',action='store_true');p.add_argument('--after-pilot',action='store_true')
    p.add_argument('--arm',choices=['max','plain','both'],default='both')
    p.add_argument('--live',action='store_true');p.add_argument('--cap-usd',type=float,default=4)
    p.add_argument('--parallelism',type=int,choices=[1,2,3,4],default=4)
    asyncio.run(main(p.parse_args()))
