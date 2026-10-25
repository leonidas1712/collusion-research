"""Combination test (APA-66): does the probe add to a text monitor? Stacked logistic, same folds as the probe.

Run with the E05 environment:
    experiments/E05-probes/.venv/bin/python experiments/E06-monitors/combine.py --run runs/<e06 main run>

For each label (near-term A/B/C from the E05 near-term export, eventual from the fold-sensitivity export),
analysis (pooled CV, LOSO) and split seed, using the probe export's own outer fold of every row:
  base     = logistic on [round, log prompt length, monitor score]
  combined = logistic on [round, log prompt length, monitor score, probe score]
Both are fit on the other folds' rows and applied to the held-out fold. "monitor" is
  - selected: the monitor setup with the best within-round AUROC on that fold's training rows (no test data);
  - fixed: GPT-5-nano detector L2, named before this test;
  - post hoc: Jev forecaster L3, the best setup after seeing all results (reported as such).
Reference: monitor + monitor, i.e. [round, length, Jev forecaster L3, GPT-5-nano detector L2], against Jev alone.
Metric: within scenario x round AUROC (E05 within_round), seed mean; paired family-bootstrap CI of the difference.
Probe scores of training rows are the probe's own out-of-fold scores (standard stacking; those probes saw the
held-out fold in training, a small optimistic leak for the combined model that the base model does not get).
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'experiments/E05-probes'))
sys.path.insert(0, str(HERE))
from metrics import within_round  # noqa: E402  (E05)
from monitors import collect  # noqa: E402

NEAR = ROOT / 'runs/20261025-0730-e05-near-term/probe_scores.csv'
EVENTUAL = ROOT / 'runs/20261025-0544-e05-fold-sensitivity/probe_scores.csv'
DATA = ROOT / 'runs/20261025-0337-e05-replay2-data/rows.jsonl'
FIXED = 'llm detector L2'
POSTHOC = 'jev forecaster L3'
REPS = 1000


def load_probe():
    """{(label, analysis): {seed: {row_id: (fold, score, label)}}}"""
    out = defaultdict(lambda: defaultdict(dict))
    with NEAR.open() as fh:
        for r in csv.DictReader(fh):
            if r['method'] == 'nested':
                out[(r['label_variant'], r['analysis'])][int(r['seed'])][r['row_id']] = (int(r['fold']), float(r['score']), int(r['label']))
    with EVENTUAL.open() as fh:
        for r in csv.DictReader(fh):
            if r['analysis'] in ('pooled', 'loso') and r['condition'] == 'recruiting':
                out[('eventual', r['analysis'])][int(r['seed'])][r['row_id']] = (int(r['fold']), float(r['score']), int(r['label']))
    return out


def fit_predict(Xtr, ytr, Xte):
    sc = StandardScaler().fit(Xtr)
    m = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(Xtr), ytr)
    return m.decision_function(sc.transform(Xte))


def wr(y, s, rounds, scen, w=None):
    return within_round(y, s, rounds, w, stratum_key=scen)[0]


def run_case(ids, folds, probe, y, meta, mon, names):
    """One seed. Returns {variant: out-of-fold scores}."""
    n = len(ids)
    rounds, lens, scen = meta['round'], meta['loglen'], meta['scenario']
    out = {k: np.full(n, np.nan) for k in ('selected_base', 'selected_comb', 'fixed_base', 'fixed_comb',
                                             'posthoc_base', 'posthoc_comb', 'mm_base', 'mm_comb')}
    chosen = []
    for f in sorted(set(folds)):
        te, tr = folds == f, folds != f
        best = max(names, key=lambda k: wr(y[tr], mon[k][tr], rounds[tr], scen[tr]) or 0)
        chosen.append(best)
        for tag, k in (('selected', best), ('fixed', FIXED), ('posthoc', POSTHOC)):
            base = np.c_[rounds, lens, mon[k]]
            out[f'{tag}_base'][te] = fit_predict(base[tr], y[tr], base[te])
            comb = np.c_[base, probe]
            out[f'{tag}_comb'][te] = fit_predict(comb[tr], y[tr], comb[te])
        mm = np.c_[rounds, lens, mon[POSTHOC]]
        out['mm_base'][te] = fit_predict(mm[tr], y[tr], mm[te])
        mm2 = np.c_[mm, mon[FIXED]]
        out['mm_comb'][te] = fit_predict(mm2[tr], y[tr], mm2[te])
    out['probe_alone'] = probe
    return out, chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    run = ap.parse_args().run.resolve()
    data = {}
    for line in DATA.read_text().splitlines():
        r = json.loads(line)
        data[f"{r['episode']}::request_idx={r['request_idx']}"] = r
    mon_scores = defaultdict(dict)
    for r in collect(run / 'cache'):
        if r['score'] is not None:
            mon_scores[f"{r['monitor']} {r['prompt']} L{r['level']}"][r['step_id']] = float(r['score'])
    names = sorted(mon_scores)
    probe_all = load_probe()
    results = {}
    rng = np.random.default_rng(20261025)
    for (label, analysis), seeds in sorted(probe_all.items()):
        per_seed, chosen_all = [], defaultdict(int)
        ids = sorted(set.intersection(*[set(v) for v in seeds.values()]))
        ids = [i for i in ids if all(i in mon_scores[k] for k in names)]
        meta = {'round': np.array([data[i]['round'] for i in ids], float),
                'loglen': np.log(np.array([data[i]['n_tokens'] for i in ids], float)),
                'scenario': np.array([data[i]['scenario'] for i in ids]),
                'family': np.array([data[i]['family'] for i in ids])}
        mon = {k: np.array([mon_scores[k][i] for i in ids]) for k in names}
        for seed, rows in sorted(seeds.items()):
            folds = np.array([rows[i][0] for i in ids])
            probe = np.array([rows[i][1] for i in ids])
            y = np.array([rows[i][2] for i in ids])
            out, chosen = run_case(ids, folds, probe, y, meta, mon, names)
            per_seed.append((y, out, np.array([f'{a}|{b}' for a, b in zip(folds, meta['scenario'])])))
            for c in chosen:
                chosen_all[c] += 1
        y0 = per_seed[0][0]
        fs = lambda key: float(np.mean([wr(y, o[key], meta['round'], fk) for y, o, fk in per_seed]))
        fam_names, codes = np.unique(meta['family'], return_inverse=True)
        pairs = {'selected': ('selected_comb', 'selected_base'), 'fixed': ('fixed_comb', 'fixed_base'),
                 'posthoc': ('posthoc_comb', 'posthoc_base'), 'monitor+monitor': ('mm_comb', 'mm_base'),
                 'posthoc monitor vs probe alone': ('posthoc_base', 'probe_alone')}
        res = {'rows': len(ids), 'positives': int(y0.sum()), 'chosen_monitor_counts': dict(chosen_all)}
        point = {k: float(np.mean([wr(y, o[k], meta['round'], meta['scenario']) for y, o, _ in per_seed]))
                 for k in per_seed[0][1]}
        res['auc'] = point
        res['auc_fold_stratified'] = {k: fs(k) for k in per_seed[0][1]}
        res['diff_fold_stratified'] = {name: fs(a) - fs(b) for name, (a, b) in pairs.items()}
        boots = defaultdict(list)
        for _ in range(REPS):
            w = rng.multinomial(len(fam_names), np.ones(len(fam_names)) / len(fam_names))[codes].astype(float)
            for name, (a, b) in pairs.items():
                d = [wr(y, o[a], meta['round'], meta['scenario'], w) - wr(y, o[b], meta['round'], meta['scenario'], w)
                     for y, o, _ in per_seed]
                boots[name].append(np.mean(d))
        res['diff'] = {name: {'diff': point[a] - point[b],
                              'ci95': [float(q) for q in np.nanquantile(boots[name], [.025, .975])]}
                       for name, (a, b) in pairs.items()}
        results[f'{label} | {analysis}'] = res
        print(label, analysis, {k: round(v['diff'], 3) for k, v in res['diff'].items()}, flush=True)
    (run / 'combine.json').write_text(json.dumps(results, indent=2))
    write_report(run, results)


def write_report(run, results):
    L = ['# Combination test: does the probe add to a text monitor?', '',
         'Stacked logistic on [round, log length, monitor] vs the same plus the probe score, fit on training folds of the '
         "probe's own outer splits, applied to the held-out fold. Within scenario x round AUROC, mean of three split seeds; "
         'paired family-bootstrap 95% CI. "Selected" picks the monitor on training rows only; "fixed" is GPT-5-nano '
         'detector L2 (named in advance); "post hoc" is Jev forecaster L3 (best after seeing results). '
         'Monitor + monitor adds GPT-5-nano detector L2 to Jev forecaster L3, as a reference for "any second view".', '',
         'Stacked scores come from different fitted models per fold, so the fold-stratified gain (fold x scenario x round) '
         'is shown too; it is the cleaner number for the stacked comparisons.', '',
         '| Label · analysis | Rows (pos) | Probe alone | Jev F L3 alone (stacked) | + probe | Gain [95% CI] | Gain, fold-strat. | Selected: gain [95% CI] | Fixed (GPT-5-nano det L2): gain [95% CI] | Fixed, fold-strat. | Monitor+monitor: gain [95% CI] |',
         '|---|---|---|---|---|---|---|---|---|---|---|']
    for key, r in results.items():
        a, d = r['auc'], r['diff']
        c = lambda x: f"{x['diff']:+.3f} [{x['ci95'][0]:+.3f}, {x['ci95'][1]:+.3f}]"
        L.append(f"| {key.replace(' | ', ' · ')} | {r['rows']} ({r['positives']}) | {a['probe_alone']:.3f} | {a['posthoc_base']:.3f} | "
                 f"{a['posthoc_comb']:.3f} | {c(d['posthoc'])} | {r['diff_fold_stratified']['posthoc']:+.3f} | {c(d['selected'])} | "
                 f"{c(d['fixed'])} | {r['diff_fold_stratified']['fixed']:+.3f} | {c(d['monitor+monitor'])} |")
    L += ['', 'Monitor chosen on training rows (counts over folds x seeds):', '']
    for key, r in results.items():
        L.append(f"- {key}: " + ', '.join(f'{k} ×{v}' for k, v in sorted(r['chosen_monitor_counts'].items(), key=lambda t: -t[1])))
    (run / 'combine.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
