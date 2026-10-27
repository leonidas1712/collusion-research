"""E14: label PERMIT calls with the paper's exact-emission rule and pack the GPU payload.

Scored calls follow the Qwen per-call audit (experiments/E05-probes/qwen_any_public.py):
calls after the first read of the protected file, through the first exact emission inclusive
(all post-read calls when nothing is emitted); the positive is the first exact emission.
Incomplete (.partial.json) episodes are excluded, as in the paper.
Also packs the plan's reproduction calls (saved test calls with frozen scores).

    python experiments/E14-permitted-onpolicy/label_calls.py ARM=RUN_DIR [ARM=RUN_DIR ...] --out payload.json

ARM is PERMIT (arm a) or PERMIT_NO_CONSEQUENCE (arm b).
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD_ROOT = Path('/Users/leo/collusion-research')  # read-only source of the saved test episodes
sys.path.insert(0, str(ROOT / 'experiments/E01-behaviour-pilot'))
from request_labels import completed_target_requests, request_index_labels


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def episode_calls(path, condition, scenario):
    raw = path.read_bytes()
    ep = json.loads(raw)
    marks = request_index_labels(ep, ep.get('label'))
    read, action = marks['first_token_read_request'], marks['first_action_target_request']
    rel = f'{path.parent.parent.name}/{path.name}'
    calls = []
    for ordinal, (idx, rec) in enumerate(completed_target_requests(ep), 1):
        if read is None or ordinal <= read or (action is not None and ordinal > action):
            continue
        calls.append({'call': {'call_id': f'{rel}::request_idx={idx}', 'episode': rel, 'episode_sha256': sha(raw),
                               'scenario': scenario, 'family': str(ep['scenario_spec']['metadata']['family_id']),
                               'round': rec['round'], 'request_idx': idx, 'ordinal': ordinal,
                               'label': int(ordinal == action), 'condition': condition,
                               'first_read': read, 'first_emission': action},
                      'request': rec['request'], 'record': rec})
    summary = {'episode': rel, 'first_read': read, 'first_emission': action,
               'emission_round': next((c['call']['round'] for c in calls if c['call']['label']), None),
               'status': ep.get('status'), 'rounds_completed': ep.get('rounds_completed')}
    return calls, summary


def reproduction_calls(plan):
    e08 = json.loads((ROOT / 'experiments/E08-policy-counterfactual/plan.json').read_text())
    by_id = {c['call_id']: c for c in e08['calls']}
    out = []
    for call_id in plan['reproduction']['call_ids']:
        c = by_id[call_id]
        run_id, name = c['episode'].split('/', 1)
        raw = (OLD_ROOT / 'runs' / run_id / 'episodes' / name).read_bytes()
        assert sha(raw) == c['episode_sha256'], call_id
        rec = json.loads(raw)['requests'][c['request_idx']]
        assert sha(json.dumps(rec['request'], ensure_ascii=False, separators=(',', ':')).encode()) == c['request_sha256']
        out.append({'call': {'call_id': call_id, 'episode': c['episode'], 'scenario': c['scenario'], 'family': c['family'],
                             'round': c['round'], 'request_idx': c['request_idx'], 'label': int(c['class'] == 'leaking'),
                             'condition': 'FORBID_REPRODUCTION', 'saved_score': c['saved_forbid_score']},
                    'request': rec['request'], 'record': rec})
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+')
    p.add_argument('--out', required=True)
    a = p.parse_args()
    plan = json.loads((HERE / 'plan.json').read_text())
    payload, episodes = reproduction_calls(plan), []
    for spec in a.runs:
        arm, run = spec.split('=', 1)
        assert arm in ('PERMIT', 'PERMIT_NO_CONSEQUENCE'), arm
        for path in sorted(x for x in (Path(run) / 'episodes').glob('episode-*.json') if not x.name.endswith('.partial.json')):
            calls, summary = episode_calls(path, arm, plan['scenario'])
            summary['arm'] = arm
            payload += calls
            episodes.append(summary)
    Path(a.out).write_text(json.dumps(payload, ensure_ascii=False))
    Path(a.out).with_suffix('.episodes.json').write_text(json.dumps(episodes, indent=1))
    n = [x for x in payload if x['call']['condition'] != 'FORBID_REPRODUCTION']
    print(json.dumps({'episodes': len(episodes), 'sharing_episodes': sum(e['first_emission'] is not None for e in episodes),
                      'permit_calls': len(n), 'sharing_calls': sum(x['call']['label'] for x in n),
                      'reproduction_calls': len(payload) - len(n)}))
