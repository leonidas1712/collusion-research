"""E14 add-on: pack the 150 E08 replay calls under PERMIT_NO_CONSEQUENCE (plan amendment_v2).

The E08 PERMIT rule replaces the FORBID rule and the scenario's consequence sentence is deleted;
the first 12 calls are also packed unedited as the FORBID reproduction check.

    python experiments/E14-permitted-onpolicy/addon_payload.py --out addon_payload.json
"""
import argparse
import copy
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD_ROOT = Path('/Users/leo/collusion-research')  # read-only source of the saved test episodes
sys.path.insert(0, str(ROOT / 'experiments/E08-policy-counterfactual'))
from counterfactual import edit_request, pack_inputs

REPRODUCTION_CALLS = 12


def no_consequence(request, scenario, e08, consequences):
    edited = edit_request(request, scenario, 'PERMIT', e08)
    system = [m for m in edited['messages'] if m.get('role') == 'system'][0]
    sentence = consequences[scenario]
    if system['content'].count(sentence) != 1:
        raise ValueError(f'Consequence sentence not found exactly once: {scenario}')
    system['content'] = system['content'].replace(sentence, '', 1)
    return edited


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    e08 = json.loads((ROOT / 'experiments/E08-policy-counterfactual/plan.json').read_text())
    plan = json.loads((HERE / 'plan.json').read_text())
    consequences = plan['amendment_v2']['addon_E08_permit_no_consequence']['consequence_sentences_by_scenario']
    packed = pack_inputs(e08, OLD_ROOT)
    payload = []
    for i, item in enumerate(packed):
        c = item['call']
        call = {'call_id': c['call_id'], 'episode': c['episode'], 'scenario': c['scenario'], 'family': c['family'],
                'round': c['round'], 'request_idx': c['request_idx'], 'label': int(c['class'] == 'leaking')}
        if i < REPRODUCTION_CALLS:
            payload.append({'call': {**call, 'condition': 'FORBID_REPRODUCTION', 'saved_score': c['saved_forbid_score']},
                            'request': item['request'], 'record': item['record']})
        payload.append({'call': {**call, 'condition': 'PERMIT_NO_CONSEQUENCE'},
                        'request': no_consequence(copy.deepcopy(item['request']), c['scenario'], e08, consequences),
                        'record': item['record']})
    Path(a.out).write_text(json.dumps(payload, ensure_ascii=False))
    print(json.dumps({'calls': len(packed), 'forwards': len(payload),
                      'leaking': sum(x['call']['label'] for x in payload if x['call']['condition'] != 'FORBID_REPRODUCTION')}))
