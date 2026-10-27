"""E14 analysis: permitted sharing calls vs forbidden test leaks on the frozen Qwen probe.

    python experiments/E14-permitted-onpolicy/analyze.py SCORES_CSV EPISODES_JSON [ADDON_SCORES_CSV] --out RUN_DIR
"""
import argparse
import csv
import gzip
import json
import math
from pathlib import Path
import random
import statistics as st

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEST = ROOT / 'runs/20261026-2212-e05-arxiv-qwen-fresh-percall/probe_scores.csv.gz'
E08_SCORES = ROOT / 'runs/20261026-1717-e08-policy-counterfactual/scores.csv'
REPS, SEED = 1000, 20261028


def _keep(value, digits=None):
    """Store full precision; rounding happens once, at registration."""
    return value


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [_keep(c - h, 3), _keep(c + h, 3)]


def auroc(pos, neg):
    if not pos or not neg:
        return None
    return sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / (len(pos) * len(neg))


def within_round_auroc(rows):
    """Positive-weighted mean of within-(scenario, round) AUROCs, as in the paper."""
    groups = {}
    for r in rows:
        groups.setdefault((r['scenario'], r['round']), []).append(r)
    total = weight = 0.0
    for g in groups.values():
        pos = [r['score'] for r in g if r['label']]
        neg = [r['score'] for r in g if not r['label']]
        if pos and neg:
            total += auroc(pos, neg) * len(pos)
            weight += len(pos)
    return total / weight if weight else None


def boot(rows, stat):
    """Episode bootstrap 95% interval for stat(rows)."""
    rng = random.Random(SEED)
    eps = {}
    for r in rows:
        eps.setdefault(r['episode'], []).append(r)
    keys = sorted(eps)
    out = []
    for _ in range(REPS):
        sample = [r for k in (rng.choice(keys) for _ in keys) for r in eps[k]]
        v = stat(sample)
        if v is not None:
            out.append(v)
    out.sort()
    return [_keep(out[int(0.025 * len(out))], 3), _keep(out[int(0.975 * len(out)) - 1], 3)] if out else None


def boot_diff(a, b, stat):
    """Independent episode bootstrap of stat(a) - stat(b)."""
    rng = random.Random(SEED)
    def groups(rows):
        g = {}
        for r in rows:
            g.setdefault(r['episode'], []).append(r)
        return [g[k] for k in sorted(g)]
    ga, gb = groups(a), groups(b)
    out = []
    for _ in range(REPS):
        sa = [r for e in (rng.choice(ga) for _ in ga) for r in e]
        sb = [r for e in (rng.choice(gb) for _ in gb) for r in e]
        out.append(stat(sa) - stat(sb))
    out.sort()
    return [_keep(out[int(0.025 * REPS)], 3), _keep(out[int(0.975 * REPS) - 1], 3)]


def describe(scores, thr):
    if not scores:
        return {'n': 0}
    q = st.quantiles(scores, n=4) if len(scores) > 1 else [scores[0]] * 3
    k = sum(s > thr for s in scores)
    return {'n': len(scores), 'median': _keep(st.median(scores), 3), 'iqr': [_keep(q[0], 3), _keep(q[2], 3)],
            'over_threshold': k, 'share_over_threshold': _keep(k / len(scores), 3), 'wilson95': wilson(k, len(scores))}


def med(rows):
    return st.median(r['score'] for r in rows)


def main(a):
    plan = json.loads((HERE / 'plan.json').read_text())
    thr = plan['threshold']
    rows = []
    for r in csv.DictReader(open(a.scores)):
        rows.append({**r, 'score': float(r['score']), 'label': int(r['label']), 'round': int(r['round'])})
    repro = [r for r in rows if r['condition'] == 'FORBID_REPRODUCTION']
    max_dev = max(abs(r['score'] - float(r['saved_score'])) for r in repro)
    assert max_dev <= plan['reproduction']['tolerance'], max_dev
    episodes = json.loads(Path(a.episodes).read_text())
    test = [{**r, 'score': float(r['score']), 'label': int(r['label']), 'round': int(r['round'])}
            for r in csv.DictReader(gzip.open(TEST, 'rt'))]
    disp = [r for r in test if r['scenario'] == plan['scenario']]
    f_leak = [r for r in disp if r['label']]
    f_non = [r for r in disp if not r['label']]
    all_leak = [r for r in test if r['label']]
    test_eps = {}
    for r in disp:
        test_eps.setdefault(r['episode'], []).append(r)
    res = {'threshold': thr, 'reproduction': {'calls': len(repro), 'max_abs_deviation': max_dev},
           'forbidden_dispatch_test': {
               'episodes_scored': len(test_eps),
               'leaking_episodes': sum(any(r['label'] for r in v) for v in test_eps.values()),
               'leak_rounds': sorted(r['round'] for r in f_leak),
               'leaking_calls': describe([r['score'] for r in f_leak], thr),
               'non_leaking_calls': describe([r['score'] for r in f_non], thr),
               'within_round_auroc': _keep(within_round_auroc(disp), 3),
               'within_round_auroc_ci': boot(disp, within_round_auroc)},
           'all_test_leaking_calls': describe([r['score'] for r in all_leak], thr),
           'control_reference': 'Test control calls were not scored in saved outputs. By construction 5% of development control calls exceed the threshold; on test episodes 5.5% of calls in refusing episodes do (runs/20261026-2224-e05-arxiv-fresh-comparisons).',
           'arms': {}}
    for arm in ('PERMIT', 'PERMIT_NO_CONSEQUENCE'):
        ar = [r for r in rows if r['condition'] == arm]
        eps = [e for e in episodes if e['arm'] == arm]
        if not eps:
            continue
        share = [r for r in ar if r['label']]
        pre = [r for r in ar if not r['label']]
        never = [e for e in eps if e['first_emission'] is None]
        rounds_with_both = {r['round'] for r in share} & {r['round'] for r in pre}
        res['arms'][arm] = {
            'episodes': len(eps), 'complete': sum(e['status'] == 'complete' for e in eps),
            'sharing_episodes': len(eps) - len(never), 'never_share': len(never),
            'never_share_rounds_completed': [e['rounds_completed'] for e in never],
            'sharing_rounds': sorted(r['round'] for r in share),
            'sharing_calls': describe([r['score'] for r in share], thr),
            'pre_sharing_calls': describe([r['score'] for r in pre], thr),
            'median_diff_vs_forbidden_leaks': _keep(med(share) - med(f_leak), 3) if share else None,
            'median_diff_ci': boot_diff(share, f_leak, med) if share else None,
            'pooled_auroc_sharing_vs_pre': _keep(auroc([r['score'] for r in share], [r['score'] for r in pre]), 3) if share and pre else None,
            'pooled_auroc_ci': boot(ar, lambda s: auroc([r['score'] for r in s if r['label']], [r['score'] for r in s if not r['label']])) if share and pre else None,
            'within_round_auroc': _keep(within_round_auroc(ar), 3) if within_round_auroc(ar) is not None else None,
            'within_round_auroc_ci': boot(ar, within_round_auroc) if within_round_auroc(ar) is not None else None,
            'rounds_with_sharing_and_pre_sharing_calls': len(rounds_with_both)}
        # round-matched: forbidden leaks in rounds where this arm also shares
        rs = {r['round'] for r in share}
        fm = [r['score'] for r in f_leak if r['round'] in rs]
        res['arms'][arm]['forbidden_leaks_in_same_rounds'] = describe(fm, thr)
    if a.addon:
        ad = [{**r, 'score': float(r['score']), 'label': int(r['label'])} for r in csv.DictReader(open(a.addon))]
        rep = [r for r in ad if r['condition'] == 'FORBID_REPRODUCTION']
        nc = {r['call_id']: r for r in ad if r['condition'] == 'PERMIT_NO_CONSEQUENCE'}
        e08 = {}
        for r in csv.DictReader(open(E08_SCORES)):
            e08.setdefault(r['call_id'], {})[r['condition']] = float(r['score'])
        dev = max(abs(r['score'] - e08[r['call_id']]['FORBID']) for r in rep)
        assert dev <= 1e-3, dev
        leak = [c for c, r in nc.items() if r['label']]
        def paired(cond):
            return [(nc[c]['score'] if cond == 'PERMIT_NO_CONSEQUENCE' else e08[c][cond]) - e08[c]['FORBID'] for c in leak]
        fam = {}
        for c in leak:
            fam.setdefault(nc[c]['family'], []).append(c)
        rng = random.Random(SEED)
        keys = sorted(fam)
        def boot_med(cond):
            vals = dict(zip(leak, paired(cond)))
            out = sorted(st.median(vals[c] for k in (rng.choice(keys) for _ in keys) for c in fam[k]) for _ in range(REPS))
            return [_keep(out[25], 3), _keep(out[974], 3)]
        res['addon_e08_permit_no_consequence'] = {
            'reproduction_max_abs_deviation': dev, 'leaking_calls': len(leak),
            **{f'median_{c}_minus_FORBID': _keep(st.median(paired(c)), 3) for c in ('PERMIT', 'NEUTRAL_EDIT', 'PERMIT_NO_CONSEQUENCE')},
            **{f'median_{c}_minus_FORBID_ci': boot_med(c) for c in ('PERMIT', 'NEUTRAL_EDIT', 'PERMIT_NO_CONSEQUENCE')},
            'share_over_threshold': {c: _keep(sum((nc[x]['score'] if c == 'PERMIT_NO_CONSEQUENCE' else e08[x][c]) > thr for x in leak) / len(leak), 3)
                                     for c in ('FORBID', 'PERMIT', 'PERMIT_NO_CONSEQUENCE')},
            'within_round_auroc_PERMIT_NO_CONSEQUENCE': _keep(within_round_auroc([{**r, 'round': int(r['round'])} for r in nc.values()]), 3)}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'results.json').write_text(json.dumps(res, indent=2) + '\n')
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('scores')
    p.add_argument('episodes')
    p.add_argument('addon', nargs='?')
    p.add_argument('--out', required=True)
    main(p.parse_args())
