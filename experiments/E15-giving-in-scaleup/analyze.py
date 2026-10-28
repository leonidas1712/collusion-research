"""E15 analysis: crossing rates by arm, split by how recently the value was read; recency figure.

    python experiments/E15-giving-in-scaleup/analyze.py CALLS_JSON EPISODES_JSON SCORES_CSV [SCORES_CSV ...] --out RUN_DIR
"""
import argparse
import csv
import gzip
import json
import math
from pathlib import Path
import random
import statistics as st
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E14_SCORES = ROOT / 'runs/20261028-0224-e14-permitted-onpolicy/scores.csv'
TEST = ROOT / 'runs/20261026-2212-e05-arxiv-qwen-fresh-percall/probe_scores.csv.gz'
REPS, SEED = 2000, 20261028
BINS = ('0', '1', '2', '3+')
ARMS = ('FORBID', 'EARLY', 'LATE')
COLORS = {'FORBID': '#000000', 'EARLY': '#009E73', 'LATE': '#CC79A7'}


def wilson(k, n, z=1.96):
    if not n:
        return None
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [c - h, c + h]


def rate(calls, thr):
    k = sum(c['score'] > thr for c in calls)
    return {'n': len(calls), 'over': k, 'share': k / len(calls) if calls else None, 'wilson95': wilson(k, len(calls)),
            'median_score': st.median(c['score'] for c in calls) if calls else None}


def boot_diff(a, b, thr):
    """Bootstrap of crossing-rate difference; one sharing call per episode, so calls are episodes."""
    rng = random.Random(SEED)
    xa, xb = [c['score'] > thr for c in a], [c['score'] > thr for c in b]
    out = sorted(sum(rng.choice(xa) for _ in xa) / len(xa) - sum(rng.choice(xb) for _ in xb) / len(xb) for _ in range(REPS))
    return {'value': sum(xa) / len(xa) - sum(xb) / len(xb), 'ci95': [out[int(.025 * REPS)], out[int(.975 * REPS) - 1]]}


def boot_median(values):
    rng = random.Random(SEED)
    out = sorted(st.median(rng.choice(values) for _ in values) for _ in range(REPS))
    return {'value': st.median(values), 'ci95': [out[int(.025 * REPS)], out[int(.975 * REPS) - 1]], 'n': len(values)}


def bin_of(c):
    s = c['calls_since_read']
    return None if s is None else ('3+' if s >= 3 else str(s))


def main(a):
    plan = json.loads((HERE / 'plan.json').read_text())
    thr = plan['threshold']
    calls = json.loads(Path(a.calls).read_text())
    episodes = json.loads(Path(a.episodes).read_text())
    scores = {}
    for path in a.scores:
        for r in csv.DictReader(open(path)):
            if r.get('condition') == 'FORBID_REPRODUCTION':
                assert abs(float(r['score']) - float(r['saved_score'])) <= plan['reproduction']['tolerance'], r['call_id']
                continue
            scores[r['call_id']] = float(r['score'])
    for r in csv.DictReader(open(E14_SCORES)):
        if r['condition'] == 'PERMIT_NO_CONSEQUENCE':
            scores[r['call_id']] = float(r['score'])
    with gzip.open(TEST, 'rt') as f:
        for r in csv.DictReader(f):
            scores[r['row_id']] = float(r['score'])
    missing = [c['call_id'] for c in calls if c['call_id'] not in scores]
    assert not missing, (len(missing), missing[:3])
    for c in calls:
        c['score'] = scores[c['call_id']]
        c['group'] = 'FORBID' if c['arm'] in ('FORBID', 'FORBID_OLD') else c['arm']
    share = [c for c in calls if c['label']]
    late_pre = [c for c in share if c['arm'] == 'LATE' and c['before_ask']]
    main_share = [c for c in share if not (c['arm'] == 'LATE' and c['before_ask'])]
    by = {g: [c for c in main_share if c['group'] == g] for g in ARMS}
    nonread = {g: [c for c in v if not c['follows_read']] for g, v in by.items()}
    forbid_r3 = [c for c in nonread['FORBID'] if c['round'] >= 3]
    res = {'threshold': thr, 'reproduction_ok': True}
    res['primary_nonread'] = {g: rate(v, thr) for g, v in nonread.items()}
    res['primary_nonread']['FORBID_old'] = rate([c for c in nonread['FORBID'] if c['arm'] == 'FORBID_OLD'], thr)
    res['primary_nonread']['FORBID_new'] = rate([c for c in nonread['FORBID'] if c['arm'] == 'FORBID'], thr)
    res['primary_nonread']['FORBID_round3plus'] = rate(forbid_r3, thr)
    res['diff_LATE_minus_FORBID_nonread_round3plus'] = boot_diff(nonread['LATE'], forbid_r3, thr) if nonread['LATE'] else None
    res['diff_EARLY_minus_FORBID_nonread'] = boot_diff(nonread['EARLY'], nonread['FORBID'], thr)
    late = res['primary_nonread']['LATE']
    if late['n'] and res['diff_LATE_minus_FORBID_nonread_round3plus']:
        low = late['wilson95'][1] < .5 and res['diff_LATE_minus_FORBID_nonread_round3plus']['ci95'][1] < 0
        rises = late['wilson95'][0] <= res['primary_nonread']['FORBID_round3plus']['share'] <= late['wilson95'][1]
        res['reading'] = 'stays_low' if low else 'rises' if rises else 'in_between'
    else:
        res['reading'] = 'not_assessable (no LATE non-read sharing calls)'
    res['follows_read'] = {g: rate([c for c in v if c['follows_read']], thr) for g, v in by.items()}
    res['all_sharing'] = {g: rate(v, thr) for g, v in by.items()}
    res['recency'] = {g: {b: rate([c for c in v if bin_of(c) == b], thr) for b in BINS} for g, v in by.items()}
    res['late_pre_ask_shares'] = rate(late_pre, thr)
    res['per_scenario'] = {g: {s: {'all': rate([c for c in v if c['scenario'] == s], thr),
                                   'nonread': rate([c for c in v if c['scenario'] == s and not c['follows_read']], thr)}
                               for s in plan['scenarios']} for g, v in by.items()}
    earlier = {}
    for c in calls:
        earlier.setdefault(c['episode'], []).append(c)
    def delta(c, pre_ask_only=False):
        prev = [x['score'] for x in earlier[c['episode']] if x['ordinal'] < c['ordinal'] and (not pre_ask_only or x['before_ask'])]
        return c['score'] - st.mean(prev) if prev else None
    res['within_episode_delta'] = {g: boot_median([d for d in map(delta, v) if d is not None]) for g, v in by.items()}
    late_deltas = [d for d in (delta(c, True) for c in by['LATE']) if d is not None]
    res['within_episode_delta']['LATE_vs_pre_ask_calls'] = boot_median(late_deltas) if late_deltas else None
    eps = {g: [e for e in episodes if (e['arm'] in ('FORBID',) and g == 'FORBID') or e['arm'] == g] for g in ARMS}
    res['episodes'] = {g: {'complete': len(v), 'sharing': sum(e['first_emission'] is not None for e in v),
                           'share_rounds': sorted(e['share_round'] for e in v if e['share_round'] is not None),
                           'ask_rounds': sorted(e['ask_round'] for e in v if e['ask_round'] is not None),
                           'no_ask': sum(e['ask_round'] is None for e in v)} for g, v in eps.items()}
    res['episodes']['FORBID_old_leaking'] = sum(e['arm'] == 'FORBID_OLD' for e in episodes)
    res['episodes']['note'] = 'FORBID counts are the new arm only; the old forbidden test leaks add 38 sharing calls.'
    late_eps = eps['LATE']
    res['late_compliance'] = {'ask_in_round_5': sum(e['ask_round'] == 5 for e in late_eps), 'episodes': len(late_eps)}
    res['hedge_before_share'] = {g: {'hedged': sum(bool(c['hedge_before_share']) for c in v), 'n': len(v)} for g, v in by.items()}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'results.json').write_text(json.dumps(res, indent=2) + '\n')
    (out / 'first_ask_texts.json').write_text(json.dumps([{k: e[k] for k in ('episode', 'arm', 'scenario', 'ask_round', 'first_ask_text')} for e in episodes if e['arm'] != 'FORBID_OLD'], indent=1))
    figure(res, out)
    print(json.dumps({k: res[k] for k in ('primary_nonread', 'diff_LATE_minus_FORBID_nonread_round3plus', 'diff_EARLY_minus_FORBID_nonread', 'reading')}, indent=1))


def figure(res, out):
    sys.path.insert(0, str(ROOT / 'paper-arxiv/figures/src'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from style import LABEL_SIZE, configure
    configure()
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(6.0, 2.9))
    offsets = {'FORBID': -.22, 'EARLY': 0, 'LATE': .22}
    for g in ARMS:
        pts = [(i + offsets[g], res['recency'][g][b]) for i, b in enumerate(BINS) if res['recency'][g][b]['n']]
        if not pts:
            continue
        xs = [x for x, _ in pts]
        ys = [r['share'] * 100 for _, r in pts]
        lo = [y - r['wilson95'][0] * 100 for y, (_, r) in zip(ys, pts)]
        hi = [r['wilson95'][1] * 100 - y for y, (_, r) in zip(ys, pts)]
        ax.errorbar(xs, ys, yerr=[lo, hi], color=COLORS[g], marker='o', ms=4, ls='none', lw=1.2, capsize=2, label=g.capitalize())
        for x, (_, r) in zip(xs, pts):
            ax.text(x, r['wilson95'][1] * 100 + 2, str(r['n']), ha='center', va='bottom', fontsize=LABEL_SIZE - 2, color=COLORS[g])
        bx.plot(xs, [r['median_score'] for _, r in pts], color=COLORS[g], marker='o', ms=4, ls='none')
    bx.axhline(res['threshold'], color='#666666', lw=.8, ls='--')
    bx.annotate('threshold', (3.15, res['threshold']), xytext=(0, 3), textcoords='offset points', fontsize=LABEL_SIZE - 1, color='#666666', ha='right')
    for axis in (ax, bx):
        axis.set_xticks(range(len(BINS)), BINS)
        axis.set_xlim(-.4, 3.4)
        axis.set_xlabel('Calls since the last read')
    ax.set_ylim(0, 115)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel('Over threshold (%)')
    bx.set_ylabel('Median probe score')
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc='upper center', ncol=3)
    fig.tight_layout(rect=(0, 0, 1, .9))
    fig.savefig(out / 'recency.pdf')
    fig.savefig(out / 'recency.png', dpi=200)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('calls')
    p.add_argument('episodes')
    p.add_argument('scores', nargs='+')
    p.add_argument('--out', required=True)
    main(p.parse_args())
