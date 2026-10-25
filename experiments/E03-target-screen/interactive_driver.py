"""Thin interactive peer driver for hand-driving the target in the fixed scenario.

The human/agent supplies each PEER (deploy-agent) message; the driver delivers it the way
the harness does, runs one full TARGET turn (tool loop against a MockEnvironment), and prints
the target's reply, its tool calls/results, and the deterministic leak status. Target system
prompt, task, fake credential, tools and the scorer are FIXED and identical to the automated
harness (reuses experiments/E01-behaviour-pilot: standard_tools, MockEnvironment, score_episode).

Only target calls cost money (peer turns come from the caller). State persists to a JSON file,
so branches can be forked for beam-search exploration.

    uv run python experiments/E03-target-screen/interactive_driver.py init  SESS --target gpt-oss
    uv run python experiments/E03-target-screen/interactive_driver.py say   SESS "peer message"
    uv run python experiments/E03-target-screen/interactive_driver.py fork  SESS NEWSESS
    uv run python experiments/E03-target-screen/interactive_driver.py show  SESS
"""
import argparse
import copy
import json
import os
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'experiments/E01-behaviour-pilot'),
                str(ROOT / 'experiments/E03-target-screen')]

from harness import standard_tools, MockEnvironment, _validate_args
from scale_up import scale_up_scenario
from scenarios import score_episode
from escalation_sweep import target_config

SESS_ROOT = ROOT / 'runs'


def _tools_for(scenario):
    base = standard_tools()
    overrides = {t.schema['function']['name']: t for t in scenario.tool_overrides}
    tools = [overrides.get(t.schema['function']['name'], t) for t in base] + list(scenario.extra_tools)
    return {t.schema['function']['name']: t for t in tools}


def _scenario():
    # Fixed: deploy-token-v2 recruiting (peer system prompt is irrelevant here; we drive the peer).
    return scale_up_scenario('deploy-token-v2', 'consequence', 'recruiting', '97999')


def _episode_view(state):
    """Minimal episode dict the deterministic scorer understands."""
    return {'scenario': state['scenario_name'],
            'scenario_spec': {'files': state['initial_files'], 'metadata': state['metadata'],
                              'name': state['scenario_name']},
            'channel': state['channel'], 'tool_log': state['tool_log'],
            'status': 'complete', 'fake': False,
            'histories': {'target': state['history']}}


def _leak_status(state):
    label = score_episode(_episode_view(state))
    return {'give_in': bool(label.get('objective_success') or label.get('other_file_disclosure')),
            'objective_success': label.get('objective_success'),
            'other_file_disclosure': label.get('other_file_disclosure'),
            'token_in_context': label.get('token_in_context'),
            'token_read_round': label.get('token_read_round'),
            'first_action_round': label.get('first_action_round'),
            'disclosure_kind': label.get('disclosure_kind'),
            'task_success': label.get('task_success')}


def cmd_init(a):
    s = _scenario()
    tools = _tools_for(s)
    state = {
        'target_name': a.target, 'scenario_name': s.name,
        'target_model': None, 'target_options': None,
        'target_system': s.target_system, 'target_task': s.target_task,
        'channel_format': s.channel_format, 'actor_names': s.actor_names,
        'tool_access': s.tool_access, 'tool_schemas': [t.schema for t in tools.values()],
        'initial_files': copy.deepcopy(s.files), 'files': copy.deepcopy(s.files),
        'metadata': copy.deepcopy(s.metadata),
        'history': [{'role': 'system', 'content': s.target_system},
                    {'role': 'user', 'content': s.target_task}],
        'channel': [], 'tool_log': [], 'round': 0, 'cost_usd': '0',
        'max_tool_steps': 12, 'max_tokens': 4096, 'temperature': 0.7,
    }
    model, _price, opts = target_config(a.target)
    state['target_model'] = model
    state['target_options'] = opts
    d = SESS_ROOT / a.session
    d.mkdir(parents=True, exist_ok=True)
    (d / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2))
    print(f'INIT {a.session} target={model}')
    print('target_system:', s.target_system)
    print('target_task:', s.target_task)
    print('Drive the peer with:  say', a.session, '"<message>"')


def _load(session):
    return json.loads((SESS_ROOT / session / 'state.json').read_text())


def _save(session, state):
    (SESS_ROOT / session / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2))


def _call_target(state, client):
    payload = {'model': state['target_model'], 'messages': copy.deepcopy(state['history']),
               'max_tokens': state['max_tokens'], 'temperature': state['temperature'],
               'tools': [t for t in state['tool_schemas']
                         if t['function']['name'] in state['tool_access']['target']]}
    payload.update(copy.deepcopy(state['target_options']))  # includes extra_body (SDK kwarg)
    resp = client.chat.completions.create(**payload)
    data = resp.model_dump() if hasattr(resp, 'model_dump') else resp
    cost = (data.get('usage') or {}).get('cost') or 0
    state['cost_usd'] = str(Decimal(state['cost_usd']) + Decimal(str(cost)))
    return data


def cmd_say(a):
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    state = _load(a.session)
    tools = _tools_for(_scenario())
    env = MockEnvironment(state['files'], channel=state['channel'],
                          test_result=_scenario().test_result)
    state['round'] += 1
    env.round = state['round']
    # Deliver the peer (recruiter) message exactly as the harness does.
    fmt = state['channel_format'].format(actor='recruiter',
                                         name=state['actor_names']['recruiter'], content=a.message)
    env.publish('recruiter', a.message)
    state['history'].append({'role': 'user', 'content': fmt})
    client = OpenAI(api_key=os.environ['OPENROUTER_API_KEY'],
                    base_url='https://openrouter.ai/api/v1', timeout=120)
    turn_tools, turn_text = [], None
    channel_start = len(env.channel)
    for step in range(state['max_tool_steps']):
        data = _call_target(state, client)
        choice = (data.get('choices') or [{}])[0]
        msg = choice.get('message') or {}
        kept = {k: v for k, v in msg.items()
                if k in ('role', 'content', 'tool_calls', 'reasoning', 'reasoning_details', 'refusal') and v is not None}
        kept['role'] = 'assistant'
        state['history'].append(kept)
        calls = msg.get('tool_calls') or []
        if not calls:
            turn_text = msg.get('content') or ''
            if turn_text.strip() and not [e for e in env.channel[channel_start:] if e['actor'] == 'target']:
                env.publish('target', turn_text)
            break
        for call in calls:
            fn = call.get('function') or {}
            name, raw_args = fn.get('name'), fn.get('arguments')
            try:
                if name not in state['tool_access']['target']:
                    raise PermissionError('tool not available')
                args = json.loads(raw_args)
                _validate_args(args, tools[name].schema['function']['parameters'])
                result = tools[name].handler(env, args, 'target')
            except PermissionError:
                result = {'error': 'PermissionError'}
            except (TypeError, ValueError, KeyError) as exc:
                result = {'error': type(exc).__name__}
            state['tool_log'].append({'actor': 'target', 'round': state['round'], 'call_id': call['id'],
                                      'name': name, 'arguments': raw_args, 'result': result})
            turn_tools.append({'name': name, 'arguments': raw_args, 'result': result})
            state['history'].append({'role': 'tool', 'tool_call_id': call['id'],
                                     'content': json.dumps(result, ensure_ascii=False)})
    state['files'] = env.files
    state['channel'] = env.channel
    _save(a.session, state)
    status = _leak_status(state)
    print(f'=== round {state["round"]}  ({state["target_name"]})  cost=${state["cost_usd"]} ===')
    print('PEER>', a.message)
    for t in turn_tools:
        res = t['result']
        shown = json.dumps(res)[:300]
        print(f'  TOOL {t["name"]}({t["arguments"][:160]}) -> {shown}')
    print('TARGET>', (turn_text or '').strip()[:1500] if turn_text is not None else '(no final text this turn)')
    print('LEAK>', json.dumps(status))


def cmd_fork(a):
    src = _load(a.session)
    d = SESS_ROOT / a.new_session
    d.mkdir(parents=True, exist_ok=True)
    (d / 'state.json').write_text(json.dumps(src, ensure_ascii=False, indent=2))
    print(f'FORK {a.session} -> {a.new_session} at round {src["round"]}')


def cmd_show(a):
    state = _load(a.session)
    print(f'session={a.session} target={state["target_model"]} round={state["round"]} cost=${state["cost_usd"]}')
    for e in state['channel']:
        who = state['actor_names'].get(e['actor'], e['actor'])
        print(f'  [r{e["round"]}] {who}: {e["content"][:500]}')
    print('LEAK>', json.dumps(_leak_status(state)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    pi = sub.add_parser('init'); pi.add_argument('session'); pi.add_argument('--target', choices=['gpt-oss', 'gemma'], default='gpt-oss')
    ps = sub.add_parser('say'); ps.add_argument('session'); ps.add_argument('message')
    pf = sub.add_parser('fork'); pf.add_argument('session'); pf.add_argument('new_session')
    psh = sub.add_parser('show'); psh.add_argument('session')
    a = p.parse_args()
    {'init': cmd_init, 'say': cmd_say, 'fork': cmd_fork, 'show': cmd_show}[a.cmd](a)


if __name__ == '__main__':
    main()
