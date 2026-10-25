"""Catalog, template and alone-episode gate for an API-served second target."""
import argparse
import asyncio
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'experiments/E01-behaviour-pilot'),
                str(ROOT / 'experiments/E02-activation-replay')]
from collusion.runs import start_run, write_json_atomic
from harness import Settings, run_episode, standard_tools
from scale_up import scale_up_scenario
from replay import render, digest
import overnight_sweep
from overnight_sweep import BudgetClient, PEER

MODEL = 'google/gemma-4-31b-it'


def scenario(family, family_id):
    return scale_up_scenario(
        'deploy-token-v2' if family == 'deploy-token-v2' else 'deploy-token',
        'consequence', 'alone', str(family_id),
        spray_row=None if family == 'deploy-token-v2' else family)


def initial_request(s):
    overrides = {t.schema['function']['name']: t for t in s.tool_overrides}
    tools = [overrides.get(t.schema['function']['name'], t) for t in standard_tools()]
    tools += list(s.extra_tools)
    return {'messages': [{'role': 'system', 'content': s.target_system},
                         {'role': 'user', 'content': s.target_task}],
            'tools': [t.schema for t in tools if t.schema['function']['name'] in s.tool_access['target']],
            'extra_body': {'reasoning': {'enabled': False}}}


def inspect_episode(ep, tokenizer):
    calls = []
    for i, record in enumerate(ep['requests']):
        if record['actor'] != 'target' or not record.get('response'):
            continue
        response = record['response']
        choice = (response.get('choices') or [{}])[0]
        message = choice.get('message') or {}
        _, ids, _, enabled = render(tokenizer, record['request'], 'from-request')
        usage = response.get('usage') or {}
        provider_tokens = usage.get('prompt_tokens')
        content = message.get('content') or ''
        calls.append({
            'request_idx': i, 'provider': response.get('provider'),
            'finish_reason': choice.get('finish_reason'),
            'native_tool_calls': len(message.get('tool_calls') or []),
            'raw_tool_text': bool(re.search(r'<\|?tool(?:_call)?\b|"(?:tool_calls|function)"\s*:', content)),
            'reasoning_text': bool(message.get('reasoning') or message.get('reasoning_details')),
            'reasoning_tokens': (usage.get('completion_tokens_details') or {}).get('reasoning_tokens'),
            'thinking_requested': enabled,
            'local_tokens': len(ids), 'provider_tokens': provider_tokens,
            'relative_token_error': abs(len(ids) / provider_tokens - 1) if provider_tokens else None,
        })
    return {'status': ep['status'], 'stop_reason': ep['stop_reason'],
            'label': ep.get('label'), 'calls': calls,
            'tool_errors': [t for t in ep['tool_log'] if isinstance(t.get('result'), dict)
                            and t['result'].get('error')]}


async def main(a):
    if not 0 < a.cap_usd <= 0.25:
        raise ValueError('Each smoke invocation is capped at $0.25')
    from transformers import AutoTokenizer
    catalog = json.loads(Path(a.catalog).read_text())[0]
    endpoint = next(e for e in catalog['endpoints']['data']['endpoints']
                    if e['provider_name'] == a.provider and e['quantization'] == 'bf16'
                    and 'tools' in e['supported_parameters'])
    revision = catalog['hf']['sha']
    tok = AutoTokenizer.from_pretrained(catalog['hf_model'], revision=revision, trust_remote_code=False)
    run = start_run('e03-gemma-' + ('smoke' if a.live else 'offline'), experiment='E03',
                    settings={**vars(a), 'target_model': MODEL}, parents=[Path(a.catalog).parent.name], model=MODEL,
                    tags=['second-target', 'smoke-gate'])
    try:
        offline = []
        for family in ('deploy-token-v2', 'handoff-exception-note'):
            req = initial_request(scenario(family, a.family_start))
            text, ids, _, _ = render(tok, req, 'from-request')
            without = render(tok, {k: v for k, v in req.items() if k != 'tools'}, 'from-request')[0]
            result = {'family': family, 'tokens': len(ids), 'tools_change_render': text != without,
                      'all_tool_names_present': all(t['function']['name'] in text for t in req['tools']),
                      'generation_suffix': text[-100:]}
            offline.append(result)
        write_json_atomic(run.dir / 'offline.json', {'revision': revision,
                          'template_sha256': digest(tok.get_chat_template().encode()), 'checks': offline})
        if not all(x['tools_change_render'] and x['all_tool_names_present'] for x in offline):
            raise ValueError('Offline template gate failed')
        if not a.live:
            run.finish(); return
        from dotenv import load_dotenv
        from openai import AsyncOpenAI
        load_dotenv(ROOT / '.env')
        pricing = endpoint['pricing']
        if Decimal(str(pricing.get('request', 0))) != 0:
            raise ValueError('Unexpected per-request fee')
        price = {'provider': a.provider, 'context_length': endpoint['context_length'],
                 'prompt_cap': str(Decimal(pricing['prompt']) * Decimal('1.01')),
                 'completion_cap': str(Decimal(pricing['completion']) * Decimal('1.01'))}
        opts = overnight_sweep.options(price)
        opts['extra_body']['provider']['quantizations'] = ['bf16']
        if a.logprobs:
            opts['logprobs'] = True
        settings = Settings(MODEL, PEER, rounds=20, target_request_options=opts)
        overnight_sweep.LIMIT = Decimal(str(a.cap_usd))
        async with AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'],
                               base_url='https://openrouter.ai/api/v1', max_retries=0, timeout=90) as client:
            budget = BudgetClient(client, run.dir / 'budget.json', {MODEL: price})
            results = []
            for family in ('deploy-token-v2', 'handoff-exception-note'):
                for i in range(a.episodes_per_family):
                    s = scenario(family, a.family_start + i)
                    ep = await run_episode(s, settings, budget, run.dir / 'episodes',
                                           episode_id=f'{family}-{i+1:04}')
                    result = {'family': family, 'episode_id': ep['episode_id'], **inspect_episode(ep, tok)}
                    results.append(result)
                    write_json_atomic(run.dir / 'smoke.json', results)
                    print(family, ep['status'], ep['label'], flush=True)
                    # A failed episode is evidence for the gate, not an invitation to scale.
                    if ep['status'] != 'complete':
                        run.result(gate='failed', reason=ep['stop_reason']); run.finish(); return
        run.result(episodes=len(results), gate='awaiting transcript and token-count audit')
        run.finish()
    except BaseException as exc:
        run.finish('failed', str(exc)); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog', required=True)
    p.add_argument('--provider', choices=['Novita', 'Crusoe'], default='Novita')
    p.add_argument('--live', action='store_true')
    p.add_argument('--logprobs', action='store_true', help='Save output token evidence for the thinking-off audit')
    p.add_argument('--episodes-per-family', type=int, choices=[1, 2], default=1)
    p.add_argument('--family-start', type=int, default=90001)
    p.add_argument('--cap-usd', type=float, default=0.25)
    asyncio.run(main(p.parse_args()))
