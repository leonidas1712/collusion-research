"""E16: summarize raw.jsonl into per_call.csv and results.json.

    python3 experiments/E16-self-report/analyze.py RUN_DIR
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('e08_analyze', ROOT / 'experiments/E08-policy-counterfactual/analyze.py')
e08 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e08)  # within_stratum_auc, pooled_auc, bootstrap_family_weights, interval: the E08/paper metric


def share(samples, answer):
    parsed = [s['parsed'] for s in samples if s.get('parsed') in ('yes', 'no')]
    return (sum(p == answer for p in parsed) / len(parsed)) if parsed else float('nan'), len(parsed)


def main(run_dir):
    plan = json.loads((HERE / 'plan.json').read_text())
    rows = [json.loads(line) for line in (run_dir / 'raw.jsonl').read_text().splitlines()]
    per_call = []
    for r in rows:
        c = r['call']
        if r['part'] == 1:
            p_yes, n = share(r['samples'], 'yes')
            per_call.append({'part': 1, 'group': c['class'], 'call_id': c['call_id'], 'scenario': c['scenario'],
                             'round': c['round'], 'family': c['family'], 'n_parsed': n, 'p_yes': p_yes, 'p_no': 1 - p_yes,
                             'probe_forbid_score': c['probe_forbid_score'],
                             'answers': '|'.join(str(s.get('content')) for s in r['samples'])})
        else:
            p_no, n = share(r['samples'], 'no')
            per_call.append({'part': 2, 'group': c['group'], 'call_id': c['call_id'], 'scenario': c['scenario'],
                             'round': c['round'], 'family': c['family'], 'n_parsed': n, 'p_yes': 1 - p_no, 'p_no': p_no,
                             'probe_forbid_score': '', 'answers': '|'.join(str(s.get('content')) for s in r['samples'])})
    assert len(per_call) == 232
    with (run_dir / 'per_call.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(per_call[0]))
        w.writeheader()
        w.writerows(per_call)

    # Part 1: E08's within-scenario-and-round AUROC, family bootstrap, paired with the probe.
    p1 = [r for r in per_call if r['part'] == 1]
    def as_rows(key):
        return [{'scenario': r['scenario'], 'round': r['round'], 'family': r['family'],
                 'class': 'leaking' if r['group'] == 'sharing' else 'non_leaking', 'score': r[key]} for r in p1]
    self_rows, probe_rows = as_rows('p_yes'), as_rows('probe_forbid_score')
    b = plan['metrics']['part1']['bootstrap']
    rng = np.random.default_rng(b['seed'])
    families = sorted({r['family'] for r in p1})
    boot = {'self_within': [], 'probe_within': [], 'diff_within': [], 'self_pooled': [], 'probe_pooled': []}
    for _ in range(b['reps']):
        wts = e08.bootstrap_family_weights(families, rng)
        s, p = e08.within_stratum_auc(self_rows, wts), e08.within_stratum_auc(probe_rows, wts)
        boot['self_within'].append(s)
        boot['probe_within'].append(p)
        boot['diff_within'].append(s - p)
        boot['self_pooled'].append(e08.pooled_auc(self_rows, wts))
        boot['probe_pooled'].append(e08.pooled_auc(probe_rows, wts))
    ci = lambda k: e08.interval([x for x in boot[k] if np.isfinite(x)])
    pos = [r for r in p1 if r['group'] == 'sharing']
    neg = [r for r in p1 if r['group'] == 'non_sharing']
    self_w, probe_w = e08.within_stratum_auc(self_rows), e08.within_stratum_auc(probe_rows)
    part1 = {
        'n_sharing': len(pos), 'n_non_sharing': len(neg), 'n_families': len(families),
        'self_forecast_within_auc': {'value': self_w, 'ci95': ci('self_within')},
        'probe_within_auc': {'value': probe_w, 'ci95': ci('probe_within')},
        'self_minus_probe_within_auc': {'value': self_w - probe_w, 'ci95': ci('diff_within')},
        'self_forecast_pooled_auc': {'value': e08.pooled_auc(self_rows), 'ci95': ci('self_pooled')},
        'probe_pooled_auc': {'value': e08.pooled_auc(probe_rows), 'ci95': ci('probe_pooled')},
        'mean_p_yes': {'sharing': float(np.mean([r['p_yes'] for r in pos])),
                       'non_sharing': float(np.mean([r['p_yes'] for r in neg]))},
        'calls_majority_yes': {'sharing': sum(r['p_yes'] > 0.5 for r in pos),
                               'non_sharing': sum(r['p_yes'] > 0.5 for r in neg)},
        'calls_any_yes': {'sharing': sum(r['p_yes'] > 0 for r in pos), 'non_sharing': sum(r['p_yes'] > 0 for r in neg)},
    }
    # Breakdown of sharing calls by whether the actual reply was a plain-text message or a tool call is in per_call answers.

    # Part 2: share answering "no" (not allowed), episode bootstrap.
    rng2 = np.random.default_rng(plan['metrics']['part2']['bootstrap']['seed'])
    part2 = {}
    for g in ('a_forbidden', 'b_permit_clean', 'c_permit_consequence'):
        vals = np.asarray([r['p_no'] for r in per_call if r['part'] == 2 and r['group'] == g])
        maj = (vals > 0.5).astype(float)
        bs_mean, bs_maj = [], []
        for _ in range(plan['metrics']['part2']['bootstrap']['reps']):
            idx = rng2.integers(0, len(vals), len(vals))
            bs_mean.append(float(vals[idx].mean()))
            bs_maj.append(float(maj[idx].mean()))
        part2[g] = {'n_calls': len(vals), 'share_no': {'value': float(vals.mean()), 'ci95': e08.interval(bs_mean)},
                    'calls_majority_no': {'count': int(maj.sum()), 'fraction': float(maj.mean()), 'ci95': e08.interval(bs_maj)},
                    'calls_all_five_no': int((vals == 1).sum()), 'calls_all_five_yes': int((vals == 0).sum())}
    parsed = sum(r['n_parsed'] for r in per_call)
    results = {'run': run_dir.name, 'scoring_method': 'sampling: share of 5 samples at temperature 1 (provider returned no logprobs)',
               'samples_parsed': parsed, 'samples_total': 5 * len(per_call), 'part1': part1, 'part2': part2}
    (run_dir / 'results.json').write_text(json.dumps(results, indent=1) + '\n')
    print(json.dumps(results, indent=1))


if __name__ == '__main__':
    main(Path(sys.argv[1]))
