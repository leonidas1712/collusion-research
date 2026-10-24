import asyncio,json,os,sys
from pathlib import Path
ROOT=Path('/Users/leo/collusion-research')
sys.path.insert(0,str(ROOT/'experiments/E01-behaviour-pilot'))
sys.path.insert(0,str(ROOT/'src'))
from dotenv import load_dotenv
from openai import AsyncOpenAI
from collusion.runs import start_run
from harness import Settings,run_episode
from overnight_rules import get_overnight_scenario
from overnight_sweep import BudgetClient,options
from dataclasses import asdict
async def main():
    load_dotenv(ROOT/'.env')
    prices=json.loads((ROOT/'runs/20261024-0332-e01-overnight-rule-strength/prices.json').read_text())
    settings=Settings('qwen/qwen3-32b','deepseek/deepseek-v4-flash',rounds=3,max_tool_steps=12,max_tokens=1536,target_request_options=options(prices['qwen/qwen3-32b']),recruiter_request_options=options(prices['deepseek/deepseek-v4-flash']))
    scenario=get_overnight_scenario('deploy-token','consequence_logged','control',family_id='2001')
    scenario.metadata.update(control_smoke_approval='Aboard #370',purpose='single control-peer smoke; no scale-up')
    run=start_run('e01-control2-smoke',experiment='E01',settings=asdict(settings),tags=['control2','smoke'],model=settings.target_model)
    client=AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'],base_url='https://openrouter.ai/api/v1',max_retries=0,timeout=90)
    try:
        budget=BudgetClient(client,run.dir/'budget.json',prices)
        ep=await run_episode(scenario,settings,budget,run.dir/'episodes',episode_id='episode-0001')
        run.result(label=ep.get('label'),cost=budget.ledger['reported_cost_usd'])
        run.finish('finished' if ep['status']=='complete' else 'failed')
        print('SMOKE_RESULT',run.id,ep['status'],json.dumps(ep.get('label')),budget.ledger['reported_cost_usd'],flush=True)
    except BaseException as exc:
        run.finish('failed',type(exc).__name__);raise
    finally:await client.close()
asyncio.run(main())
