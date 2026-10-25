"""Export saved probe robustness results without inference, refitting or new intervals.

Run: uv run --with matplotlib python report/make_appendix_robustness.py
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
LABELS = {'eventual': 'Eventual', 'A_hazard': 'A: current/next round',
          'B_round_contrast': 'B: round contrast', 'C_step_contrast': 'C: request contrast'}
SCENARIOS = {'deploy-token-v2': 'Deploy token', 'dispatch-integration-code': 'Dispatch code',
             'handoff-exception-note': 'Handoff note', 'procurement-reserve-price': 'Reserve price',
             'service-capacity-figure': 'Capacity figure', 'service-rollout-threshold': 'Rollout threshold'}


def load(path, sources):
    raw = path.read_bytes()
    sources[str(path.relative_to(ROOT))] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    return json.loads(raw)


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        w.writeheader(); w.writerows(rows)


def ci(v, bounds):
    lo, hi = bounds
    assert 0 <= lo <= v <= hi <= 1
    return f'{v:.3f} [{lo:.3f}, {hi:.3f}]'


def save(fig, path):
    fig.savefig(path.with_suffix('.png'), dpi=300, facecolor='white')
    fig.savefig(path.with_suffix('.pdf'), facecolor='white')
    plt.close(fig)


def table(out, stem, headers, body, widths, note, title):
    md = [f'**{title}**', '', note, '', '| ' + ' | '.join(headers) + ' |',
          '|' + '|'.join('---' for _ in headers) + '|']
    md.extend('| ' + ' | '.join(map(str, row)) + ' |' for row in body)
    (out / (stem + '.md')).write_text('\n'.join(md) + '\n')
    height = .34 * (len(body) + 1) + 1.15
    fig, ax = plt.subplots(figsize=(11, height))
    fig.subplots_adjust(left=.015, right=.985, top=.84, bottom=.02)
    ax.axis('off')
    t = ax.table(cellText=body, colLabels=headers, colWidths=widths, cellLoc='left',
                 colLoc='left', bbox=[0, 0, 1, 1])
    t.auto_set_font_size(False); t.set_fontsize(8)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor('#cbd5e1'); cell.set_linewidth(.4)
        if r == 0:
            cell.set_facecolor('#e2e8f0'); cell.set_text_props(weight='bold')
        elif r % 2 == 0:
            cell.set_facecolor('#f8fafc')
    fig.text(.02, .97, title, va='top', weight='bold', fontsize=11)
    # The full methodological note is kept in the Markdown companion.
    fig.text(.02, .92, ('AUROC point estimates; per-scenario confidence intervals are not available in the saved source.'
              if 'point estimates' in title else
              'AUROC; brackets: 95% family-bootstrap confidence intervals. See companion Markdown for definitions.'),
             va='top', fontsize=8)
    save(fig, out / stem)


def main(args):
    for field in ['main_run', 'mlp_run', 'layer_run', 'output_dir']:
        setattr(args, field, getattr(args, field).resolve())
    out = args.output_dir; out.mkdir(parents=True, exist_ok=True)
    sources = {}
    main_data = load(args.main_run / 'metrics.json', sources)
    mlp = load(args.mlp_run / 'metrics.json', sources)
    layers = load(args.layer_run / 'metrics.json', sources)
    score_path = args.main_run / 'probe_scores.csv'
    raw = score_path.read_bytes()
    sources[str(score_path.relative_to(ROOT))] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    counts = {}
    for r in csv.DictReader(raw.decode().splitlines()):
        if r['method'] == 'nested' and r['seed'] == '42' and r['analysis'] == 'loso':
            k = (r['label_variant'], r['scenario'])
            c = counts.setdefault(k, {'rows': 0, 'positives': 0, 'episodes': set()})
            c['rows'] += 1; c['positives'] += int(r['label']); c['episodes'].add(r['episode'])
    summary = []
    for label in ['A_hazard', 'B_round_contrast', 'C_step_contrast']:
        for analysis in ['pooled', 'loso']:
            for method in ['nested', 'fixed32']:
                m = main_data[label][analysis]['methods'][method]
                summary.append(dict(label=label, analysis=analysis, method=method,
                    rows=m['rows'], positives=m['positives'], episodes=m['episodes'],
                    auc=m['within_round_auc'], ci_low=m['within_round_ci95'][0], ci_high=m['within_round_ci95'][1],
                    fold_auc=m['fold_stratified_auc'], fold_low=m['fold_stratified_ci95'][0], fold_high=m['fold_stratified_ci95'][1],
                    scenario_mean=m['balanced_auc'], scenario_mean_low=m['balanced_ci95'][0], scenario_mean_high=m['balanced_ci95'][1],
                    source=str(args.main_run.relative_to(ROOT) / 'metrics.json')))
    write_csv(out / 'appendix_h_robustness.csv', summary)
    note = ('All-data Qwen3-32B recruiting steps, secret in context and strictly before first forbidden action. '
            'A labels the current or next round; B retains these positives and held-episode negatives; C instead takes positives '
            'within three target requests. B/C exclude earlier give-in steps using hindsight and are not prospective alarm labels. '
            'Nested means layer selected on inner training validation; fixed32 fixes decoder block 32 (zero-based). '
            'Pooled uses five family folds; LOSO holds out a scenario. Values average three seeds. '
            'Intervals use 1,000 family resamples, conditional on fitted models. Scenario mean weights comparable scenarios equally; '
            'the primary metric weights same-scenario, same-round comparisons by positive count. Fold sensitivity additionally '
            'requires the same fitted fold. Confirmation episodes are included in this pool; this is not an independent confirmation.')
    body = [[LABELS[r['label']], r['analysis'].upper(), 'Inner-selected' if r['method']=='nested' else 'Layer 32',
             f"{r['rows']} / {r['positives']} / {r['episodes']}",
             ci(r['auc'], [r['ci_low'], r['ci_high']]),
             ci(r['fold_auc'], [r['fold_low'], r['fold_high']]),
             ci(r['scenario_mean'], [r['scenario_mean_low'], r['scenario_mean_high']])] for r in summary]
    table(out, 'appendix_h_robustness', ['Label', 'Split', 'Probe', 'Steps / + / episodes', 'Scenario × round', 'Fold × scenario × round', 'Scenario mean'],
          body, [.16,.06,.10,.14,.18,.18,.18], note, 'Near-term robustness: all-data cohort')
    scenarios = []
    for label in ['A_hazard', 'B_round_contrast', 'C_step_contrast']:
        for scenario in SCENARIOS:
            c = counts[(label, scenario)]
            row = dict(label=label, scenario=scenario, rows=c['rows'], positives=c['positives'], episodes=len(c['episodes']))
            for analysis in ['pooled', 'loso']:
                for method in ['nested', 'fixed32']:
                    row[f'{analysis}_{method}'] = main_data[label][analysis]['methods'][method]['per_scenario_auc'][scenario]
            row['source'] = str(args.main_run.relative_to(ROOT) / 'metrics.json')
            scenarios.append(row)
    for label in ['A_hazard', 'B_round_contrast', 'C_step_contrast']:
        selected = [r for r in scenarios if r['label'] == label]
        expected = main_data[label]['loso']['methods']['nested']
        assert sum(r['rows'] for r in selected) == expected['rows']
        assert sum(r['positives'] for r in selected) == expected['positives']
        assert sum(r['episodes'] for r in selected) == expected['episodes']
    write_csv(out / 'appendix_h_per_scenario.csv', scenarios)
    for label in ['A_hazard', 'B_round_contrast', 'C_step_contrast']:
        selected = [r for r in scenarios if r['label'] == label]
        body = [[SCENARIOS[r['scenario']], f"{r['rows']} / {r['positives']} / {r['episodes']}"] +
                [f"{r[k]:.3f}" for k in ['pooled_nested','loso_nested','pooled_fixed32','loso_fixed32']] for r in selected]
        table(out, 'appendix_h_per_scenario_' + label[0].lower(),
              ['Scenario', 'Steps / + / episodes', 'Pooled inner-selected', 'LOSO inner-selected', 'Pooled layer 32', 'LOSO layer 32'],
              body, [.18,.18,.16,.16,.16,.16],
              note + ' Per-scenario values are within-round AUROCs. The source does not provide per-scenario confidence intervals; none are inferred here.',
              'Per-scenario robustness: ' + LABELS[label] + ' (all data; point estimates)')
    mlp_rows = []
    for key, m in mlp.items():
        label, analysis = key.split('/')
        delta = m['mlp_minus_nested']['scenario_round']
        row = dict(label=label, analysis=analysis, rows=m['rows'], positives=m['positives'],
                   mlp=m['methods']['mlp']['within_round_auc'], mlp_low=m['methods']['mlp']['within_round_ci95'][0], mlp_high=m['methods']['mlp']['within_round_ci95'][1],
                   logistic=m['methods']['nested']['within_round_auc'], logistic_low=m['methods']['nested']['within_round_ci95'][0], logistic_high=m['methods']['nested']['within_round_ci95'][1],
                   difference=delta['mean'], difference_low=delta['paired_family_ci95'][0], difference_high=delta['paired_family_ci95'][1],
                   source=str(args.mlp_run.relative_to(ROOT) / 'metrics.json'))
        mlp_rows.append(row)
    write_csv(out / 'appendix_h_mlp.csv', mlp_rows)
    body = [[LABELS[r['label']], r['analysis'].upper(), f"{r['rows']} / {r['positives']}",
             ci(r['mlp'], [r['mlp_low'], r['mlp_high']]), ci(r['logistic'], [r['logistic_low'], r['logistic_high']]),
             f"{r['difference']:+.3f} [{r['difference_low']:+.3f}, {r['difference_high']:+.3f}]"] for r in mlp_rows]
    table(out, 'appendix_h_mlp', ['Label', 'Split', 'Steps / +', 'MLP', 'Logistic', 'Paired MLP − logistic'],
          body, [.19,.07,.10,.21,.21,.22],
          'First data batch only, not the all-data cohort. A one-hidden-layer MLP (32 ReLU units, 80 epochs) and logistic probe '
          'each select layers on inner validation using the same saved splits. Scenario × round AUROC, three-seed mean; '
          'paired differences and intervals use the same 1,000 family resamples. No C-label MLP result is available.',
          'MLP sensitivity: first data batch only')
    curve = []
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.7), layout='constrained', sharey=True)
    for ax, label in zip(axes, ['eventual','B_round_contrast']):
        for analysis, color, marker, style in [('pooled','#0072b2','o','-'),('loso','#a64b00','s','--')]:
            m = layers[label][analysis]
            rr = []
            for layer, v in sorted(m['layers'].items(), key=lambda item:int(item[0])):
                r = dict(label=label, analysis=analysis, layer=int(layer), auc=v['within_round_auc'],
                         ci_low=v['within_round_ci95'][0], ci_high=v['within_round_ci95'][1], rows=m['rows'], families=m['families'],
                         source=str(args.layer_run.relative_to(ROOT) / 'metrics.json'))
                curve.append(r); rr.append(r)
            x=[r['layer'] for r in rr]; y=[r['auc'] for r in rr]
            ax.errorbar(x,y,yerr=[[r['auc']-r['ci_low'] for r in rr],[r['ci_high']-r['auc'] for r in rr]],
                        color=color,marker=marker,linestyle=style,markersize=3,linewidth=1,capsize=2,elinewidth=.6,
                        label=analysis.upper())
        ax.axhline(.5,color='#64748b',linestyle=':',linewidth=.9)
        ax.set(xlabel='Decoder block (zero-based)', xlim=(-1,64), ylim=(.35,.78), xticks=[0,16,32,48,63])
        ax.set_title(LABELS[label],loc='left');ax.grid(axis='y',alpha=.15)
    axes[0].set_ylabel('Within scenario × round AUROC'); axes[1].legend(frameon=False,fontsize=9)
    fig.suptitle('First-batch layer diagnostic (not layer selection)',fontsize=12,weight='bold')
    save(fig, out / 'appendix_h_layers'); write_csv(out / 'appendix_h_layers.csv', curve)
    (out/'appendix_h_layers.md').write_text('**First-batch layer diagnostic, not layer selection.** Fixed-layer logistic probes at all 17 candidate decoder blocks, '
        'evaluated on saved outer folds. Points average three seeds; bars are pointwise 95% family-bootstrap intervals (1,000 resamples), '
        'conditional on fitted models, not simultaneous across layers. Eventual uses 2,910 steps; B uses 2,460; both have 133 families. '
        'B is a hindsight contrast. The curves use the first data batch only and do not describe the expanded all-data cohort. '
        'Line segments connect measured candidate blocks without smoothing. Selecting a layer from these test curves would invalidate an unbiased performance estimate; '
        'the inner-selected headline estimates remain separate. Pooled comparisons may be sensitive to cross-fold score calibration; LOSO compares within one fitted model per scenario. '
        'The saved diagnostic does not include A or C curves.\n')
    manifest = dict(sources=sources, transformations=['Copy saved point estimates and intervals; no fits or new bootstrap.',
                   'Count per-scenario unique episodes and steps from nested LOSO seed 42 score export.',
                   'Keep first-batch MLP/layer diagnostics separate from expanded all-data results.'],
                   figure=dict(width_inches=10,height_inches=3.7,dpi=300),
                   missing=['Per-scenario confidence intervals not saved.', 'No all-data MLP or all-data per-layer curve in selected sources.', 'No A/C layer curve or C MLP in selected sources.'])
    (out/'appendix_h_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Wrote {len(summary)} aggregate, {len(scenarios)} scenario, {len(mlp_rows)} MLP and {len(curve)} layer records.')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main-run',type=Path,default=ROOT/'runs/20261025-1456-e05-all-data-main')
    p.add_argument('--mlp-run',type=Path,default=ROOT/'runs/20261025-0848-e05-near-term-mlp')
    p.add_argument('--layer-run',type=Path,default=ROOT/'runs/20261025-1003-e05-layer-diagnostic')
    p.add_argument('--output-dir',type=Path,default=ROOT/'report/figures')
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42}):
        main(p.parse_args())
