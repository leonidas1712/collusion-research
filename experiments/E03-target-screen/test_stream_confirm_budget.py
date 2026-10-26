import asyncio
from decimal import Decimal
from types import SimpleNamespace
from stream_confirm_bulk import BoundedBudget,SCENARIO

def test_bound_and_concurrent_ledger(tmp_path):
 class Client:
  async def create(self,**payload):
   await asyncio.sleep(0)
   return {'id':'fake','provider':'fake','usage':{'cost':.001}}
 client=Client();wrapped=SimpleNamespace(chat=SimpleNamespace(completions=client))
 price={'provider':'fake','context_length':1048576,'prompt_cap':'0.000001','completion_cap':'0.000004'}
 budget=BoundedBudget(wrapped,tmp_path/'budget.json',{'m':price},Decimal('1'),bounds={'s':{'m':100}})
 async def call():
  SCENARIO.set('s')
  return await budget.create(model='m',messages=[{'role':'user','content':'fixture'}],max_tokens=128,extra_body={'provider':{'order':['fake'],'allow_fallbacks':False}})
 async def run():await asyncio.gather(*(call() for _ in range(8)))
 asyncio.run(run())
 assert Decimal(budget.ledger['reported_cost_usd'])==Decimal('.008')
 assert Decimal(budget.ledger['charged_or_reserved_usd'])==Decimal('.008')
 assert all(Decimal(r['reserved_usd'])<Decimal('.02') for r in budget.ledger['calls'])
 assert not budget.blocked
