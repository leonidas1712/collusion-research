"""CPU near-term labels on replay2 features, retaining every saved split assignment."""
import argparse
import csv
import json
import sys
import shutil
import time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from threadpoolctl import threadpool_limits
from data import ROOT, CANDIDATES
from models import fit_logistic, score
from metrics import within_round, position_weights
from evaluate import ranking_summary, score_bootstrap, finite_mean, interval
from replay2_models import fit_metadata, score_metadata, save_metadata
from replay2_baseline_audit import DATA, FIT
from report import write_json
sys.path.insert(0, str(ROOT/'src'))
from collusion.runs import start_run

VARIANTS = ('A_hazard', 'B_round_contrast', 'C_step_contrast')
MODES = ('pooled', 'loso')
SEEDS = (42, 43, 44)
METHODS = ('eventual_nested', 'eventual_fixed32', 'nested', 'fixed32', 'turn', 'length',
           'scenario_round', 'metadata_base', 'metadata_probe')


def label_rows(rows, variant):
    if variant not in VARIANTS:
        raise ValueError(variant)
    keep = np.zeros(len(rows), dtype=bool)
    y = np.zeros(len(rows), dtype=int)
    for i, r in enumerate(rows):
        if not r['eligible'] or r['condition'] != 'recruiting':
            continue
        assert r['ordinal'] > r['first_read']
        if r['label']:
            assert r['first_action'] > r['ordinal']
            assert r['steps_until_action'] == r['first_action'] - r['ordinal'] > 0
            delta = r['action_round'] - r['round']
            assert delta >= 0
            near = r['steps_until_action'] <= 3 if variant == 'C_step_contrast' else delta <= 1
            y[i] = int(near)
        keep[i] = variant == 'A_hazard' or not r['label'] or bool(y[i])
    return keep, y


def restrict(indices, keep):
    indices = np.asarray(indices, dtype=int)
    return indices[keep[indices]]


def family_subset(rows, indices, families):
    families = set(families)
    return np.array([i for i in indices if rows[i]['family'] in families], dtype=int)


def saved_splits(rows, mode, note, keep):
    source = ROOT/'runs'/FIT/mode
    seed, fold = note['seed'], note['fold']
    with np.load(source/f'split-s{seed}-f{fold}.npz') as d:
        split = {k: restrict(d[k], keep) for k in ('train', 'test', 'inner_train', 'inner_validation')}
    stacking = []
    for s in note['stacking']['folds']:
        train = family_subset(rows, split['train'], s['train_families'])
        test = family_subset(rows, split['train'], s['test_families'])
        validation = family_subset(rows, train, s['inner']['inner_validation_families'])
        if s['inner']['kind'] == 'training_scenario_holdout':
            validation = np.array([i for i in validation if rows[i]['scenario'] == s['inner']['validation_scenario']], dtype=int)
        stacking.append(dict(train=train, test=test,
            inner_train=family_subset(rows, train, s['inner']['inner_train_families']),
            inner_validation=validation))
    return split, stacking


def check_split(rows, y, split):
    train, test = split['train'], split['test']
    assert len(train) and len(test)
    assert not {rows[i]['family'] for i in train} & {rows[i]['family'] for i in test}
    assert set(split['inner_train']) | set(split['inner_validation']) <= set(train)
    assert not {rows[i]['family'] for i in split['inner_train']} & {rows[i]['family'] for i in split['inner_validation']}
    for key in ('train', 'inner_train'):
        idx = split[key]
        assert len(set(y[idx])) == 2, key
        position_weights(y[idx], np.array([rows[i]['round'] for i in idx]))
    val = split['inner_validation']
    metric, _ = within_round(y[val], y[val], np.array([rows[i]['round'] for i in val]),
                            stratum_key=[rows[i]['scenario'] for i in val])
    assert np.isfinite(metric), 'No comparable inner-validation stratum'


def choose_layer(rows, x, y, fit, val, seed):
    rounds = np.array([rows[i]['round'] for i in fit])
    vr = np.array([rows[i]['round'] for i in val])
    vs = [rows[i]['scenario'] for i in val]
    values = {}
    for layer in CANDIDATES:
        model = fit_logistic(x[fit, layer], y[fit], rounds, seed)
        values[layer] = within_round(y[val], score(model, x[val, layer]), vr, stratum_key=vs)[0]
    assert any(np.isfinite(v) for v in values.values())
    selected = max(CANDIDATES, key=lambda k: (values[k] if np.isfinite(values[k]) else -1, -k))
    return selected, values


def save_lr(path, model):
    scaler, clf = model
    np.savez_compressed(path, mean=scaler.mean_, scale=scaler.scale_, coef=clf.coef_, intercept=clf.intercept_)


def fit_case(arguments):
    out, variant, mode, note = arguments
    with threadpool_limits(limits=2):
        start = time.perf_counter()
        rows = [json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
        x = np.load(ROOT/'runs'/DATA/'features.npy', mmap_mode='r')
        keep, y = label_rows(rows, variant)
        split, stacking = saved_splits(rows, mode, note, keep)
        train, test = split['train'], split['test']
        seed, fold = note['seed'], note['fold']
        dest = out/variant/mode/f's{seed}-f{fold}'; dest.mkdir(parents=True)
        rounds = np.array([r['round'] for r in rows])
        layer, selection = choose_layer(rows, x, y, split['inner_train'], split['inner_validation'], seed+fold*17)
        values = {}; reconstruction = {}
        for k in sorted({32, layer}):
            model = fit_logistic(x[train, k], y[train], rounds[train], seed)
            pred = score(model, x[test, k]); save_lr(dest/f'lr-l{k}.npz', model)
            scaler, clf = model
            reconstructed = ((np.asarray(x[test, k], dtype=float)-scaler.mean_)/scaler.scale_)@clf.coef_[0]+clf.intercept_[0]
            reconstruction[k] = float(np.max(np.abs(pred-reconstructed)))
            assert reconstruction[k] < 1e-9
            if k == 32: values['fixed32'] = pred
            if k == layer: values['nested'] = pred
        values['turn'] = -rounds[test].astype(float)
        values['length'] = np.array([rows[i]['n_tokens'] for i in test], dtype=float)
        crossfit = np.full(len(rows), np.nan); stack_notes = []
        for j, s in enumerate(stacking):
            stack_seed = seed+fold*101
            k, inner = choose_layer(rows, x, y, s['inner_train'], s['inner_validation'], stack_seed+j*31)
            model = fit_logistic(x[s['train'], k], y[s['train']], rounds[s['train']], stack_seed)
            assert np.isnan(crossfit[s['test']]).all()
            crossfit[s['test']] = score(model, x[s['test'], k])
            save_lr(dest/f'stack{j}-lr-l{k}.npz', model)
            np.savez_compressed(dest/f'stack{j}-split.npz', **s)
            stack_notes.append(dict(fold=j, layer=k, validation_auroc=inner))
        assert np.isfinite(crossfit[train]).all()
        for method, length, probe in [('scenario_round', False, None), ('metadata_base', True, None),
                                      ('metadata_probe', True, crossfit[train])]:
            model = fit_metadata(rows, train, y[train], include_length=length, probe=probe)
            values[method] = score_metadata(model, rows, test, probe=values['nested'] if probe is not None else None)
            save_metadata(dest/f'{method}.npz', model)
        assert all(np.isfinite(s).all() for s in values.values())
        np.savez_compressed(dest/'scores.npz', **values, **split, y_test=y[test], train_crossfit_probe=crossfit[train])
        record = dict(seed=seed, fold=fold, chosen_layer=layer, validation_auroc=selection,
                      stacking=stack_notes, max_score_reconstruction_error=max(reconstruction.values()),
                      train_rows=len(train), test_rows=len(test), seconds=time.perf_counter()-start)
        write_json(dest/'fit.json', record)
        return variant, mode, seed, fold, record


def evaluate(rows, y, ids, predictions, folds, reps):
    rounds = np.array([rows[i]['round'] for i in ids]); scenarios = [rows[i]['scenario'] for i in ids]
    families = np.array([rows[i]['family'] for i in ids]); names, codes = np.unique(families, return_inverse=True)
    weights = np.random.default_rng(20261024).multinomial(len(names), np.ones(len(names))/len(names), size=reps).astype(float)
    results = {}; boot = {}
    for method, scores in predictions.items():
        summary, wb, pb = ranking_summary(np.tile(y[ids], (3, 1)), scores, rounds, families, reps, stratum_key=scenarios)
        per_seed = []; boots = []; coverage = []
        for si, s in enumerate(scores):
            strata = [(scenario, int(fold)) for scenario, fold in zip(scenarios, folds[si])]
            a, detail = within_round(y[ids], s, rounds, stratum_key=strata)
            b, _ = score_bootstrap(y[ids], s, rounds, codes, weights, stratum_key=strata)
            per_seed.append(a); boots.append(b); coverage.append(detail['positive_coverage'])
        sensitivity_boot = finite_mean(boots, axis=0)
        summary['fold_sensitivity'] = dict(auc=float(finite_mean(per_seed)), by_seed=per_seed,
            ci95=interval(sensitivity_boot), positive_coverage_by_seed=coverage,
            valid_bootstrap_reps=int(np.isfinite(sensitivity_boot).sum()))
        results[method] = summary; boot[method] = (wb, pb, sensitivity_boot)
    differences = {}
    for a, b in [('nested','eventual_nested'), ('fixed32','eventual_fixed32'), ('nested','scenario_round'),
                 ('metadata_probe','metadata_base')]:
        differences[a+'_minus_'+b] = {}
        for j, (metric, mean) in enumerate([
            ('scenario_round', results[a]['within_round_auc']-results[b]['within_round_auc']),
            ('pooled', results[a]['pooled_auc']-results[b]['pooled_auc']),
            ('fold_sensitivity', results[a]['fold_sensitivity']['auc']-results[b]['fold_sensitivity']['auc'])]):
            differences[a+'_minus_'+b][metric] = dict(mean=mean, paired_family_ci95=interval(boot[a][j]-boot[b][j]))
    return dict(methods=results, paired_differences=differences, rows=len(ids), positives=int(y[ids].sum()),
                negatives=int((y[ids]==0).sum()), episodes=len({rows[i]['episode'] for i in ids}), families=len(names))


def summarize(run, rows, reps):
    results = {}; export_count = 0; unique = set()
    fields = ['row_id','step_id','row','analysis','label_variant','seed','fold','score','method','label',
              'eventual_label','rounds_until_action','steps_until_action','episode','request_idx',
              'request_sha256','condition','scenario','round']
    with (run.dir/'probe_scores.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        for variant in VARIANTS:
            keep, y = label_rows(rows, variant); ids = np.flatnonzero(keep); results[variant] = {}
            for mode in MODES:
                preds = {m: np.full((3, len(rows)), np.nan) for m in METHODS}
                folds = np.full((3, len(rows)), -1, dtype=int)
                with np.load(ROOT/'runs'/FIT/mode/'predictions.npz') as old:
                    for method in ('nested','fixed32'): preds['eventual_'+method][:,ids] = old[method][:,ids]
                    for si, seed in enumerate(SEEDS):
                        for fold in range(5 if mode=='pooled' else 6):
                            with np.load(run.dir/variant/mode/f's{seed}-f{fold}'/'scores.npz') as d:
                                test = d['test']; assert (folds[si,test]==-1).all()
                                assert np.array_equal(d['y_test'], y[test])
                                for method in METHODS:
                                    if not method.startswith('eventual_'): preds[method][si,test] = d[method]
                                folds[si,test] = fold
                        assert np.array_equal(folds[si,ids], old['folds'][si,ids])
                assert all(np.isfinite(a[:,ids]).all() for a in preds.values())
                slim = {m:s[:,ids] for m,s in preds.items()}
                np.savez_compressed(run.dir/variant/mode/'predictions.npz', **preds, y=y, eligible=ids, folds=folds, seeds=SEEDS)
                results[variant][mode] = evaluate(rows, y, ids, slim, folds[:,ids], reps)
                for method in METHODS:
                    for si, seed in enumerate(SEEDS):
                        for i in ids:
                            r=rows[i]; rid=r['episode']+'::request_idx='+str(r['request_idx'])
                            key=(rid,variant,mode,method,seed); assert key not in unique; unique.add(key)
                            writer.writerow(dict(row_id=rid,step_id=rid,row=int(i),analysis=mode,label_variant=variant,
                                seed=seed,fold=int(folds[si,i]),score=float(preds[method][si,i]),method=method,label=int(y[i]),
                                eventual_label=r['label'],rounds_until_action=r['action_round']-r['round'] if r['label'] else '',
                                steps_until_action=r['steps_until_action'] if r['label'] else '',
                                **{k:r[k] for k in ('episode','request_idx','request_sha256','condition','scenario','round')}))
                            export_count += 1
                write_json(run.dir/'metrics.json', results)
                print('EVALUATED',variant,mode,flush=True)
    write_report(run, results, export_count)
    return results, export_count


def write_report(run, results, export_count):
    lines = ['# Near-term action probes', '',
        'CPU only; no new episodes or activations. A labels all eligible recruiting steps positive if the first forbidden action occurs this round or next; earlier give-in steps are negative. B drops those earlier give-in steps and retains held negatives. C uses the same clean contrast with 1–3 completed target requests until the first action. Eligibility remains strictly after the first read and strictly before the first action.', '',
        'Outer, inner-validation and three-fold stacking assignments are filtered from the saved replay-2 splits, never reallocated. Layers are reselected within training data (0,4,…,60,63), then logistic regression is refit with the original C=0.1, round-balanced weights and training-only scaling. Added value uses scenario, round and prompt length, then adds a training-cross-fitted near-term probe score; layer selection is repeated within each stacking training split. No MLP or alarm thresholds are fitted here.', '',
        'Intervals are 95% family-bootstrap intervals (1,000 resamples), shared across methods and seeds; three seed estimates are averaged. They condition on the saved splits and fitted models. Scenario × round AUROC is the primary ranking; fold × scenario × round is a sensitivity. Single-class strata are omitted; coverage is in metrics.json. The new labels and contrasts are exploratory, and clean contrasts use hindsight to remove far-from-action steps.', '',
        '| Label | Analysis | Rows (+) | Method | Scenario × round AUROC [95% CI] | Fold sensitivity [95% CI] |',
        '|---|---|---:|---|---|---|']
    fmt = lambda a, ci: f'{a:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]' if ci else f'{a:.3f} [unavailable]'
    for variant, modes in results.items():
        for mode, result in modes.items():
            for method, m in result['methods'].items():
                s=m['fold_sensitivity']
                lines.append(f"| {variant} | {mode} | {result['rows']} ({result['positives']}) | {method} | {fmt(m['within_round_auc'],m['within_round_ci95'])} | {fmt(s['auc'],s['ci95'])} |")
    lines += ['', '## Added value', '', '| Label | Analysis | Pooled AUROC gain [paired family CI] |', '|---|---|---|']
    for variant, modes in results.items():
        for mode, result in modes.items():
            d=result['paired_differences']['metadata_probe_minus_metadata_base']['pooled']
            lines.append(f"| {variant} | {mode} | {fmt(d['mean'],d['paired_family_ci95'])} |")
    lines += ['', '## Score export and provenance', '',
        f'`probe_scores.csv` has {export_count:,} records. The unique key is `(row_id, analysis, label_variant, method, seed)`. E06 row IDs and request hashes are preserved. `nested` and `fixed32` are near-term refits; `eventual_nested` and `eventual_fixed32` are frozen original eventual-label scores, evaluated without refitting. All baselines are exported too. Only eligible recruiting rows are included; these are ranking results, not a benign-calibrated alarm analysis.', '',
        f'Parents: `{DATA}` (features/rows), `{FIT}` (all split assignments and frozen eventual scores). Individual fit coefficients, splits, training-cross-fitted stacking scores and selection logs are saved beneath each variant/analysis. `labels.jsonl` includes every original row, variant membership and both labels for exact monitor alignment. `preflight.json` records split checks. Every exported fitted fold matches the original assignment; saved predictions are finite and selected/fixed logistic scores reconstruct within 1e-9.']
    (run.dir/'report.md').write_text('\n'.join(lines)+'\n')


def main(args):
    rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
    run=start_run('e05-near-term',experiment='E05',parents=[DATA,FIT]+([args.reuse_run] if args.reuse_run else []),settings=dict(
        variants=VARIANTS,analyses=MODES,seeds=SEEDS,candidate_layers=CANDIDATES,
        bootstrap_reps=args.reps,split_policy='filter original outer, inner and stacking splits',
        cpu_workers=args.workers,threads_per_worker=2,no_gpu=True))
    try:
        jobs=[]; preflight=[]; labels=[]
        for variant in VARIANTS:
            keep,y=label_rows(rows,variant)
            for i,r in enumerate(rows):
                labels.append(dict(row=i,row_id=r['episode']+'::request_idx='+str(r['request_idx']),
                    request_sha256=r['request_sha256'],label_variant=variant,included=bool(keep[i]),
                    label=int(y[i]) if keep[i] else None,eventual_label=r['label'],round=r['round'],
                    action_round=r['action_round'],steps_until_action=r['steps_until_action']))
            for mode in MODES:
                notes=json.loads((ROOT/'runs'/FIT/mode/'folds.json').read_text())
                for note in notes:
                    split,stack=saved_splits(rows,mode,note,keep); check_split(rows,y,split)
                    for s in stack:check_split(rows,y,s)
                    assert sorted(np.concatenate([s['test'] for s in stack]))==sorted(split['train'])
                    if mode=='loso':
                        assert not {rows[i]['scenario'] for i in split['train']} & {rows[i]['scenario'] for i in split['test']}
                    preflight.append(dict(variant=variant,mode=mode,seed=note['seed'],fold=note['fold'],
                        train=len(split['train']),test=len(split['test']),positives=int(y[split['test']].sum())))
                    jobs.append((run.dir,variant,mode,note))
        write_json(run.dir/'preflight.json',preflight)
        (run.dir/'labels.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in labels))
        print('PREFLIGHT PASSED',len(jobs),'outer fits',flush=True)
        if args.preflight_only:
            run.result(preflight_passed=True);run.finish();print('NEAR_TERM_PREFLIGHT',run.id);return
        completed=[]; pending=[]
        for job in jobs:
            _, variant, mode, note = job
            relative = f"{variant}/{mode}/s{note['seed']}-f{note['fold']}"
            prior = ROOT/'runs'/args.reuse_run/relative if args.reuse_run else None
            if prior and mode == 'pooled' and (prior/'fit.json').exists():
                keep, _ = label_rows(rows, variant)
                split, stack = saved_splits(rows, mode, note, keep)
                with np.load(prior/'scores.npz') as d:
                    for key, indices in split.items():assert np.array_equal(d[key], indices)
                for j, expected in enumerate(stack):
                    with np.load(prior/f'stack{j}-split.npz') as d:
                        for key, indices in expected.items():assert np.array_equal(d[key], indices)
                dest=run.dir/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(prior,dest)
                record=json.loads((dest/'fit.json').read_text())
                completed.append(dict(variant=variant,mode=mode,reused_from=args.reuse_run,**record))
            else:pending.append(job)
        print('REUSED',len(completed),'completed pooled fits',flush=True)
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            for variant,mode,seed,fold,record in executor.map(fit_case,pending):
                completed.append(dict(variant=variant,mode=mode,**record))
                write_json(run.dir/'progress.json',completed)
                print('FIT',len(completed),'/',len(jobs),variant,mode,seed,fold,'seconds',round(record['seconds'],1),flush=True)
        with threadpool_limits(limits=2):
            results,n=summarize(run,rows,args.reps)
        run.result(outer_fits=len(completed),export_rows=n,complete=True);run.finish();print('NEAR_TERM_RUN',run.id)
    except BaseException as exc:
        run.finish('failed',str(exc));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=3);p.add_argument('--reps',type=int,default=1000)
    p.add_argument('--preflight-only',action='store_true');p.add_argument('--reuse-run');main(p.parse_args())
