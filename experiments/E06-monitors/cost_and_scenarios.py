"""Compare cached near-term predictions by billed cost and scenario; no model calls."""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/E05-probes'))
from all_data_main import read_rows, labels, row_id, MONITORS, DATA
from evaluate import ranking_summary
sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run

SOURCE = '20261025-1456-e05-all-data-main'
SEEDS = [42, 43, 44]


def write_csv(path, records):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main():
    run = start_run('e06-cost-and-scenarios', experiment='E06', parents=[SOURCE, DATA, *MONITORS],
                    settings={'label': 'A_hazard', 'bootstrap_reps': 1000, 'bootstrap_seed': 20261025})
    rows = read_rows()
    keep, all_y = labels(rows, 'A_hazard')
    indices = np.flatnonzero(keep)
    selected = [rows[i] for i in indices]
    lookup = {row_id(r): i for i, r in enumerate(selected)}
    y = all_y[indices]
    assert len(indices) == 4697 and y.sum() == 250
    rounds = np.array([r['round'] for r in selected])
    families = np.array([r['family'] for r in selected])
    scenarios = np.array([r['scenario'] for r in selected])
    scores = {f'probe {mode}': np.full((3, len(y)), np.nan) for mode in ['pooled', 'loso']}
    with (ROOT / 'runs' / SOURCE / 'probe_scores.csv').open() as f:
        for r in csv.DictReader(f):
            if r['label_variant'] != 'A_hazard' or r['method'] != 'nested':
                continue
            i = lookup[r['row_id']]
            assert r['request_sha256'] == selected[i]['request_sha256'] and int(r['label']) == y[i]
            s = scores[f"probe {r['analysis']}"]
            k = SEEDS.index(int(r['seed']))
            assert np.isnan(s[k, i])
            s[k, i] = float(r['score'])
    sources = [json.loads((ROOT/'runs'/name/'scores.json').read_text()) for name in MONITORS]
    name_of = lambda r: f"{r['monitor']} {r['prompt']} L{r['level']}"
    methods = sorted(set(map(name_of, sources[0])) & set(map(name_of, sources[1])))
    assert len(methods) == 8
    costs = {name: np.full(len(y), np.nan) for name in methods}
    all_costs = defaultdict(list)
    audits = []
    for source, records in zip(MONITORS, sources):
        billed = defaultdict(float)
        total = 0.0
        states = defaultdict(int)
        for path in (ROOT/'runs'/source).glob('budget*.json'):
            ledger = json.loads(path.read_text())
            entries = next(v for v in ledger.values() if isinstance(v, list))
            subtotal = 0.0
            for entry in entries:
                states[entry['state']] += 1
                assert entry['state'] == 'billed', entry['state']
                cost = float(entry['cost'])
                billed[entry['key']] += cost
                subtotal += cost
            assert np.isclose(subtotal, float(ledger['billed']), atol=1e-9)
            total += subtotal
        for r in records:
            assert r['cost'] is not None and np.isclose(r['cost'], billed[r['key']], atol=1e-10)
            name = name_of(r)
            if name not in methods:
                continue
            all_costs[name].append(float(r['cost']))
            if r['step_id'] not in lookup:
                continue
            i = lookup[r['step_id']]
            assert r['request_sha256'] == selected[i]['request_sha256'] and r['parse_error'] is None
            s = scores.setdefault(name, np.full((3, len(y)), np.nan))
            assert np.isnan(s[:, i]).all()
            s[:, i] = float(r['score'])
            costs[name][i] = r['cost']
        cache_total = sum(r['cost'] for r in records)
        assert np.isclose(total, cache_total, atol=1e-9)
        audits.append(dict(source=source, billed=total, cached_cost=cache_total, states=dict(states)))
    assert all(np.isfinite(s).all() for s in scores.values())
    assert all(len(c) == 6404 for c in all_costs.values())
    reference = json.loads((ROOT/'runs'/SOURCE/'metrics.json').read_text())['A_hazard']
    scores = {name: scores[name] for name in ['probe pooled', 'probe loso', *methods]}
    assert len({r['episode'] for r in selected}) == 241
    overall, by_scenario = [], []
    for name, s in scores.items():
        assert name.startswith('probe') or np.isfinite(costs[name]).all()
        summary, _, _ = ranking_summary(np.tile(y, (3, 1)), s, rounds, families, seed=20261025,
                                        stratum_key=scenarios)
        mode = 'loso' if name == 'probe loso' else 'pooled'
        key = 'nested' if name.startswith('probe') else name
        ref = reference[mode]['methods'][key]
        assert np.isclose(summary['within_round_auc'], ref['within_round_auc'], atol=1e-12)
        assert np.allclose(summary['within_round_ci95'], ref['within_round_ci95'], atol=1e-12)
        overall.append(dict(method=name, auc=summary['within_round_auc'], ci_low=summary['within_round_ci95'][0],
                            ci_high=summary['within_round_ci95'][1], steps=len(y), positives=int(y.sum()),
                            usd_per_1000=0.0 if name.startswith('probe') else float(costs[name].mean()*1000),
                            matched_billed_usd=0.0 if name.startswith('probe') else float(costs[name].sum()),
                            all_6404_usd_per_1000=0.0 if name.startswith('probe') else float(np.mean(all_costs[name])*1000)))
        for scenario in sorted(set(scenarios)):
            mask = scenarios == scenario
            result, _, _ = ranking_summary(np.tile(y[mask], (3, 1)), s[:, mask], rounds[mask], families[mask], seed=20261025)
            ci = result['within_round_ci95']
            by_scenario.append(dict(method=name, scenario=scenario, steps=int(mask.sum()), positives=int(y[mask].sum()),
                                    episodes=len({selected[i]['episode'] for i in np.flatnonzero(mask)}),
                                    auc=result['within_round_auc'], ci_low=ci[0], ci_high=ci[1],
                                    positive_coverage=result['positive_coverage_by_seed'][0],
                                    valid_bootstrap_reps=result['within_round_valid_bootstrap_reps']))
        print(name, overall[-1], flush=True)
    write_csv(run.dir/'cost_accuracy.csv', overall)
    write_csv(run.dir/'per_scenario.csv', by_scenario)
    (run.dir/'results.json').write_text(json.dumps(dict(overall=overall, per_scenario=by_scenario, cost_audit=audits), indent=2))
    plot(run.dir, overall)
    report(run.dir, overall, by_scenario, audits)
    run.result(steps=len(y), positives=int(y.sum()), episodes=241, matched_methods=len(scores), integrity_checks='passed')
    print(run.dir)


def display(name):
    return name.replace('llm', 'GPT-5-nano').replace('jev', 'Jev').replace('forecaster', 'F').replace('detector', 'D')


def plot(directory, records):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.rc_context({'font.size': 10, 'pdf.fonttype': 42}):
        fig, axes = plt.subplots(1, 2, figsize=(10, 5.5), sharey=True, gridspec_kw={'width_ratios': [1, 3]}, layout='constrained')
        for i, r in enumerate(records):
            probe = r['method'].startswith('probe')
            ax = axes[0 if probe else 1]
            x = i if probe else r['usd_per_1000']
            color = '#222222' if probe else '#0072B2' if r['method'].startswith('jev') else '#A64700'
            marker = ['o', 's', '^', 'v', 'D', 'P', 'X', '*', '<', '>'][i]
            ax.errorbar(x, r['auc'], yerr=[[r['auc']-r['ci_low']], [r['ci_high']-r['auc']]], color=color,
                        marker=marker, capsize=3, linestyle='none', label=display(r['method']))
        axes[0].set(xticks=[0, 1], xticklabels=['Pooled', 'LOSO'], xlim=(-.5, 1.5), xlabel='Probe: approximately $0\nmarginal scoring cost', ylabel='Within scenario × round AUROC')
        axes[1].set(xscale='log', xlabel='Billed USD per 1,000 scored steps (log scale)')
        axes[1].legend(loc='upper center', bbox_to_anchor=(.5, -.15), ncol=4, fontsize=8)
        for ax in axes:
            ax.axhline(.5, color='.6', linestyle='--', linewidth=.8)
            ax.set_ylim(.3, .8)
            ax.grid(axis='y', alpha=.2)
        fig.suptitle('Near-term forbidden-action prediction: accuracy and cost\n4,697 steps; 95% family-bootstrap confidence intervals', fontsize=12)
        fig.savefig(directory/'cost_accuracy.png', dpi=300, facecolor='white')
        fig.savefig(directory/'cost_accuracy.pdf', facecolor='white')
        plt.close(fig)
        from PIL import Image
        with Image.open(directory/'cost_accuracy.png') as image:
            metadata = dict(pixels=list(image.size), dpi=list(image.info['dpi']), mode=image.mode)
        metadata.update(width_inches=10, height_inches=5.5, matplotlib=matplotlib.__version__,
                        source_table='cost_accuracy.csv', x_scale='base-10 log for monitors; categorical zero-cost probe panel',
                        uncertainty='95% percentile family-bootstrap CI; 1000 draws; seed 20261025')
        (directory/'figure_metadata.json').write_text(json.dumps(metadata, indent=2))


def report(directory, overall, per_scenario, audits):
    fmt = lambda r: f"{r['auc']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}]"
    text = ['# Near-term prediction: cost and scenario breakdown', '',
            'This analysis compares activation probes with eight text-monitor setups on 4,697 recruiting steps from 241 episodes (250 positive steps). A positive means a forbidden action occurs in the current or next round; all evaluated steps precede the first action. Farther-away actions and episodes that never act are negative. No models were refitted and no paid calls were made.', '',
            'The nested logistic probe uses training-only layer selection. Pooled predictions use five family-held-out folds; LOSO means leave one scenario out. Probe metrics are computed separately for seeds 42, 43 and 44 and then averaged, not computed on averaged scores. Monitor scores are fixed. D denotes a detector of current rule breaking; F denotes a forecaster of future rule breaking. Jev is typesafe/jev-1.14; GPT-5-nano is openai/gpt-5-nano. Visibility L1 includes target tool calls and posted text; L2 adds peer text; L3 adds unposted target text and tool results.', '',
            'AUROC compares positive and negative steps within the same scenario and round, weighting comparable strata by positive count. Single-class strata cannot contribute. Per-scenario estimates compare within round. Confidence intervals use 1,000 family bootstrap draws (seed 20261025), shared across methods. A family groups related scenario instances so they are resampled together; intervals do not include model-training or price uncertainty. These are descriptive all-data estimates, not a new confirmation test.', '',
            'Jev forecaster L3 has the highest overall point estimate (0.650) at USD 0.112 per 1,000 scored steps. The pooled probe scores 0.586 at approximately zero marginal scoring cost. Across scenarios its point estimates span 0.546–0.609; LOSO spans 0.544–0.644. Jev forecaster L3 spans 0.553–0.701. These ranges describe heterogeneity, not statistically established differences between scenarios.', '',
            '## Accuracy and billed cost', '',
            '| Method | AUROC [95% CI] | USD / 1,000 matched steps |', '|---|---:|---:|']
    text += [f"| {display(r['method'])} | {fmt(r)} | {r['usd_per_1000']:.4f} |" for r in overall]
    text += ['', 'The cost denominator is exactly the 4,697 steps used for accuracy. Provider-reported billed costs include charged parsing retries. Each cached cost was reconciled by request key against the budget ledger; all ledger entries are billed, with no unresolved reservations. The full ledgers include other methods and non-recruiting steps and total ' + ', '.join(f"USD {r['billed']:.6f}" for r in audits) + '. The CSV also provides each method’s mean over all 6,404 cached eligible steps, including control and alone episodes.', '',
             'The probe’s approximately zero marginal cost assumes the target forward pass already exposes the selected last-token activation. Scoring is an affine dot product (the fitted scaling can be folded into its coefficients). It excludes target inference, training, activation transfer and infrastructure integration; hosted APIs that do not expose activations require separate replay. No wall-time or monetary microbenchmark of the dot product was performed.', '',
             'Offline capture was more expensive: `runs/20261025-0339-e02-replay2-results/report.md` reports USD 5.5137 for 6,026 requests, and `runs/20261025-0923-e02-replay3-completion/report.md` reports USD 2.9434 for 3,112 requests. Combined billing snapshots are USD 8.4571 / 9,138 = USD 0.9255 per 1,000 captured requests. Conservative compute-plus-overhead bounds total USD 10.39, or USD 1.1370 per 1,000 captured requests. Billing can lag. These denominators include ineligible requests and 23 shared branching states: this is capture cost per request, not a measured deployment cost per eligible scoring step. Replay saved all 64 layers and included reply-fidelity computation.', '',
             '![Accuracy versus billed cost](cost_accuracy.png)', '',
             'Figure: points are the table estimates and vertical bars are family-bootstrap intervals. A separate zero-cost panel avoids assigning a fabricated positive value to the probe on the logarithmic monitor-cost axis. Both panels share the AUROC scale; the dashed line is 0.5. Colors distinguish model families and marker shapes distinguish methods. This is a general-purpose appendix figure, with no journal-specific formatting claim.', '', '## Per-scenario estimates', '']
    for scenario in sorted({r['scenario'] for r in per_scenario}):
        subset = [r for r in per_scenario if r['scenario']==scenario]
        first = subset[0]
        text += [f"### {scenario}", '', f"{first['steps']} steps; {first['positives']} positives; {first['episodes']} episodes. Comparable-stratum positive coverage: {first['positive_coverage']:.1%}.", '', '| Method | Within-round AUROC [95% CI] |', '|---|---:|']
        text += [f"| {display(r['method'])} | {fmt(r)} |" for r in subset]
        text += ['']
    text += ['## Reproduction and checks', '', f'Run `experiments/E05-probes/.venv/bin/python experiments/E06-monitors/cost_and_scenarios.py` from the repository root. Input probe scores: `runs/{SOURCE}/probe_scores.csv`. Labels and row metadata: `runs/{DATA}/rows.jsonl`. Monitor scores and budget ledgers: ' + ', '.join(f'`runs/{x}`' for x in MONITORS) + '.', '',
             'All rows were matched by step ID and request hash, with exact label checks and one prediction per method, seed and step. All ten overall estimates and confidence intervals reproduce the all-data metrics to numerical tolerance. Each common monitor covers 6,404 eligible rows; the matched subset has no missing scores or costs. See `results.json` for cost reconciliation, `cost_accuracy.csv` and `per_scenario.csv` for plot-ready data, and `cost_accuracy.pdf` for the vector figure. Small scenario samples can produce wide intervals; ranking methods from overlapping intervals is not a paired significance test.']
    (directory/'report.md').write_text('\n'.join(text)+'\n')


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        main()
