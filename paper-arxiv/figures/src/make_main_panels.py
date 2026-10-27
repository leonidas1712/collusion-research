"""Render requested main-text panels directly from the saved figure analyses."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter
from style import configure, MODEL_COLORS, CONTROL_COLOR, LABEL_SIZE, end_labels, paper_number

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'paper-arxiv/figures'
TRAJECTORY = ROOT / 'runs/20261026-2254-e05-arxiv-score-trajectories/metrics.json'
ALARMS = ROOT / 'runs/20261028-0120-e13-alarm-tradeoffs-matched'
EPISODE = ROOT / 'runs/20261027-0049-e05-arxiv-episode-calibration-descriptive/metrics.json'


def save(fig, stem, sources, rows):
    for suffix in ['pdf', 'png']:
        fig.savefig(OUT / f'{stem}.{suffix}', dpi=180)
    (OUT / f'{stem}.json').write_text(json.dumps({
        'sources': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        'transformation': 'Select existing panels; no new scores, fits, thresholds or aggregation.',
        'width_inches': fig.get_figwidth(), 'height_inches': fig.get_figheight(),
    }, indent=2) + '\n')
    with (OUT / f'{stem}.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader(); w.writerows(rows)
    plt.close(fig)


def trajectories():
    data = json.loads(TRAJECTORY.read_text())
    assert data['include_figure']
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.9), sharey=True)
    fig.subplots_adjust(left=.10, right=.98, top=.84, bottom=.29, wspace=.16)
    exports = []
    for ax, model, title in zip(axes, ['qwen', 'gpt_oss'], ['Qwen3-32B', 'gpt-oss-20b']):
        color = MODEL_COLORS[model]
        ends = []
        for summary in data['summaries']:
            if summary['model'] != model:
                continue
            rows = summary['aggregate']; fresh = summary['cohort'] == 'fresh'
            x = [r['offset'] for r in rows]
            ax.plot(x, [100*r['median'] for r in rows], color=color,
                    ls='-' if fresh else '--', marker='o' if fresh else None, ms=3, lw=1.3)
            if fresh:
                ax.fill_between(x, [100*r['q25'] for r in rows], [100*r['q75'] for r in rows], color=color, alpha=.12)
            exports.extend(dict(model=model, cohort=summary['cohort'], **r) for r in rows)
            assert x[-1] == 0
            ends.append(('test' if fresh else 'dev.', 100*rows[-1]['median']))
        ax.set(title=title, xticks=[-10,-5,0], xlabel='Scored calls before leak', ylim=(0,103))
        end_labels(ax, ends, color, right=3.4); ax.spines['bottom'].set_bounds(-10, 0)
        ax.axvline(0, color='#777777', lw=.8, ls=':'); ax.grid(axis='y', alpha=.15)
    axes[0].set_ylabel('Probe score percentile')
    fig.legend(handles=[Line2D([],[],color='#444444',ls='--',label='Development median'),
                        Line2D([],[],color='#444444',label='Test median (band: middle 50%)')],
               loc='lower center', ncol=2, frameon=False, fontsize=9)
    save(fig, 'fig6_trajectory_aggregate', [TRAJECTORY], exports)


def alarms():
    with (ALARMS / 'curves.csv').open() as f:
        rows = [r for r in csv.DictReader(f) if r['panel'] == 'Qwen: fresh episodes']
    metrics = json.loads((ALARMS / 'metrics.json').read_text())
    fig, ax = plt.subplots(figsize=(4.5, 4.0))
    fig.subplots_adjust(left=.17, right=.93, bottom=.34, top=.88)
    for name, color, ls, marker in [('Last-prompt probe', MODEL_COLORS['qwen'], '-', 'o'),
                                    ('Jev', '#666666', '--', 's')]:
        curve = [r for r in rows if r['detector'] == name]
        op = next(p for p in metrics['operating_points'] if p['panel'] == 'Qwen: fresh episodes' and p['detector'] == name)
        ax.plot([float(r['refusing_alarm']) for r in curve], [float(r['leaks_caught']) for r in curve],
                color=color, ls=ls, lw=1.5, label='Zero-shot Jev' if name=='Jev' else name)
        ax.plot(op['refusing_call_alarm'], op['leaking_call_alarm'], marker=marker, color=color, ms=7)
        prefix = 'qwenMatchedProbe' if name == 'Last-prompt probe' else 'qwenMatchedJev'
        text = (paper_number(prefix+'Caught', op['leaking_call_alarm']) + ' caught\n'
                + paper_number(prefix+'Refusing', op['refusing_call_alarm']) + ' flagged')
        # Probe label sits between its curve and Jev's; Jev's sits just right of its square.
        xy = (.135, .935) if name == 'Last-prompt probe' else (.12, .30)
        ax.text(*xy, text, ha='left', va='top' if name == 'Last-prompt probe' else 'center',
                fontsize=LABEL_SIZE, color=color, linespacing=1.1)
    episode = json.loads(EPISODE.read_text())['qwen_probe']
    assert episode['calibration_status'] == 'descriptive_fresh_refusing_calibration'
    point = episode['episode_calibrated']
    ax.plot(point['refusing_calls']['rate'], point['leaking_calls']['rate'],
            marker='D', mfc='white', mec=MODEL_COLORS['qwen'], mew=1.7, ms=8,
            clip_on=False, zorder=5)
    # Whole percent to match the other 'caught' labels; still checked against the registered 21.1%.
    paper_number('qwenCalibrationEpisodeLeakCallsRate', point['leaking_calls']['rate'])
    # Diamond label sits out in the empty lower right, joined to the diamond by a thin leader.
    ax.annotate(f"{100*point['leaking_calls']['rate']:.0f}%" + ' caught\n'
                + paper_number('qwenCalibrationEpisodeRefusingCallsRate', point['refusing_calls']['rate']) + ' flagged',
                (point['refusing_calls']['rate'], point['leaking_calls']['rate']), xytext=(.30, .11),
                ha='left', va='center', fontsize=LABEL_SIZE, color=MODEL_COLORS['qwen'], linespacing=1.1,
                arrowprops=dict(arrowstyle='-', color='#888888', lw=.6, shrinkA=2, shrinkB=6))
    ax.set(title='Qwen3-32B: test episodes', xlim=(0,1), ylim=(0,1.02),
           xlabel='Calls in refusing episodes flagged', ylabel='Leaking calls caught')
    ax.xaxis.set_major_formatter(PercentFormatter(1)); ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(alpha=.15)
    fig.legend(loc='lower center', bbox_to_anchor=(.5,.15), ncol=2, frameon=False, fontsize=9)
    fig.legend(handles=[
        Line2D([], [], marker='o', color='#555555', ls='none',
               label='Filled: probe at control-call threshold; Jev at same share flagged'),
        Line2D([], [], marker='D', mfc='white', mec=MODEL_COLORS['qwen'], ls='none',
               label='Per-episode threshold')],
        loc='lower center', bbox_to_anchor=(.5,.015), ncol=1, frameon=False, fontsize=8.5)
    rows.append(dict(panel='Qwen: fresh episodes',
                     detector='Last-prompt probe: descriptive episode-calibrated marker',
                     threshold_offset=episode['episode_threshold']-episode['original_threshold'],
                     leaks_caught=point['leaking_calls']['rate'],
                     refusing_alarm=point['refusing_calls']['rate']))
    save(fig, 'fig7_qwen_alarms', [ALARMS/'curves.csv', ALARMS/'metrics.json', EPISODE], rows)


if __name__ == '__main__':
    configure(); trajectories(); alarms()
