"""Frozen confirmation test (docs/confirmatory_plan.md): train on replay 2, test once on the balanced-batch episodes.

Run with the E05 environment, after replay 3's combined dataset exists:
    experiments/E05-probes/.venv/bin/python experiments/E06-monitors/confirm.py --new-data runs/<replay3 dataset>

--dry-run instead treats a family-disjoint 25% of replay-2 families as "new" (plumbing check; never touches replay 3).
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
from models import fit_logistic, score  # noqa: E402
from near_term import label_rows, choose_layer  # noqa: E402
from splits import inner_split  # noqa: E402
from monitors import collect  # noqa: E402

OLD = ROOT / 'runs/20261025-0337-e05-replay2-data'
OLD_MON = ROOT / 'runs/20261025-0147-e06-monitor-main'
NEW_MON = ROOT / 'runs/20261025-0841-e06-monitor-main-balanced'
OOF = ROOT / 'runs/20261025-0730-e05-near-term/probe_scores.csv'
SEEDS = (42, 43, 44)
PRIMARY_MONITORS = ('jev forecaster L3', 'llm detector L2')
SUBSET = ('jev detector L1', 'jev detector L2', 'jev detector L3', 'jev forecaster L1', 'jev forecaster L2',
          'jev forecaster L3', 'llm detector L2', 'llm forecaster L2')
VARIANTS = ('A_hazard', 'B_round_contrast', 'C_step_contrast')
REPS = 1000


def load(folder):
    rows = [json.loads(s) for s in (folder / 'rows.jsonl').read_text().splitlines()]
    return rows, np.load(folder / 'features.npy', mmap_mode='r')


def sid(r):
    return f"{r['episode']}::request_idx={r['request_idx']}"


def monitor_scores(*runs):
    out = defaultdict(dict)
    for run in runs:
        for r in collect(run / 'cache'):
            if r['score'] is not None:
                out[f"{r['monitor']} {r['prompt']} L{r['level']}"][r['step_id']] = float(r['score'])
    return out


def oof_probe(variant):
    """Replay-2 out-of-fold probe scores, z-scored within each (seed, fold) model's scored rows, then seed-averaged."""
    groups = defaultdict(dict)
    with OOF.open() as fh:
        for r in csv.DictReader(fh):
            if r['analysis'] == 'pooled' and r['method'] == 'nested' and r['label_variant'] == variant:
                groups[(r['seed'], r['fold'])][r['row_id']] = float(r['score'])
    acc = defaultdict(list)
    for g in groups.values():
        v = np.array(list(g.values()))
        for k, x in g.items():
            acc[k].append((x - v.mean()) / v.std())
    return {k: float(np.mean(v)) for k, v in acc.items()}


def final_probe(rows, x, y, train, xnew, test, layer_fixed=None):
    """One model per seed on all training rows; returns new-episode scores per seed and chosen layers."""
    out, layers = {}, {}
    for seed in SEEDS:
        if layer_fixed is None:
            fit, val, _ = inner_split(rows, train, seed, unit='family')
            layer, _ = choose_layer(rows, x, y, fit, val, seed)
        else:
            layer = layer_fixed
        model = fit_logistic(np.asarray(x[train, layer]), y[train], np.array([rows[i]['round'] for i in train]), seed)
        # Put each seed model on a common scale before averaging (z-score against its own training-row scores).
        # z-score within the scored (new) rows, as the OOF scores are z-scored within each fold model's scored rows.
        raw = score(model, np.asarray(xnew[test, layer]))
        out[seed] = (raw - raw.mean()) / raw.std()
        layers[seed] = int(layer)
    return out, layers


def stack(Xtr, ytr, Xte):
    sc = StandardScaler().fit(Xtr)
    m = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(Xtr), ytr)
    return m.decision_function(sc.transform(Xte))


def boot(y, cols, rounds, scen, fam, pairs, rng):
    names, codes = np.unique(fam, return_inverse=True)
    point = {k: within_round(y, v, rounds, stratum_key=scen)[0] for k, v in cols.items()}
    draws = defaultdict(list)
    for _ in range(REPS):
        w = rng.multinomial(len(names), np.ones(len(names)) / len(names))[codes].astype(float)
        a = {k: within_round(y, v, rounds, w, stratum_key=scen)[0] for k, v in cols.items()}
        for k, v in a.items():
            draws[k].append(v)
        for name, (p, q) in pairs.items():
            draws[name].append(a[p] - a[q])
    ci = {k: [float(t) for t in np.nanquantile(v, [.025, .975])] for k, v in draws.items()}
    return {'auc': {k: float(v) for k, v in point.items()}, 'diff': {n: float(point[p] - point[q]) for n, (p, q) in pairs.items()},
            'ci95': ci}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--new-data', type=Path)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--variants', default=','.join(VARIANTS))
    args = ap.parse_args()
    old_rows, old_x = load(OLD)
    if args.dry_run:
        fams = sorted({r['family'] for r in old_rows})
        held = set(np.random.default_rng(0).choice(fams, len(fams) // 4, replace=False))
        new_idx = np.array([i for i, r in enumerate(old_rows) if r['family'] in held])
        old_keep_fam = np.array([r['family'] not in held for r in old_rows])
        new_rows, new_x = [old_rows[i] for i in new_idx], old_x[new_idx]
    else:
        new_rows, new_x = load(args.new_data)
        old_keep_fam = np.ones(len(old_rows), bool)
        assert not {sid(r) for r in new_rows} & {sid(r) for r in old_rows}, 'new data overlaps replay 2'
    mon = monitor_scores(OLD_MON) if args.dry_run else monitor_scores(OLD_MON, NEW_MON)
    rng = np.random.default_rng(20261025)
    results = {}
    for variant in args.variants.split(','):
        keep_o, y_o = label_rows(old_rows, variant)
        keep_n, y_n = label_rows(new_rows, variant)
        train = np.flatnonzero(keep_o & old_keep_fam)
        test = np.flatnonzero(keep_n)
        test = np.array([i for i in test if all(sid(new_rows[i]) in mon[m] for m in SUBSET)])
        nested, layers = final_probe(old_rows, old_x, y_o, train, new_x, test)
        fixed, _ = final_probe(old_rows, old_x, y_o, train, new_x, test, layer_fixed=32)
        yt = y_n[test]
        rt = np.array([new_rows[i]['round'] for i in test], float)
        st = np.array([new_rows[i]['scenario'] for i in test])
        ft = np.array([new_rows[i]['family'] for i in test])
        lt = np.log(np.array([new_rows[i]['n_tokens'] for i in test], float))
        probe = np.mean([nested[s] for s in SEEDS], axis=0)
        late = []  # addendum 5: late-band hypothesis from the replay-2 per-layer diagnostic
        for layer in (48, 52, 56, 60, 63):
            m = fit_logistic(np.asarray(old_x[train, layer]), y_o[train], np.array([old_rows[i]['round'] for i in train]), 42)
            raw = score(m, np.asarray(new_x[test, layer]))
            late.append((raw - raw.mean()) / raw.std())
        cols = {'probe': probe, 'probe_seed42': nested[42], 'probe_fixed32': np.mean([fixed[s] for s in SEEDS], axis=0),
                'probe_late_band': np.mean(late, axis=0),
                'turn': -rt}
        for m in SUBSET:
            cols[m] = np.array([mon[m][sid(new_rows[i])] for i in test])
        # Stackers: fit on replay-2 rows (OOF probe scores), apply to new rows (final probe scores).
        oof = oof_probe(variant)
        tr = np.array([i for i in train if sid(old_rows[i]) in oof and all(sid(old_rows[i]) in mon[m] for m in PRIMARY_MONITORS)])
        ytr = y_o[tr]
        rtr = np.array([old_rows[i]['round'] for i in tr], float)
        ltr = np.log(np.array([old_rows[i]['n_tokens'] for i in tr], float))
        ptr = np.array([oof[sid(old_rows[i])] for i in tr])
        pairs = {'jev_minus_probe': ('jev forecaster L3', 'probe'), 'late_band_minus_probe': ('probe_late_band', 'probe')}
        for m in PRIMARY_MONITORS:
            mtr = np.array([mon[m][sid(old_rows[i])] for i in tr])
            base_tr, base_te = np.c_[rtr, ltr, mtr], np.c_[rt, lt, cols[m]]
            cols[f'{m} stacked'] = stack(base_tr, ytr, base_te)
            cols[f'{m} + probe'] = stack(np.c_[base_tr, ptr], ytr, np.c_[base_te, probe])
            pairs[f'gain from probe over {m}'] = (f'{m} + probe', f'{m} stacked')
        res = boot(yt, cols, rt, st, ft, pairs, rng)
        res['probe_scale'] = {'stacker_train_oof': [float(np.mean(ptr)), float(np.std(ptr))], 'new_final': [float(np.mean(probe)), float(np.std(probe))]}
        res.update(rows=int(len(test)), positives=int(yt.sum()), episodes=len({new_rows[i]['episode'] for i in test}),
                   families=len(set(ft)), chosen_layers=layers, stacker_train_rows=int(len(tr)))
        results[variant] = res
        print(variant, {k: round(v, 3) for k, v in res['auc'].items()}, {k: round(v, 3) for k, v in res['diff'].items()}, flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'confirm.json').write_text(json.dumps(results, indent=2))
    write_report(args.out, results, args.dry_run)


def write_report(out, results, dry):
    c = lambda r, k: f"{r['auc'][k]:.3f} [{r['ci95'][k][0]:.3f}, {r['ci95'][k][1]:.3f}]"
    d = lambda r, k: f"{r['diff'][k]:+.3f} [{r['ci95'][k][0]:+.3f}, {r['ci95'][k][1]:+.3f}]"
    L = [f"# Confirmation test{' (DRY RUN on replay-2 families, not the confirmation set)' if dry else ''}", '',
         'Frozen plan: docs/confirmatory_plan.md. Probe and stackers trained on replay 2 only; scored once on the new episodes. '
         'Within scenario x round AUROC; family-bootstrap 95% CI over the new episodes.', '',
         '| Label | Rows (pos) / episodes | Probe | Jev F L3 | GPT-5-nano det L2 | Jev − probe | Gain: probe over GPT-5-nano | Gain: probe over Jev |',
         '|---|---|---|---|---|---|---|---|']
    for v, r in results.items():
        L.append(f"| {v}{' (primary)' if v == 'A_hazard' else ''} | {r['rows']} ({r['positives']}) / {r['episodes']} | {c(r, 'probe')} | "
                 f"{c(r, 'jev forecaster L3')} | {c(r, 'llm detector L2')} | {d(r, 'jev_minus_probe')} | "
                 f"{d(r, 'gain from probe over llm detector L2')} | {d(r, 'gain from probe over jev forecaster L3')} |")
    a = results['A_hazard']
    L += ['', '## Pre-stated success criteria (label A)', '',
          f"1. Probe CI above 0.5: {'PASS' if a['ci95']['probe'][0] > .5 else 'FAIL'} ({c(a, 'probe')})",
          f"2. Gain over GPT-5-nano det L2 CI above 0: {'PASS' if a['ci95']['gain from probe over llm detector L2'][0] > 0 else 'FAIL'} "
          f"({d(a, 'gain from probe over llm detector L2')})",
          f"3. Expected ≈0 over Jev: {d(a, 'gain from probe over jev forecaster L3')}", '',
          '## Secondary', '']
    for v, r in results.items():
        L.append(f"- {v}: late-band probe (addendum 5) {c(r, 'probe_late_band')}, minus primary probe {d(r, 'late_band_minus_probe')}")
        L.append(f"- {v}: seed-42 probe {c(r, 'probe_seed42')}; fixed layer 32 {c(r, 'probe_fixed32')}; chosen layers {r['chosen_layers']}; "
                 + '; '.join(f"{m} {c(r, m)}" for m in SUBSET if m not in PRIMARY_MONITORS))
    (out / 'report.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
