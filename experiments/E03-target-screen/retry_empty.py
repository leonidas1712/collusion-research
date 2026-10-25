"""Resend saved empty-response requests without executing their generated tool calls."""
import argparse
import asyncio
import json
import os
from pathlib import Path

from gemma_screen import MODEL, ConcurrentBudget, price_for
from gemma_gate import ROOT
from harness import _retry_delay
from collusion.runs import start_run, write_json_atomic


async def main(a):
    if len(a.episodes) != 2:
        raise ValueError('This diagnostic takes exactly two failed episodes')
    requests = []
    for path in a.episodes:
        ep = json.loads(Path(path).read_text())
        if ep['stop_reason'] != 'empty_assistant_message':
            raise ValueError('Source did not fail with an empty assistant message')
        record = ep['requests'][-1]
        assert record['actor'] == 'target' and record['request']['model'] == MODEL
        requests.append((path, record['request']))
    prices = {MODEL: price_for(MODEL, 'Crusoe', 'bf16')}
    run = start_run('e03-gemma-empty-resends', experiment='E03', settings=vars(a),
                    parents=[Path(p).parent.parent.name for p in a.episodes],
                    tags=['second-target', 'serving-diagnostic'], model=MODEL)
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    load_dotenv(ROOT / '.env')
    async with AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'],
                           base_url='https://openrouter.ai/api/v1', max_retries=0, timeout=90) as client:
        budget = ConcurrentBudget(client, run.dir/'budget.json', prices, '.05')
        results = []
        for path, payload in requests:
            for repeat in range(1, 4):
                row = {'source': path, 'repeat': repeat, 'request': payload, 'attempts': []}
                for attempt in range(6):
                    try:
                        response = await budget.create(**payload)
                        raw = response.model_dump()
                        message = raw['choices'][0]['message']
                        row.update(response=raw, empty=not message.get('tool_calls')
                                   and not (message.get('content') or '').strip())
                        row['attempts'].append({'status': 'success'})
                        break
                    except Exception as exc:
                        status = getattr(exc, 'status_code', None)
                        row['attempts'].append({'error': type(exc).__name__, 'status_code': status})
                        if status != 429 or attempt == 5:
                            row['error'] = type(exc).__name__
                            break
                        delay, _ = _retry_delay(exc, attempt)
                        row['attempts'][-1]['retry_delay_seconds'] = delay
                        write_json_atomic(run.dir/'resends.json', results + [row])
                        await asyncio.sleep(delay)
                results.append(row)
                write_json_atomic(run.dir/'resends.json', results)
                print(Path(path).parent.parent.name, repeat, row.get('empty'), row.get('error'), flush=True)
                await asyncio.sleep(3)
        run.result(calls=len(results), empty=sum(r.get('empty') is True for r in results),
                   errors=sum('error' in r for r in results), cost=budget.ledger['reported_cost_usd'])
        run.finish()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('episodes', nargs='+')
    asyncio.run(main(p.parse_args()))
