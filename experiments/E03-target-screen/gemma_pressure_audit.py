"""Audit whether private peer reasoning entered the target-visible conversation."""
import argparse
import json
from pathlib import Path


def audit(ep):
    private = []
    peer_responses = 0
    providers = set()
    for request in ep['requests']:
        if request['actor'] != 'recruiter' or not request.get('response'):
            continue
        response = request['response']
        providers.add(response.get('provider'))
        for choice in response.get('choices', []):
            message = choice.get('message') or {}
            if message.get('reasoning'):
                private.append(message['reasoning'])
            for detail in message.get('reasoning_details') or []:
                if detail.get('text'):
                    private.append(detail['text'])
            peer_responses += 1
    target_messages = [m for r in ep['requests'] if r['actor'] == 'target'
                       for m in r['request']['messages']]
    visible = json.dumps([ep['channel'], target_messages, ep['histories']['target']], ensure_ascii=False)
    leaks = [i for i, text in enumerate(private) if text in visible]
    target_reasoning_fields = sum(bool(m.get('reasoning') or m.get('reasoning_details'))
                                  for m in target_messages)
    return {'status': ep['status'], 'rounds_completed': ep['rounds_completed'],
            'peer_responses': peer_responses, 'peer_providers': sorted(providers, key=str),
            'private_reasoning_texts': len(private), 'verbatim_reasoning_leaks': leaks,
            'target_history_reasoning_fields': target_reasoning_fields,
            'reasoning_isolated': bool(private) and not leaks and not target_reasoning_fields}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('episode', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(json.loads(args.episode.read_text())), indent=2))
