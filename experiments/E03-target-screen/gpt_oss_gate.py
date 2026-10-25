"""API-only gpt-oss alone smoke with a capped ledger and Harmony token audit."""
import argparse
import asyncio
import copy
from decimal import Decimal
import json
import os
from pathlib import Path

from gemma_gate import ROOT, scenario, initial_request
from gemma_screen import ConcurrentBudget
from harness import Settings, run_episode
from overnight_sweep import PEER, options
from replay import normalize_messages, digest
from collusion.runs import start_run, write_json_atomic

MODEL = 'openai/gpt-oss-20b'


def token_audit(tok, request):
    messages, changes = normalize_messages(request['messages'])
    # Harmony reads `thinking`, whereas the API history uses `reasoning`.
    variants = {}
    for mapped in (False, True):
        current = copy.deepcopy(messages)
        for message in current:
            if message['role'] == 'assistant':
                message.setdefault('content', '')
                if mapped and message.get('reasoning'):
                    message['thinking'] = message['reasoning']
        kwargs = dict(tools=request.get('tools'), add_generation_prompt=True, reasoning_effort='low')
        name = 'reasoning_to_thinking' if mapped else 'unadapted_low'
        try:
            text = tok.apply_chat_template(current, tokenize=False, **kwargs)
            ids = tok.encode(text, add_special_tokens=False)
            variants[name] = dict(tokens=len(ids), prompt_sha256=digest(text.encode()), suffix=text[-80:])
        except Exception as exc:
            variants[name] = {'error': str(exc)}
    return variants


async def main(a):
    if not 0 < a.cap_usd <= 3:
        raise ValueError('Smoke cap must be at most USD3')
    catalog = json.loads(Path(a.catalog).read_text())[0]
    endpoint = next(e for e in catalog['endpoints']['data']['endpoints']
                    if e['provider_name'] == a.provider and e['quantization'] == a.precision
                    and 'tools' in e['supported_parameters'])
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL, revision=catalog['hf']['sha'], trust_remote_code=False)
    run = start_run('e03-gpt-oss-smoke', experiment='E03', model=MODEL,
                    parents=[Path(a.catalog).parent.name], settings={**vars(a), 'revision': catalog['hf']['sha'],
                    'reasoning_effort': 'low', 'template_sha256': digest(tok.get_chat_template().encode())})
    offline = []
    for family in ['deploy-token-v2', 'handoff-exception-note']:
        req = initial_request(scenario(family, 96001))
        checks = token_audit(tok, req)
        assert all('error' not in v for v in checks.values()), checks
        offline.append(dict(family=family, checks=checks))
    write_json_atomic(run.dir/'offline.json', offline)
    pricing = endpoint['pricing']
    assert Decimal(str(pricing.get('request', 0))) == 0
    price = dict(provider=a.provider, context_length=endpoint['context_length'],
                 prompt_cap=str(Decimal(pricing['prompt'])*Decimal('1.01')),
                 completion_cap=str(Decimal(pricing['completion'])*Decimal('1.01')))
    write_json_atomic(run.dir/'endpoint.json', endpoint)
    opts = options(price)
    opts['extra_body']['provider']['quantizations'] = [a.precision]
    opts['extra_body']['provider']['require_parameters'] = True
    opts['extra_body']['reasoning'] = {'effort': 'low', 'exclude': False}
    settings = Settings(MODEL, PEER, rounds=20, max_tokens=4096, target_request_options=opts,
                        empty_after_send_ends_turn=True, empty_response_retries=2,
                        api_retry_attempts=10, api_retry_max_delay=60)
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    load_dotenv(ROOT/'.env')
    results = []
    async with AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'], base_url='https://openrouter.ai/api/v1',
                           max_retries=0, timeout=90) as client:
        budget = ConcurrentBudget(client, run.dir/'budget.json', {MODEL: price}, Decimal(str(a.cap_usd)))
        budget.save()
        for family in ['deploy-token-v2', 'handoff-exception-note']:
            s = scenario(family, 96001)
            ep = await run_episode(s, settings, budget, run.dir/'episodes', episode_id=family+'-0001')
            calls = []
            for idx, record in enumerate(ep['requests']):
                response = record.get('response')
                if not response:
                    calls.append(dict(request_idx=idx, error=record.get('error')))
                    continue
                choice = response['choices'][0]
                message = choice.get('message') or {}
                usage = response.get('usage') or {}
                checks = token_audit(tok, record['request'])
                for variant in checks.values():
                    if 'tokens' in variant and usage.get('prompt_tokens'):
                        variant['relative_error'] = variant['tokens']/usage['prompt_tokens']-1
                calls.append(dict(request_idx=idx, round=record['round'], provider=response.get('provider'),
                                  finish_reason=choice['finish_reason'], native_finish_reason=choice.get('native_finish_reason'),
                                  prompt_tokens=usage.get('prompt_tokens'), render=checks,
                                  tool_calls=[t['function']['name'] for t in message.get('tool_calls') or []],
                                  reasoning_fields=[k for k in ('reasoning','reasoning_details') if message.get(k)],
                                  reasoning_characters=len(message.get('reasoning') or ''),
                                  history_reasoning_messages=sum(bool(m.get('reasoning')) for m in record['request']['messages']),
                                  empty_end_turn=record.get('empty_after_send_end_turn',False),
                                  resend=record.get('empty_resend_number',0)))
            results.append(dict(family=family, status=ep['status'], stop_reason=ep['stop_reason'], label=ep.get('label'), calls=calls))
            write_json_atomic(run.dir/'audit.json', results)
            print(family, ep['status'], ep['stop_reason'], 'cost', budget.ledger['reported_cost_usd'], flush=True)
        run.result(episodes=len(results), billed_usd=budget.ledger['reported_cost_usd'],
                   charged_or_reserved_usd=budget.ledger['charged_or_reserved_usd'])
    run.finish()
    print(run.dir)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog', required=True)
    p.add_argument('--provider', default='CoreWeave')
    p.add_argument('--precision', default='fp4')
    p.add_argument('--cap-usd', type=float, default=.25)
    asyncio.run(main(p.parse_args()))
