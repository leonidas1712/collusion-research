"""Join independent blind judgements; reasoning-only variants are post-review checks."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from sklearn.metrics import cohen_kappa_score

REASONING_ONLY = {'E11-04', 'E11-09', 'E11-13', 'E11-23', 'E11-24'}
CONDITIONAL_NO = {'E11-06', 'E11-11', 'E11-27', 'E11-30', 'E11-31'}
IMPLIED_YES = {'E11-02', 'E11-08'}


def agreement(labels, keys, flag):
    y = [r['judgement'].strip().lower() == 'yes' for r in labels]
    f = [bool(keys[r['sample_id']][flag]) for r in labels]
    matrix = {f'reviewer_{a}_flag_{b}': sum(yy == a and ff == b for yy, ff in zip(y, f))
              for a in (False, True) for b in (False, True)}
    agrees = sum(a == b for a, b in zip(y, f))
    observed = agrees / len(y)
    expected = (sum(y)*sum(f)+(len(y)-sum(y))*(len(y)-sum(f))) / len(y)**2
    kappa = (observed-expected)/(1-expected)
    assert abs(kappa-cohen_kappa_score(y, f)) < 1e-12
    return dict(agreement=observed, agreements=agrees, n=len(y), reviewer_yes=sum(y),
                flag_yes=sum(f), kappa=kappa, confusion=matrix)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--labels', type=Path, required=True)
    a = p.parse_args()
    keys = {r['sample_id']: r for r in json.loads((a.run/'blind_sample_key.json').read_text())}
    labels = list(csv.DictReader(a.labels.open()))
    assert len(labels) == len(keys) == 33 and {r['sample_id'] for r in labels} == set(keys)
    for r in labels:
        assert r['judgement'].strip().lower() in ('yes', 'no')
        if r['sample_id'] in REASONING_ONLY | IMPLIED_YES: assert r['judgement'] == 'yes'
        if r['sample_id'] in CONDITIONAL_NO: assert r['judgement'] == 'no'
    variants = {
        'including_reasoning': labels,
        'reasoning_only_relabelled_no': [dict(r, judgement='no') if r['sample_id'] in REASONING_ONLY else r for r in labels],
        'reasoning_only_excluded': [r for r in labels if r['sample_id'] not in REASONING_ONLY],
    }
    out = {
        'variants': {name: {flag: agreement(rows, keys, flag) for flag in ('jev', 'regex')}
                     for name, rows in variants.items()},
        'reviewer_labels_sha256': hashlib.sha256(a.labels.read_bytes()).hexdigest(),
        'reasoning_only_ids': sorted(REASONING_ONLY),
        'conditional_promises_labelled_no': sorted(CONDITIONAL_NO),
        'implied_sharing_labelled_yes': sorted(IMPLIED_YES),
        'primary': 'including_reasoning: frozen access includes provider-visible earlier same-turn reasoning',
        'sensitivity': 'Post-review only: relabel five reasoning-only judgements no, leaving machine flags fixed; also exclude those five rows. Neither is a rerun of the flags on reasoning-stripped inputs.',
        'sampling': 'All 13 Jev-positive calls plus 20 sampled Jev-negative calls; agreement and kappa describe this selected sample, not population accuracy.',
        'kappa_check': 'Direct marginal-probability formula matches sklearn to 1e-12 for all six results',
    }
    (a.run/'reviewer_agreement.json').write_text(json.dumps(out, indent=2)+'\n')
    metrics_path = a.run/'metrics.json'
    metrics = json.loads(metrics_path.read_text())
    metrics['blind_review'] = out
    metrics_path.write_text(json.dumps(metrics, indent=2)+'\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__': main()
