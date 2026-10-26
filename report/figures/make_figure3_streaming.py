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


CAPTION = """Figure 3. Exploratory, gpt-oss-20b. A linear probe on the target's reasoning tokens recognises the reply that leaks the protected value; text and rule baselines reading the same material do not. (a) Within scenario × round AUROC on held-out scenarios; whiskers are 95% family-bootstrap confidence intervals. Label: this reply makes the first public emission of the value, by any route. The reasoning probe and all baselines are scored on the same 1,995 replies with reasoning (121 leaking) from 238 episodes. "…cut before value mention" drops every reasoning token from the first exact mention of the value onward. Reasoning length uses the final length of the reasoning (reversed), so it is a hindsight comparator, not an online alarm. *A probe on the incoming peer message and tool results alone, trained on the same label (seed 42 only; 2,199 replies, 143 leaking): much of the signal is present before the target reasons. †The post-ask probe applied to pre-ask replies against the eventual episode outcome (628 replies, 388 positives). (b) AUROC as the label moves closer to the leak. This ladder is descriptive, not a paired comparison: both the input and the reply set change between points, so it does not isolate an effect of label proximity. Last-prompt probe: 2,059 post-ask replies (169 positives for eventual, 148 for this or next round). Reasoning (paper replies): the paper's reply cohort; 1,874 replies, 118 positives. Reasoning (+ leaking replies): the panel-a reply set, which adds each episode's first leaking reply; 1,995 replies, 199 positives for this or next round and 121 for this reply. All cohorts cover 238 episodes. Values and exact source keys are in figure3_streaming.csv.
"""


DISPLAY_A = {  # CSV label -> (display label, panel-a row position, top to bottom)
    'Reasoning-token probe': ('Reasoning-token probe', 9.0),
    'Before value mention': ('…cut before value mention', 8.1),
    'Incoming-message probe*': ('Incoming message only*', 7.2),
    'Length (hindsight)': ('Reasoning length (hindsight)', 5.3),
    'Jev on reasoning': ('Jev judge on reasoning', 4.4),
    'Keywords': ('Keyword rule', 3.5),
    'GPT-5-nano on reasoning': ('GPT-5-nano on reasoning', 2.6),
    'Pre-ask placebo†': ('Pre-ask placebo†', .7),
}
GROUP_HEADINGS = [(9.75, 'Linear probes on activations', '#087f8c'),
                  (6.05, 'Text and rule baselines', '#334155'),
                  (1.45, 'Control', '#64748b')]
# Panel b: x position, marker. Triangles share panel a's reply set (paper replies + first leaking reply).
POS_B = {'Last prompt: eventual': (0, 'D'), 'Last prompt: near-term': (.84, 'D'),
         'Reasoning: paper cohort': (1.02, 'o'), 'Reasoning: extended': (1.20, '^'),
         'Reasoning: this reply': (2, '^')}
TEAL, SLATE, GREY = '#087f8c', '#334155', '#64748b'


def render(rows, output):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7,
                         'pdf.fonttype': 42, 'ps.fonttype': 42,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.labelcolor': SLATE, 'text.color': SLATE,
                         'xtick.color': SLATE, 'ytick.color': SLATE,
                         'xtick.labelsize': 7, 'ytick.labelsize': 7})
    W, H = 6.5, 2.85
    fig = plt.figure(figsize=(W, H), facecolor='white')
    left = fig.add_axes([.255, .25, .27, .60])
    right = fig.add_axes([.66, .25, .32, .60])

    # (a) recognising the leaking reply
    for r in (r for r in rows if r['panel'] == 'a'):
        label, y = DISPLAY_A[r['label']]
        color, marker = STYLE[r['group']]
        head = r['label'] == 'Reasoning-token probe'
        left.errorbar(r['estimate'], y, xerr=[[r['estimate']-r['low']], [r['high']-r['estimate']]],
                      fmt=marker, color=color, ecolor=color, markersize=4.5 if head else 3.8,
                      capsize=1.8, linewidth=.9, zorder=3)
        left.text(1.012, y, f"{r['estimate']:.2f}", ha='left', va='center', fontsize=6.8,
                  color=color if r['group'] != 'control' else GREY, weight='bold' if head else 'normal')
        left.text(-.03, y, label, transform=left.get_yaxis_transform(), ha='right', va='center',
                  fontsize=7, weight='bold' if head else 'normal')
    for y, text, color in GROUP_HEADINGS:
        left.text(-.03, y, text, transform=left.get_yaxis_transform(), ha='right', va='center',
                  fontsize=6.2, style='italic', color=color)
    left.set_yticks([])
    left.set(xlim=(.25, 1), ylim=(.1, 10.2))
    left.set_xlabel('AUROC on held-out scenarios (95% CI)', fontsize=7, labelpad=2)
    left.set_xticks([.3, .5, .7, .9])
    left.spines['left'].set_visible(False)
    for y in [6.6, 1.95]:
        left.axhline(y, xmin=-.9, color='#CBD5E1', linewidth=.6, clip_on=False)
    left.axvline(.5, color=GREY, linestyle='--', linewidth=.8, zorder=0)
    left.text(.5, 10.2, 'chance', ha='center', va='bottom', fontsize=6, color=GREY)
    left.grid(axis='x', alpha=.15)
    fig.text(.012, .955, '(a) Recognising the reply that leaks (gpt-oss-20b)', weight='bold', fontsize=8)

    # (b) label ladder
    for r in (r for r in rows if r['panel'] == 'b'):
        x, marker = POS_B[r['label']]
        color, _ = STYLE[r['group']]
        right.errorbar(x, r['estimate'], yerr=[[r['estimate']-r['low']], [r['high']-r['estimate']]],
                       fmt=marker, color=color, markersize=4.2, capsize=1.8, linewidth=.9, zorder=3)
        dx, ha = {'Last prompt: eventual': (-6, 'right'), 'Last prompt: near-term': (-6, 'right'),
                  'Reasoning: paper cohort': (-5, 'right'), 'Reasoning: extended': (6, 'left'),
                  'Reasoning: this reply': (6, 'left')}[r['label']]
        right.annotate(f"{r['estimate']:.2f}", (x, r['estimate']), xytext=(dx, 0), va='center',
                       textcoords='offset points', ha=ha, fontsize=6.8, color=color,
                       bbox=dict(boxstyle='square,pad=0.1', facecolor='white', edgecolor='none'))
    right.set(xlim=(-.5, 2.4), ylim=(.4, 1.0))
    right.set_ylabel('AUROC (95% CI)', fontsize=7, labelpad=2)
    right.set_xticks([0, 1, 2], ['Eventual\noutcome', 'This or next\nround', 'This\nreply'], fontsize=7)
    right.tick_params(axis='x', length=0, pad=3)
    right.set_yticks([.5, .6, .7, .8, .9, 1.0])
    right.axhline(.5, color=GREY, linestyle='--', linewidth=.8, zorder=0)
    right.grid(axis='y', alpha=.15)
    right.set_xlabel('Label horizon  (closer to the leak \u2192)', fontsize=7, labelpad=2)
    fig.text(.585, .955, '(b) The closer the label, the more readable', weight='bold', fontsize=8)
    fig.text(.585, .895, 'Descriptive: labels and reply sets differ between points', fontsize=6.2, color=GREY)
    handles = [Line2D([], [], marker='D', color=SLATE, linestyle='', markersize=4, label='Last-prompt probe'),
               Line2D([], [], marker='o', color=TEAL, linestyle='', markersize=4, label='Reasoning (paper replies)'),
               Line2D([], [], marker='^', color=TEAL, linestyle='', markersize=4.5, label='Reasoning (+ leaking replies)')]
    right.legend(handles=handles, loc='upper left', bbox_to_anchor=(0, 1.02), ncol=1, frameon=False,
                 fontsize=6.4, handletextpad=.2, labelspacing=.35, borderaxespad=.2)

    fig.text(.012, .045, '* Peer message and tool results before the reply; one seed.   '
             '† Pre-ask replies vs eventual outcome.', fontsize=6.2, color=GREY)
    for ext in ['png', 'pdf']:
        fig.savefig(output / f'figure3_streaming.{ext}', dpi=300, facecolor='white')
    plt.close(fig)
    return W, H


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
    w, h = render(rows, args.output_dir)
    print(f'{len(rows)} saved estimates; figure size {w} × {h} inches.')


if __name__ == '__main__':
    main()
