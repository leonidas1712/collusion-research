"""Post-hoc fold-stratified ranking and E06 export from frozen OOF scores."""
import csv
import json
import sys
import numpy as np
from data import ROOT
from metrics import within_round
from report import write_json
from replay2_baseline_audit import DATA, FIT, ANALYSIS
sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run

METHODS = ('nested', 'fixed32', 'band26_30', 'dom32', 'mlp', 'turn', 'length',
           'scenario_only', 'scenario_round', 'metadata_base', 'metadata_probe', 'shuffled32')
FOLDS = '20261025-0240-e05-replay2-folds'


def main():
    rows = [json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
    reference = [json.loads(s) for s in (ROOT/'runs'/FOLDS/'rows.jsonl').read_text().splitlines()]
    assert len(rows) == len(reference)
    for a, b in zip(rows, reference):
        for key in ('episode', 'request_idx', 'request_sha256', 'prompt_sha256'):
            assert a[key] == b[key], (a['index'], key)
    run = start_run('e05-fold-sensitivity', experiment='E05', parents=[DATA, FIT, ANALYSIS, FOLDS],
                    settings={'post_hoc': True, 'no_refits': True, 'strata': 'fold x scenario x round',
                              'export_probe': 'nested logistic', 'ranking_rows': 'eligible recruiting'})
    try:
        results = {}; exported = 0; keys = set()
        fields = ['row_id', 'step_id', 'row', 'analysis', 'seed', 'fold', 'score', 'method',
                  'episode', 'request_idx', 'request_sha256', 'condition', 'scenario', 'round', 'label']
        with (run.dir/'probe_scores.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
            for mode in ('pooled', 'loso', 'v2'):
                with np.load(ROOT/'runs'/FIT/mode/'predictions.npz') as d:
                    eligible = d['eligible']
                    if mode in ('pooled', 'loso'):
                        assert np.array_equal(eligible, np.load(ROOT/'runs'/FOLDS/'eligible.npy'))
                    head = eligible[[rows[i]['condition'] == 'recruiting' for i in eligible]]
                    rounds = np.array([rows[i]['round'] for i in head])
                    scenarios = [rows[i]['scenario'] for i in head]
                    methods = {}
                    for method in METHODS:
                        if method not in d:
                            methods[method] = {'available': False}; continue
                        seeds = []
                        for si, seed in enumerate(d['seeds']):
                            scores = d[method][si, head]
                            assert np.isfinite(scores).all()
                            y = d['shuffled_labels'][si, head] if method == 'shuffled32' else d['y'][head]
                            folds = d['folds'][si, head]; assert (folds >= 0).all()
                            pre, pd = within_round(y, scores, rounds, stratum_key=scenarios)
                            post, detail = within_round(y, scores, rounds,
                                stratum_key=[(s, int(k)) for s, k in zip(scenarios, folds)])
                            seeds.append(dict(seed=int(seed), predeclared=pre, post_hoc=post,
                                predeclared_positive_coverage=pd['positive_coverage'],
                                post_hoc_positive_coverage=detail['positive_coverage']))
                        methods[method] = dict(available=True, by_seed=seeds,
                            predeclared=float(np.mean([v['predeclared'] for v in seeds])),
                            post_hoc=float(np.mean([v['post_hoc'] for v in seeds])))
                    results[mode] = dict(eligible_rows=len(eligible), recruiting_rows=len(head), methods=methods)
                    for si, seed in enumerate(d['seeds']):
                        for i in eligible:
                            r = rows[i]; rid = r['episode']+'::request_idx='+str(r['request_idx'])
                            key = (rid, mode, int(seed)); assert key not in keys; keys.add(key)
                            score = float(d['nested'][si, i]); assert np.isfinite(score)
                            writer.writerow(dict(row_id=rid, step_id=rid, row=int(i), analysis=mode,
                                seed=int(seed), fold=int(d['folds'][si, i]), score=score, method='nested',
                                **{k:r[k] for k in fields if k in ('episode','request_idx','request_sha256','condition','scenario','round','label')}))
                            exported += 1
        with (run.dir/'probe_scores.csv').open() as f:
            saved = list(csv.DictReader(f))
        assert len(saved) == exported == 29214
        for r in saved:
            source = rows[int(r['row'])]
            assert r['request_sha256'] == source['request_sha256']
            assert int(r['fold']) >= 0
        write_json(run.dir/'metrics.json', results)
        lines = ['# Frozen-score fold sensitivity (post hoc)', '',
            'No refits or GPU work. Original scenario × round estimates remain predeclared. The sensitivity adds fitted fold to each stratum, separately for each seed, then averages the three seed AUROCs. Only eligible recruiting rows enter ranking. Strata without both labels are omitted; per-seed positive coverage is in metrics.json. Differences can reflect changed comparable rows as well as cross-fold score shifts. No new confidence intervals are estimated.', '',
            '| Analysis | Method | Predeclared | Post hoc fold × scenario × round |',
            '|---|---|---:|---:|']
        for mode, result in results.items():
            for method, v in result['methods'].items():
                if v['available']:
                    lines.append(f"| {mode} | {method} | {v['predeclared']:.6f} | {v['post_hoc']:.6f} |")
                else:
                    lines.append(f'| {mode} | {method} | unavailable | unavailable |')
        lines += ['', 'Pooled MLP was not fitted in the original recipe. Its saved v2 and LOSO scores are included; no new fit was made. Shuffled32 uses its saved shuffled labels, as in the original null analysis.', '',
            '## E06 score export', '',
            '`probe_scores.csv` contains the inner-selected (nested) logistic probe, one row per `(row_id, analysis, seed)`: 29,214 records. `row_id` and `step_id` both use E06’s `episode::request_idx=N` identifier; `row` is the original integer E05 index. Pooled and LOSO each have 4,184 rows × 3 seeds; v2 has 1,370 × 3. Scores are untransformed saved decision scores. Control and alone rows are included for alarm evaluation; filter `condition == recruiting` for headline ranking. Fold labels are analysis- and seed-specific.', '',
            'All source episode/request/hash identities match the pre-exported E06 fold table; pooled and LOSO eligible indices match exactly. CSV keys, finite scores, fold assignments and round-trip hashes are checked. For calibration, use the original fit split/calibration files: this export contains OOF scores, not training-fold calibration predictions. Existing frozen threshold arrays remain in the source predictions.npz files.', '',
            f'Sources: `{DATA}`, `{FIT}`, `{FOLDS}`.']
        (run.dir/'report.md').write_text('\n'.join(lines)+'\n')
        run.result(exported_records=exported, no_refits=True); run.finish(); print(run.id)
    except BaseException as exc:
        run.finish('failed', str(exc)); raise


if __name__ == '__main__':
    main()
