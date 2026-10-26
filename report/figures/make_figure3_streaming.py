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


CAPTION = """Figure 3. On gpt-oss-20b, a probe reading the model's reasoning picks out the reply that will leak the secret, and reading the text of the same reasoning does not. This analysis is exploratory and was designed after the main results. (a) Each row scores the same 1,995 replies that have reasoning (121 of them leak) from 238 episodes, on held-out scenarios. A reply counts as leaking if it is the first to make the secret public, by any route. AUROC measures how well a score ranks leaking replies above the others: 0.5 is chance and 1 is perfect. Whiskers are 95% bootstrap confidence intervals. "Stopped before the secret is mentioned" ignores every reasoning token from the first time the secret appears in the reasoning. The length row uses the final length of the reasoning, which is known only after the reply, so it is not a usable alarm. *This probe reads only what arrives before the reply: the peer's message and tool results (one seed; 2,199 replies, 143 leaking). It also scores 0.93, so much of the signal is already there before the model reasons. †The same probe, scored on replies from before the peer asks, against whether the episode ever leaks (628 replies, 388 positives); it stays at chance, as it should. (b) The same kind of probe, asked about leaks at different distances. The points are not a paired comparison: the reply set and the input differ between them. Probe at end of incoming message: 2,059 replies (169 positives for "ever", 148 for "this round or next"). Probe on reasoning, this round or next: 1,874 replies, 118 positives. The 0.93 point is the headline result from panel a, whose reply set also includes each episode's first leaking reply. Appendix J.8 gives the full table, including the reasoning probe on that larger reply set for "this round or next" (0.64). All points cover 238 episodes. Values and exact source keys are in figure3_streaming.csv.
"""


DISPLAY_A = {  # CSV label -> (display label, panel-a row position, top to bottom)
    'Reasoning-token probe': ("Probe on the model's reasoning", 9.0),
    'Before value mention': ('Same, stopped before the secret is mentioned', 8.1),
    'Incoming-message probe*': ("Probe on the peer's message only*", 7.2),
    'Length (hindsight)': ('Length of the reasoning (known only afterwards)', 5.3),
    'Jev on reasoning': ('LLM judge (Jev) reading the reasoning', 4.4),
    'Keywords': ('Keyword search', 3.5),
    'GPT-5-nano on reasoning': ('Small LLM (GPT-5-nano) reading the reasoning', 2.6),
    'Pre-ask placebo†': ('Probe before any request (should be ~0.5)†', .7),
}
GROUP_HEADINGS = [(9.75, "Probe reading the model's internals", '#087f8c'),
                  (6.05, 'Reading the text instead', '#334155'),
                  (1.45, 'Sanity check', '#64748b')]
# Panel b. To add a horizon: insert it into HORIZONS (left = far from the leak, right = nearest),
# then map its CSV label in B_ROWS. Horizons with no plotted row are skipped automatically.
# The extended-cohort near-term point (0.64) is left to Appendix J.8; the this-reply point uses
# panel a's reply set, which adds the leaking replies (see caption).
HORIZONS = [('eventual', 'Will it\never leak?'),
            ('round', 'Leak this\nround or next?'),
            ('reply', 'Leak in\nthis reply?')]
SERIES_B = {'last-prompt': ('Probe at end of incoming message', 'D', -1),
            'reasoning': ('Probe on reasoning', 'o', +1)}  # (legend, marker, side of value label)
B_ROWS = {'Last prompt: eventual': ('eventual', 'last-prompt'),
          'Last prompt: near-term': ('round', 'last-prompt'),
          'Reasoning: paper cohort': ('round', 'reasoning'),
          'Reasoning: this reply': ('reply', 'reasoning')}
TEAL, SLATE, GREY = '#087f8c', '#334155', '#64748b'


def render(rows, output):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7,
                         'pdf.fonttype': 42, 'ps.fonttype': 42,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.labelcolor': SLATE, 'text.color': SLATE,
                         'xtick.color': SLATE, 'ytick.color': SLATE,
                         'xtick.labelsize': 7, 'ytick.labelsize': 7})
    W, H = 6.5, 2.85
    fig = plt.figure(figsize=(6.5, 2.85), facecolor='white')
    left = fig.add_axes([.355, .25, .21, .60])
    right = fig.add_axes([.69, .25, .295, .60])

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
                  fontsize=6.5, weight='bold' if head else 'normal')
    for y, text, color in GROUP_HEADINGS:
        left.text(-.03, y, text, transform=left.get_yaxis_transform(), ha='right', va='center',
                  fontsize=6.2, style='italic', color=color)
    left.set_yticks([])
    left.set(xlim=(.25, 1), ylim=(.1, 10.2))
    left.set_xticks([.3, .5, .7, .9])
    left.spines['left'].set_visible(False)
    for y in [6.6, 1.95]:
        left.axhline(y, xmin=-1.6, color='#CBD5E1', linewidth=.6, clip_on=False)
    left.axvline(.5, color=GREY, linestyle='--', linewidth=.8, zorder=0)
    left.text(.5, 10.2, 'chance', ha='center', va='bottom', fontsize=6, color=GREY)
    left.grid(axis='x', alpha=.15)
    left.annotate('warns before the\nreply\'s output', xy=(.905, 8.1), xytext=(.84, 8.1),
                  ha='right', va='center', fontsize=6, color=TEAL, linespacing=1.1,
                  bbox=dict(boxstyle='square,pad=0.15', facecolor='white', edgecolor='none'),
                  arrowprops=dict(arrowstyle='->', color=TEAL, linewidth=.6))
    fig.text(.29, .14, 'AUROC: how well it separates leaking replies (0.5 = chance, 1 = perfect)',
             fontsize=6.8, ha='center')
    fig.text(.012, .955, '(a) gpt-oss-20b: which reply will leak the secret?', weight='bold', fontsize=7.8)

    # (b) label ladder
    b_rows = [r for r in rows if r['panel'] == 'b' and r['label'] in B_ROWS]
    used = [h for h, _ in HORIZONS if any(B_ROWS[r['label']][0] == h for r in b_rows)]
    xpos = {h: 1.1 * i for i, h in enumerate(used)}
    for r in b_rows:
        horizon, series = B_ROWS[r['label']]
        _, marker, side = SERIES_B[series]
        shared = sum(B_ROWS[q['label']][0] == horizon for q in b_rows) > 1
        x = xpos[horizon] + (.1 * side if shared else 0)
        color = TEAL if series == 'reasoning' else SLATE
        right.errorbar(x, r['estimate'], yerr=[[r['estimate']-r['low']], [r['high']-r['estimate']]],
                       fmt=marker, color=color, markersize=4.2, capsize=1.8, linewidth=.9, zorder=3)
        right.annotate(f"{r['estimate']:.2f}", (x, r['estimate']), xytext=(6 * side, 0), va='center',
                       textcoords='offset points', ha='left' if side > 0 else 'right', fontsize=6.8,
                       color=color, bbox=dict(boxstyle='square,pad=0.1', facecolor='white', edgecolor='none'))
    right.set(xlim=(-.6, xpos[used[-1]] + .55), ylim=(.4, 1.0))
    right.set_ylabel('AUROC', fontsize=7, labelpad=2)
    right.set_xticks(list(xpos.values()), [dict(HORIZONS)[h] for h in used],
                     fontsize=6.6)
    right.tick_params(axis='x', length=0, pad=3)
    right.set_yticks([.5, .6, .7, .8, .9, 1.0])
    right.axhline(.5, color=GREY, linestyle='--', linewidth=.8, zorder=0)
    right.grid(axis='y', alpha=.15)
    fig.text(.525, .955, '(b) The nearer the leak, the easier to predict', weight='bold', fontsize=7.8)
    handles = [Line2D([], [], marker=m, color=TEAL if k == 'reasoning' else SLATE, linestyle='',
                      markersize=4, label=name) for k, (name, m, _) in SERIES_B.items()]
    right.legend(handles=handles, loc='upper left', bbox_to_anchor=(0, 1.02), ncol=1, frameon=False,
                 fontsize=6.3, handletextpad=.2, labelspacing=.35, borderaxespad=.2)

    fig.text(.012, .035, "* Also sees tool results; one seed.   † Scored on replies before the peer asks.",
             fontsize=6.2, color=GREY)
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
