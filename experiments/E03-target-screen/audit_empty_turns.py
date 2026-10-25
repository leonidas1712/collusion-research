"""Check whether empty-response failures followed an already delivered channel post."""
from collections import Counter
import json
from pathlib import Path

from gemma_gate import ROOT
from collusion.runs import start_run, write_json_atomic


def audit(path, ep):
    index = len(ep['requests']) - 1
    record = ep['requests'][index]
    actor, rnd = record['actor'], record['round']
    delivered = [t for t in ep['tool_log'] if t['actor'] == actor and t['round'] == rnd
                 and t['name'] == 'send_message' and isinstance(t.get('result'), dict)
                 and t['result'].get('delivered') is True]
    prior_ids = {c['id'] for r in ep['requests'][:index] if r['actor'] == actor and r['round'] == rnd
                 for choice in (r.get('response') or {}).get('choices', [])
                 for c in ((choice.get('message') or {}).get('tool_calls') or [])
                 if c.get('function', {}).get('name') == 'send_message'}
    delivered = [t for t in delivered if t['call_id'] in prior_ids]
    last = record['request']['messages'][-1]
    return {'episode': str(path.relative_to(ROOT)), 'target_model': ep['settings']['target_model'],
            'empty_actor': actor, 'empty_model': record['request']['model'], 'round': rnd,
            'same_turn_delivered_send_message': bool(delivered),
            'last_input_is_delivered_send_receipt': last.get('role') == 'tool'
                and last.get('tool_call_id') in {t['call_id'] for t in delivered},
            'delivered_call_ids': [t['call_id'] for t in delivered],
            'request_idx': index, 'resend_number': record.get('empty_resend_number', 0)}


if __name__ == '__main__':
    rows = []
    patterns = ['*scaleup/episodes/*.json', '*e01-gemma-screen*/episodes/*.json']
    for path in sorted({p for pattern in patterns for p in (ROOT/'runs').glob(pattern)}):
        ep = json.loads(path.read_text())
        if ep.get('settings', {}).get('target_model') not in ('qwen/qwen3-32b', 'google/gemma-4-31b-it'):
            continue
        if ep.get('stop_reason') == 'empty_assistant_message':
            rows.append(audit(path, ep))
    run = start_run('e03-empty-turn-audit', experiment='E03', settings={'patterns': patterns},
                    tags=['serving-diagnostic', 'offline'])
    result = {'episodes': rows, 'failures': len(rows),
              'same_turn_delivered': sum(r['same_turn_delivered_send_message'] for r in rows),
              'immediately_after_receipt': sum(r['last_input_is_delivered_send_receipt'] for r in rows),
              'by_empty_model': dict(Counter(r['empty_model'] for r in rows))}
    write_json_atomic(run.dir/'audit.json', result)
    lines = ['# Empty replies after delivered messages', '',
        'This audit checks stored failures without rerunning models. A successful send_message '
        'must belong to the same actor and round, have delivered:true in the tool log, and match '
        'a preceding native tool-call ID. The final prompt must end with that delivery receipt '
        'for the stricter immediate-predecessor check.', '',
        f"Failures found: {len(rows)}. Same-turn successful posts: {result['same_turn_delivered']}. "
        f"Immediate delivery receipts: {result['immediately_after_receipt']}.", '',
        'The search covers all saved Qwen3-32B scale-up episode files, including additional scenarios '
        'and a thinking-mode batch, plus the Gemma screen files present at audit time. '
        'It is broader than the primary analysis corpus.', '',
        '| Episode | Empty actor | Round | Same-turn post | Last input is receipt |',
        '|---|---|---:|---|---|']
    lines += [f"| {r['episode']} | {r['empty_actor']} | {r['round']} | {r['same_turn_delivered_send_message']} | {r['last_input_is_delivered_send_receipt']} |" for r in rows]
    lines += ['', 'Proposed interpretation: a valid stop response with no text or tool calls may end '
        'the turn normally if that actor already delivered a channel message during the same turn. '
        'Log the empty response and post nothing extra. Other empty responses retain the bounded '
        'resend rule and remain incomplete when it is exhausted. This audit changes no episode '
        'status, label or harness behaviour.', '']
    (run.dir/'report.md').write_text('\n'.join(lines))
    run.result(**{k: v for k, v in result.items() if k != 'episodes'})
    run.finish()
    print(run.id, {k: v for k, v in result.items() if k != 'episodes'})
