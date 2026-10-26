"""Draft Figure 3 from saved estimates, without fits or manuscript changes.

Run: uv run --with matplotlib python report/figures/make_figure3_streaming.py
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
STREAM = ROOT / 'runs/20261026-0526-e05-reasoning-stream'
INCOMING = ROOT / 'runs/20261026-1128-e05-stream-layer18-loso'
PROMPT = ROOT / 'runs/20261026-0138-e05-gpt-oss-main'
STYLE = {'activation': ('#087f8c', 'o'), 'text/rule': ('#334155', 's'),
         'control': ('#64748b', 'D'), 'last-prompt': ('#334155', 'D')}


def collect():
    rows = []
    def read(path):
        raw = path.read_bytes()
        return json.loads(raw), str(path.relative_to(ROOT)), hashlib.sha256(raw).hexdigest()

    def add(panel, label, group, data, path, digest, key, note='', seeds=3):
        value = data.get('within_round_auc', data.get('within_auc'))
        low, high = data.get('within_round_ci95', data.get('ci95'))
        assert 0 <= low <= value <= high <= 1
        rows.append(dict(panel=panel, label=label, group=group, estimate=value,
                         low=low, high=high, rows=data['rows'], positives=data['positives'],
                         episodes=data.get('episodes', 238), seeds=seeds,
                         source=path, source_sha256=digest, source_key=key, note=note))
    m, path, digest = read(STREAM / 'metrics.json')
    for label, key, group, note in [
        ('Before value mention', 'immediate/censored/loso/extended/token_max', 'activation', 'Reasoning-token probe; stricter censoring sensitivity'),
        ('Reasoning-token probe', 'immediate/all/loso/extended/token_max', 'activation', 'This-reply any-publication label'),
        ('Pre-ask placebo†', 'immediate/all/loso/pre_ask_placebo/token_max', 'control', 'Different label: eventual episode outcome; pre-ask steps'),
    ]:
        add('a', label, group, m[key], path, digest, key, note)
    for label, key in [
        ('Reasoning: paper cohort', 'round/all/loso/frozen/token_max'),
        ('Reasoning: extended', 'round/all/loso/extended/token_max'),
        ('Reasoning: this reply', 'immediate/all/loso/extended/token_max'),
    ]:
        add('b', label, 'activation', m[key], path, digest, key)
    for filename, methods in [
        ('comparison-jev-1-14.json', [('Jev 1.14 sampled-prefix MAX', 'Jev on reasoning'),
                                   ('Broad keyword MAX', 'Keywords'),
                                   ('Reversed final length (retrospective)', 'Length (hindsight)')]),
        ('comparison-gpt-5-nano.json', [('GPT-5-nano sampled-prefix MAX', 'GPT-5-nano on reasoning')]),
    ]:
        comp, path, digest = read(STREAM / filename)
        assert comp['exact_row_and_hash_match']
        for method, label in methods:
            matches = [r for r in comp['records'] if r['method'] == method and r['cut'] == 'all' and r['split'] == 'loso']
            assert len(matches) == 1
            add('a', label, 'text/rule', matches[0], path, digest,
                f'records:method={method};cut=all;split=loso',
                'Fixed score on matched replies; length uses final length retrospectively' if label.startswith('Length') else 'Fixed text/rule score on matched replies', seeds=0)
    inc, path, digest = read(INCOMING / 'metrics.json')
    add('a', 'Incoming-message probe*', 'activation', inc['incoming/probe'], path, digest,
        'incoming/probe', 'Seed 42; incoming peer messages and tool results; expanded capture', seeds=1)
    gp, path, digest = read(PROMPT / 'metrics.json')
    for variant, label in [('eventual', 'Last prompt: eventual'), ('A_hazard', 'Last prompt: near-term')]:
        matches = [r for r in gp if r['window'] == 'post_ask' and r['variant'] == variant
                   and r['mode'] == 'loso' and r['method'] == 'nested' and r['sensitivity'] == 'primary']
        assert len(matches) == 1
        add('b', label, 'last-prompt', matches[0], path, digest,
            f'window=post_ask;variant={variant};mode=loso;method=nested;sensitivity=primary')
    return rows


CAPTION = """Draft Figure 3. Reading reasoning recognises the leaking reply more strongly than last-prompt prediction anticipates a later leak. (a) Within scenario × round AUROC; whiskers are saved 95% family-bootstrap confidence intervals. Activation rows are held-out-scenario estimates; fixed text/rule scores are evaluated on the same replies as the reasoning probe. Rows are sorted within groups. The reasoning and text/rule comparison uses 1,995 replies, 121 positives, from 238 episodes. *Incoming-message capture includes peer messages and tool results, uses seed 42 only, and covers 2,199 replies / 143 positives. †The pre-ask placebo instead predicts eventual episode outcome on 628 steps / 388 positives. Length is reversed final reasoning length, a hindsight comparator, not an online alarm. (b) The label ladder is descriptive, not a paired comparison or an isolated effect of label proximity: the input and eligible cohort change. Last-prompt eventual and near-term estimates use 2,059 steps (169 and 148 positives); near-term reasoning uses 1,874 replies / 118 positives in the paper cohort and 1,995 / 199 in the extended cohort. This-reply reasoning uses the panel-a cohort. All cohorts cover 238 episodes. Near-term means this or the next round. Points are deliberately unconnected. Exploratory results; no new fits. Numeric values and exact source keys are in figure3_streaming.csv.
"""


def render(rows, output):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7,
                         'pdf.fonttype': 42, 'ps.fonttype': 42,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.labelcolor': '#334155', 'text.color': '#334155'})
    fig = plt.figure(figsize=(6.5, 2.6), facecolor='white')
    left = fig.add_axes([.265, .22, .255, .59])
    right = fig.add_axes([.645, .22, .33, .59])
    a = sorted([r for r in rows if r['panel'] == 'a'],
               key=lambda r: (['activation', 'text/rule', 'control'].index(r['group']), -r['estimate']))
    ys = [8, 7, 6, 4.7, 3.7, 2.7, 1.7, .3]
    for r, y in zip(a, ys):
        color, marker = STYLE[r['group']]
        left.errorbar(r['estimate'], y, xerr=[[r['estimate']-r['low']], [r['high']-r['estimate']]],
                      fmt=marker, color=color, ecolor=color, markersize=3.5, capsize=2, linewidth=.8)
        left.text(1.015, y, f"{r['estimate']:.3f}", ha='left', va='center', fontsize=6.3)
    left.set_yticks(ys, [r['label'] for r in a], fontsize=6.5)
    left.tick_params(axis='y', length=0, pad=4)
    left.set(xlim=(.25, 1), ylim=(-.5, 8.7), xlabel='AUROC (95% CI)')
    left.set_xticks([.3, .5, .7, .9])
    left.spines['left'].set_visible(False)
    for y in [5.35, .95]:
        left.axhline(y, color='#CBD5E1', linewidth=.6)
    left.axvline(.5, color='#64748b', linestyle='--', linewidth=.8, zorder=0)
    left.grid(axis='x', alpha=.15)
    fig.text(.015, .955, '(a) Recognising the leaking reply', weight='bold', fontsize=8)
    fig.text(.015, .885, 'gpt-oss-20b · held-out scenarios', fontsize=7)
    fig.text(.615, .955, '(b) From later outcome to this reply', weight='bold', fontsize=8)
    fig.text(.645, .885, 'Different labels and cohorts; no paired contrast', fontsize=6.2)
    positions = {'Last prompt: eventual': 0, 'Last prompt: near-term': .84,
                 'Reasoning: paper cohort': 1.02, 'Reasoning: extended': 1.20,
                 'Reasoning: this reply': 2}
    for r in [r for r in rows if r['panel'] == 'b']:
        x = positions[r['label']]
        color, marker = STYLE[r['group']]
        if r['label'] == 'Reasoning: extended': marker = '^'
        right.errorbar(x, r['estimate'], yerr=[[r['estimate']-r['low']], [r['high']-r['estimate']]],
                       fmt=marker, color=color, markersize=4, capsize=2, linewidth=.8)
        if r['label'] == 'Last prompt: near-term':
            xytext=(-9, -14)
        elif r['label'] == 'Reasoning: paper cohort':
            xytext=(-15, 8)
        elif r['label'] == 'Reasoning: extended':
            xytext=(13, 11)
        else: xytext=(0, 9)
        right.annotate(f"{r['estimate']:.3f}", (x, r['estimate']), xytext=xytext,
                       textcoords='offset points', ha='center', fontsize=6.2, color=color)
    right.set(xlim=(-.25, 2.3), ylim=(.4, 1.03), ylabel='AUROC (95% CI)')
    right.set_xticks([0, 1, 2], ['Eventual', 'This / next\nround', 'This reply'], fontsize=6.5)
    right.set_yticks([.5, .7, .9])
    right.axhline(.5, color='#64748b', linestyle='--', linewidth=.8, zorder=0)
    right.grid(axis='y', alpha=.15)
    handles = [Line2D([], [], marker='o', color='#087f8c', linestyle='', label='Reasoning'),
               Line2D([], [], marker='^', color='#087f8c', linestyle='', label='Extended cohort'),
               Line2D([], [], marker='D', color='#334155', linestyle='', label='Last prompt')]
    right.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, -.38), ncol=3,
                 frameon=False, fontsize=5.8, handletextpad=.2, columnspacing=.6, markerscale=.8)
    fig.text(.015, .075, '* Incoming: seed 42, expanded capture.  † Placebo: eventual label.', fontsize=6)
    fig.text(.015, .025, 'Groups: teal circles = activations; slate squares = text/rules; grey diamond = control.', fontsize=5.8)
    for ext in ['png', 'pdf']:
        fig.savefig(output / f'figure3_streaming.{ext}', dpi=300, facecolor='white')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'report/figures')
    parser.add_argument('--input-csv', type=Path, help='Re-render the saved figure CSV without the run folders')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.input_csv:
        with args.input_csv.open(newline='') as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            for key in ['estimate', 'low', 'high']:
                row[key] = float(row[key])
            for key in ['rows', 'positives', 'episodes', 'seeds']:
                row[key] = int(row[key])
    else:
        rows = collect()
    with (args.output_dir / 'figure3_streaming.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / 'figure3_streaming_caption.md').write_text(CAPTION)
    render(rows, args.output_dir)
    print(f'{len(rows)} saved estimates; figure size 6.5 × 2.6 inches (468 × 187.2 pt).')


if __name__ == '__main__':
    main()
