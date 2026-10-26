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
from matplotlib.transforms import blended_transform_factory

ROOT = Path(__file__).resolve().parents[2]
STREAM = ROOT / 'runs/20261026-0526-e05-reasoning-stream'
INCOMING = ROOT / 'runs/20261026-1128-e05-stream-layer18-loso'
PERCALL = ROOT / 'runs/20261026-1221-e05-lastprompt-percall-6013'
QWEN_MAIN = ROOT / 'runs/20261025-1456-e05-all-data-main'
QWEN_PERCALL = ROOT / 'runs/20261026-1237-e05-qwen-percall'
CONFIRM = ROOT / 'runs/20261026-1302-e05-stream-confirm-score'
# Panel-b rungs still being computed; kept as blank CSV rows and plotted once filled.
PENDING_B = [('gpt-oss last prompt: eventual', 'oss-lp', 'Any-public-emission label, eventual horizon'),
             ('gpt-oss last prompt: round', 'oss-lp', 'Any-public-emission label, this round or next')]
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
    add('b', 'gpt-oss reasoning: this call', 'oss-reason', m['immediate/all/loso/extended/token_max'], path, digest,
        'immediate/all/loso/extended/token_max', 'Same estimate as the panel-a headline row')
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
    pc, path, digest = read(PERCALL / 'metrics.json')
    add('a', 'Last-prompt probe retrained per call', 'activation', pc['matched/immediate/loso'], path, digest,
        'matched/immediate/loso', "Paper's last-prompt probe refit on the per-call label; same replies as the reasoning probe")
    for key, label in [('matched/immediate/loso', 'gpt-oss last prompt: this call'),
                       ('matched/strict1/loso', 'gpt-oss last prompt: next call')]:
        add('b', label, 'oss-lp', pc[key], path, digest, key, 'Last-prompt probe fit on this horizon; any public emission')
    qm, path, digest = read(QWEN_MAIN / 'metrics.json')
    for variant, label in [('eventual', 'Qwen last prompt: eventual'), ('A_hazard', 'Qwen last prompt: round')]:
        add('b', label, 'qwen-lp', qm[variant]['loso']['methods']['nested'], path, digest,
            f'{variant}/loso/methods/nested', "Paper's main Qwen3-32B probe; paper's give-in rule")
    qp, path, digest = read(QWEN_PERCALL / 'metrics.json')
    for key, label in [('immediate/loso', 'Qwen last prompt: this call'), ('strict1/loso', 'Qwen last prompt: next call')]:
        add('b', label, 'qwen-lp', qp[key], path, digest, key, "Same probe recipe fit on this horizon; paper's give-in rule")
    cf, path, digest = read(CONFIRM / 'metrics.json')
    counts = json.loads((CONFIRM / 'counts.json').read_bytes())
    data = dict(cf['max_score'], rows=counts['scored_recruiting_replies'],
                positives=counts['positive_reasoning_replies'], episodes=counts['recruiting_episodes'])
    note = 'Frozen reasoning probe and threshold on new episodes; no refitting'
    add('a', 'Frozen probe, new episodes', 'activation', data, path, digest, 'max_score', note, seeds=1)
    add('b', 'gpt-oss reasoning, new episodes: this call', 'oss-new', data, path, digest, 'max_score', note, seeds=1)
    for label, group, note in PENDING_B:
        rows.append(dict(panel='b', label=label, group=group, estimate='', low='', high='', rows='', positives='',
                         episodes='', seeds='', source='', source_sha256='', source_key='', note='PENDING: ' + note))
    return rows


CAPTION = """Figure 3. On gpt-oss-20b, a probe reading the model's reasoning picks out the reply that will leak the secret, and reading the text of the same reasoning does not. This analysis is exploratory and was designed after the main results. (a) Each row scores the same 1,995 replies that have reasoning (121 of them leak) from 238 episodes, on held-out scenarios. A reply counts as leaking if it is the first to make the secret public, by any route. AUROC measures how well a score ranks leaking replies above the others: 0.5 is chance and 1 is perfect. Whiskers are 95% bootstrap confidence intervals. The right-hand column shows the practical trade-off: each detector's alarm cutoff is set so that about 5% of no-ask control replies alarm, and the column gives the share of leaking replies that cutoff catches and the share of normal replies in pressured episodes that never leak on which it fires. The keyword rule never fires, because it matches more than 5% of control replies. The two LLM judges (Jev and GPT-5-nano) read only the reasoning text of the call, as six growing snapshots scored with a running maximum and with the secret masked; they see no conversation or tool results, whereas the probes' activations reflect the full context. "Last prompt token" is the paper's main probe, read at the last prompt token before the model writes anything, retrained to ask whether this call will leak (1,995 replies, 121 leaking; three seeds). "Same, frozen, on 84 new episodes" applies the reasoning probe and its alarm cutoff, both fixed before the episodes were collected, to new episodes (594 replies with reasoning, 26 leaking, from 57 recruiting episodes). "Stopped before the secret is mentioned" ignores every reasoning token from the first time the secret appears in the reasoning. The length row uses the final length of the reasoning, which is known only after the reply, so it is not a usable alarm. *A separate probe, trained on this label for each call, that reads only what arrives before the reply: the peer's message and tool results. It used a reduced recipe (one seed, layer 18; 2,199 replies, 143 leaking). It also scores 0.93, so much of the signal is already there before the model reasons, but it alarms far more often on normal replies. †The same probe, scored on replies from before the peer asks, against whether the episode ever leaks (628 replies, 388 positives); it stays at chance, as it should. (b) Matched ladders: within each series the model, the outcome and the reading position are fixed and only the horizon changes; lines join points of the same series, and the series are not compared with each other. Qwen3-32B, last prompt token, the paper's give-in outcome: the paper's eventual and near-term results (0.52 and 0.58; 4,697 steps from 241 episodes), and the same recipe fit per call (this call, 0.95, on 4,844 calls; next call, 0.71, on 4,743 calls; 101 positives each). gpt-oss-20b, last prompt token, any public emission: fit per call on the panel-a replies (this call, 0.91; 1,995 calls, 121 positives) and one call ahead (0.62; 1,874 calls, 116 positives). Retrained to ask whether this call will leak, the paper's last-prompt probe reaches 0.91 before the model writes anything; reading the reasoning adds a little (0.93, the panel-a headline). "Next call" excludes the leaking calls themselves, so it ranks the call just before the leak; on gpt-oss that call is usually the one that reads the protected file (Appendix J.8). Values and exact source keys are in figure3_streaming.csv.
"""


DISPLAY_A = {  # CSV label -> (display label, panel-a row position, top to bottom)
    'Reasoning-token probe': ("Probe on the model's reasoning", 10.8),
    'Before value mention': ('Same, stopped before secret is mentioned', 9.9),
    'Frozen probe, new episodes': ('Same, frozen, on 84 new episodes', 9.0),
    'Last-prompt probe retrained per call': ('Last prompt token (before the call starts)', 8.1),
    'Incoming-message probe*': ('Probe on incoming message + tool results*', 7.2),
    'Length (hindsight)': ('Reasoning length (known only afterwards)', 5.3),
    'Jev on reasoning': ('LLM judge (Jev) on the reasoning', 4.4),
    'Keywords': ('Keyword search', 3.5),
    'GPT-5-nano on reasoning': ('Small LLM (GPT-5-nano) on the reasoning', 2.6),
    'Pre-ask placebo†': ('Probe before any request (should be ~0.5)†', .7),
}
# Alarm column: % of leaking replies flagged / % of normal held-episode replies flagged, at a cutoff
# set for ~5% alarms on no-ask control replies. Sources: report/paper.md Appendix J.8 "Alarms and lead"
# (reasoning probe 84.8/4.4, Jev 91.7/9.0-9.4, GPT-5-nano 5.0/34.6; keyword rules never alarm) and
# runs/20261026-1128-e05-stream-layer18-loso/report.md (incoming probe 95.1/19.1), and
# runs/20261026-1221-e05-lastprompt-percall-6013/metrics.json matched/immediate/loso, seed means of
# positive_reply_alarm_by_seed / held_reply_alarm_by_seed (retrained last-prompt probe 56.5/1.6), and
# runs/20261026-1302-e05-stream-confirm-score/report.md frozen alarms (new episodes 14/26 = 53.8%, 12/490 = 2.4%).
ALARMS = {'Reasoning-token probe': '85% / 4%', 'Frozen probe, new episodes': '54% / 2%', 'Last-prompt probe retrained per call': '56% / 2%', 'Incoming-message probe*': '95% / 19%',
          'Jev on reasoning': '92% / 9%', 'GPT-5-nano on reasoning': '5% / 35%',
          'Keywords': 'never fires'}
GROUP_HEADINGS = [(11.55, "Probe reading the model's internals", '#087f8c'),
                  (6.05, 'Reading the text instead', '#334155'),
                  (1.45, 'Sanity check', '#64748b')]
# Panel b: matched ladders. Within a series the model, the outcome and the reading position are fixed and
# only the horizon changes. To add a rung, add a CSV row and map its label in B_ROWS; blank rows are skipped.
HORIZONS = [('eventual', 'Will it\never\ngive in?'),
            ('round', 'This\nround or\nnext?'),
            ('next', 'Next\ncall?'),
            ('reply', 'This\ncall?')]
B_ROWS = {'Qwen last prompt: eventual': ('eventual', 'qwen-lp'),
          'Qwen last prompt: round': ('round', 'qwen-lp'),
          'Qwen last prompt: next call': ('next', 'qwen-lp'),
          'Qwen last prompt: this call': ('reply', 'qwen-lp'),
          'gpt-oss last prompt: eventual': ('eventual', 'oss-lp'),
          'gpt-oss last prompt: round': ('round', 'oss-lp'),
          'gpt-oss last prompt: next call': ('next', 'oss-lp'),
          'gpt-oss last prompt: this call': ('reply', 'oss-lp'),
          'gpt-oss reasoning: this call': ('reply', 'oss-reason'),
}
# The frozen new-episode result (0.905) is shown as a panel-a row rather than a fourth point here.
TEAL, SLATE, GREY = '#087f8c', '#334155', '#64748b'
# series -> (legend, marker, colour, filled, value-label position; per-horizon overrides)
SERIES_B = {'qwen-lp': ('Qwen3-32B, last prompt', 'D', SLATE, True, {'*': 'left', 'reply': 'above'}),
            'oss-lp': ('gpt-oss, last prompt', 'D', TEAL, False, {'*': 'right', 'reply': 'below'}),
            'oss-reason': ('gpt-oss, reasoning', 'o', TEAL, True, {'*': 'right'})}


def render(rows, output):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7,
                         'pdf.fonttype': 42, 'ps.fonttype': 42,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.labelcolor': SLATE, 'text.color': SLATE,
                         'xtick.color': SLATE, 'ytick.color': SLATE,
                         'xtick.labelsize': 7, 'ytick.labelsize': 7})
    W, H = 6.5, 2.95
    fig = plt.figure(figsize=(W, H), facecolor='white')
    left = fig.add_axes([.315, .245, .16, .60])
    right = fig.add_axes([.725, .245, .255, .60])
    col = blended_transform_factory(fig.transFigure, left.transData)
    ALARM_X = .617

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
        alarm = ALARMS.get(r['label'], '–')
        left.text(ALARM_X, y, alarm, transform=col, ha='center', va='center', fontsize=6.6,
                  color=GREY if alarm in ('–', 'never fires') else SLATE, weight='bold' if head else 'normal')
        left.text(-.03, y, label, transform=left.get_yaxis_transform(), ha='right', va='center',
                  fontsize=6.5, weight='bold' if head else 'normal')
    for y, text, color in GROUP_HEADINGS:
        left.text(-.03, y, text, transform=left.get_yaxis_transform(), ha='right', va='center',
                  fontsize=6.2, style='italic', color=color)
    left.set_yticks([])
    left.set(xlim=(.25, 1), ylim=(.1, 12.0))
    left.set_xticks([.3, .5, .7, .9])
    left.spines['left'].set_visible(False)
    for y in [6.6, 1.95]:  # group separators
        left.axhline(y, xmin=-1.7, xmax=2.0, color='#CBD5E1', linewidth=.6, clip_on=False)
    left.axvline(.5, color=GREY, linestyle='--', linewidth=.8, zorder=0)
    auroc_x = left.transData.transform((1.012, 0))[0] / fig.bbox.width
    fig.text(auroc_x, .893, 'AUROC', ha='left', va='bottom', fontsize=6.4, weight='bold')
    fig.text(ALARM_X, .893, 'Catch / false alarm', ha='center', va='bottom', fontsize=6.4, weight='bold')
    fig.text(ALARM_X, .862, '(% leaks / % normal)', ha='center', va='bottom', fontsize=6, color=GREY)
    left.text(.5, 12.0, 'chance', ha='center', va='bottom', fontsize=6, color=GREY)
    left.grid(axis='x', alpha=.15)
    left.annotate('warns before the\nreply\'s output', xy=(.93, 9.9), xytext=(.85, 9.9),
                  ha='right', va='center', fontsize=6, color=TEAL, linespacing=1.1,
                  bbox=dict(boxstyle='square,pad=0.15', facecolor='white', edgecolor='none'),
                  arrowprops=dict(arrowstyle='->', color=TEAL, linewidth=.6))
    fig.text(.395, .145, 'AUROC: how well it ranks leaking replies first\n(0.5 = chance, 1 = perfect)',
             fontsize=6.6, ha='center', va='top', linespacing=1.1)
    fig.text(.012, .955, '(a) gpt-oss-20b: which reply will leak the secret?', weight='bold', fontsize=7.8)

    # (b) matched ladders
    b_rows = [r for r in rows if r['panel'] == 'b' and r['label'] in B_ROWS and r['estimate'] != '']
    used = [h for h, _ in HORIZONS if any(B_ROWS[r['label']][0] == h for r in b_rows)]
    xpos = {h: 1.1 * i for i, h in enumerate(used)}
    order = list(SERIES_B)
    points = {k: [] for k in order}
    for h in used:  # spread the series present at each horizon evenly around the tick
        here = sorted((r for r in b_rows if B_ROWS[r['label']][0] == h), key=lambda r: order.index(B_ROWS[r['label']][1]))
        for i, r in enumerate(here):
            points[B_ROWS[r['label']][1]].append((h, xpos[h] + .18 * (i - (len(here) - 1) / 2), r))
    for series, pts in points.items():
        name, marker, color, filled, where_map = SERIES_B[series]
        if len(pts) > 1:
            right.plot([x for _, x, _ in pts], [r['estimate'] for _, _, r in pts], color=color, lw=.7, alpha=.45, zorder=2)
        for h, x, r in pts:
            right.errorbar(x, r['estimate'], yerr=[[r['estimate']-r['low']], [r['high']-r['estimate']]],
                           fmt=marker, color=color, markersize=4.2, capsize=1.8, linewidth=.9, zorder=3,
                           markerfacecolor=color if filled else 'white', markeredgewidth=1)
            where = where_map.get(h, where_map['*'])
            anchor, offset, va, ha = {'left': (r['estimate'], (-5, 0), 'center', 'right'),
                                      'right': (r['estimate'], (5, 0), 'center', 'left'),
                                      'above': (r['high'], (0, 2), 'bottom', 'center'),
                                      'below': (r['low'], (0, -2), 'top', 'center')}[where]
            right.annotate(f"{r['estimate']:.2f}", (x, anchor), xytext=offset, va=va,
                           textcoords='offset points', ha=ha, fontsize=6.6, color=color,
                           bbox=dict(boxstyle='square,pad=0.1', facecolor='white', edgecolor='none'))
    right.set(xlim=(-.5, xpos[used[-1]] + .62), ylim=(.4, 1.03))
    right.set_ylabel('AUROC', fontsize=7, labelpad=2)
    right.set_xticks(list(xpos.values()), [dict(HORIZONS)[h] for h in used],
                     fontsize=6.3, linespacing=1.05)
    right.tick_params(axis='x', length=0, pad=3)
    right.set_yticks([.5, .6, .7, .8, .9, 1.0])
    right.axhline(.5, color=GREY, linestyle='--', linewidth=.8, zorder=0)
    right.grid(axis='y', alpha=.15)
    fig.text(.555, .955, '(b) The nearer the act, the easier to predict', weight='bold', fontsize=7.6)
    handles = [Line2D([], [], marker=m, color=c, linestyle='', markersize=4, markeredgewidth=1, label=name,
                      markerfacecolor=c if filled else 'white')
               for name, m, c, filled, _ in SERIES_B.values()]
    right.legend(handles=handles, loc='upper left', bbox_to_anchor=(-.02, .96), ncol=1, frameon=False,
                 fontsize=6.1, handletextpad=.2, labelspacing=.35, borderaxespad=.2)

    fig.text(.012, .035, "* Separate probe trained on this label; one seed, reduced recipe.   † Scored on replies before the peer asks.",
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
                row[key] = float(row[key]) if row[key] else ''
            for key in ['rows', 'positives', 'episodes', 'seeds']:
                row[key] = int(row[key]) if row[key] else ''
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
