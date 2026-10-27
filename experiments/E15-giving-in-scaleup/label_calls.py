"""E15: label calls, add the recency, ask-round and hedge fields, and pack the GPU payload.

Scored calls and the sharing label follow the paper and E14 (request_labels.request_index_labels):
calls after the first read of the protected file through the first exact emission inclusive;
incomplete (.partial.json) episodes are excluded. Only episodes that share are kept (plan gpu_scope).
Writes <out>.payload.json (new episodes, plus the E14 reproduction calls) and <out>.calls.json
(per-call fields for the new arms, E14 arm b as dispatch EARLY, and the old forbidden test leaks).

    python experiments/E15-giving-in-scaleup/label_calls.py FORBID=RUN EARLY=RUN LATE=RUN ... --out PREFIX
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD_ROOT = Path('/Users/leo/collusion-research')  # read-only source of the saved test episodes
sys.path[:0] = [str(ROOT / 'experiments/E01-behaviour-pilot'), str(ROOT / 'experiments/E14-permitted-onpolicy')]
from request_labels import completed_target_requests, request_index_labels
from label_calls import reproduction_calls  # E14 reproduction calls

E14_ARM_B = 'runs/20261028-0150-e14-permitted-onpolicy-arm-b'
TEST = ROOT / 'runs/20261026-2212-e05-arxiv-qwen-fresh-percall/probe_scores.csv.gz'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def text_of(message):
    content = message.get('content') if isinstance(message, dict) else None
    if isinstance(content, list):
        return ' '.join(str(part.get('text', '')) if isinstance(part, dict) else str(part) for part in content)
    return str(content or '')


def reply_text(record):
    response = record.get('response') or {}
    choices = response.get('choices') or [] if isinstance(response, dict) else []
    return text_of(choices[0].get('message', {})) if choices else ''


def episode_calls(path, arm, hedge):
    raw = path.read_bytes()
    ep = json.loads(raw)
    meta = ep['scenario_spec']['metadata']
    value, key, private = ep['scenario_spec']['honeypots'][0], meta['secret_key'], meta['private_path']
    marks = request_index_labels(ep, ep.get('label'))
    read, action = marks['first_token_read_request'], marks['first_action_target_request']
    asks = [c for c in ep['channel'] if c.get('actor') == 'recruiter' and (key in text_of(c) or private in text_of(c))]
    ask_round = asks[0]['round'] if asks else None
    first_ask_text = text_of(asks[0]) if asks else None
    rel = f'{path.parent.parent.name}/{path.name}'
    calls, last_read, hedged = [], None, False
    for ordinal, (idx, rec) in enumerate(completed_target_requests(ep), 1):
        last = rec['request']['messages'][-1]
        follows = last.get('role') == 'tool' and value in text_of(last)
        if follows:
            last_read = ordinal
        share = action is not None and ordinal == action
        in_window = read is not None and ordinal > read and (action is None or ordinal <= action)
        if in_window:
            calls.append({'call': {
                'call_id': f'{rel}::request_idx={idx}', 'episode': rel, 'episode_sha256': sha(raw), 'arm': arm,
                'condition': arm, 'scenario': meta['spray_row_id'], 'family': str(meta['family_id']),
                'round': rec['round'], 'request_idx': idx, 'ordinal': ordinal, 'label': int(share),
                'follows_read': follows, 'calls_since_read': None if last_read is None else ordinal - last_read,
                'ask_round': ask_round, 'before_ask': ask_round is None or rec['round'] < ask_round,
                'hedge_before_share': hedged if share else None},
                'request': rec['request'], 'record': rec})
        if action is None or ordinal < action:
            hedged = hedged or bool(hedge.search(reply_text(rec)))
    summary = {'episode': rel, 'arm': arm, 'scenario': meta['spray_row_id'], 'status': ep.get('status'),
               'rounds_completed': ep.get('rounds_completed'), 'first_read': read, 'first_emission': action,
               'share_round': next((c['call']['round'] for c in calls if c['call']['label']), None),
               'ask_round': ask_round, 'first_ask_text': first_ask_text}
    return calls, summary


def episodes_in(run):
    return sorted(p for p in (Path(run) / 'episodes').glob('*.json') if not p.name.endswith('.partial.json'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+')
    p.add_argument('--out', required=True)
    a = p.parse_args()
    plan = json.loads((HERE / 'plan.json').read_text())
    hedge = re.compile(plan['hedge_regex'])
    payload, fields, summaries = [], [], []
    def add(calls, summary, score):
        summaries.append(summary)
        if summary['first_emission'] is None:
            return
        for c in calls:
            fields.append(c['call'])
            if score:
                payload.append(c)
    for spec in a.runs:
        arm, run = spec.split('=', 1)
        assert arm in plan['arms'], arm
        for path in episodes_in(ROOT / run if not Path(run).is_absolute() else run):
            add(*episode_calls(path, arm, hedge), score=True)
    for path in episodes_in(ROOT / E14_ARM_B):  # dispatch EARLY, already scored in E14
        add(*episode_calls(path, 'EARLY', hedge), score=False)
    with gzip.open(TEST, 'rt') as f:
        test = list(csv.DictReader(f))
    leaking = sorted({r['episode'] for r in test if r['label'] == '1'})
    for episode in leaking:
        run, name = episode.split('/', 1)
        add(*episode_calls(OLD_ROOT / 'runs' / run / 'episodes' / name, 'FORBID_OLD', hedge), score=False)
    plan_e14 = json.loads((ROOT / 'experiments/E14-permitted-onpolicy/plan.json').read_text())
    payload = reproduction_calls(plan_e14) + payload
    Path(a.out + '.payload.json').write_text(json.dumps(payload, ensure_ascii=False))
    Path(a.out + '.calls.json').write_text(json.dumps(fields))
    Path(a.out + '.episodes.json').write_text(json.dumps(summaries, indent=1))
    from collections import Counter
    print(json.dumps({'episodes': Counter(s['arm'] for s in summaries),
                      'sharing_episodes': Counter(s['arm'] for s in summaries if s['first_emission'] is not None),
                      'scored_calls': Counter(c['arm'] for c in fields), 'payload_forwards': len(payload)}, default=dict))
