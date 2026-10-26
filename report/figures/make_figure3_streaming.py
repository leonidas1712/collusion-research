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
QWEN_LADDER = ROOT / 'runs/20261026-1313-e05-qwen-label-ladder'
QWEN_PERCALL = ROOT / 'runs/20261026-1237-e05-qwen-percall'
CONFIRM = ROOT / 'runs/20261026-1302-e05-stream-confirm-score'
LADDER = ROOT / 'runs/20261026-1304-e05-lastprompt-label-ladder'
JEV_INPUT = ROOT / 'runs/20261026-1306-e06-percall-input-jev'
JEV_INPUT_QWEN = ROOT / 'runs/20261026-1309-e06-percall-input-jev-qwen'
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
    ql, lpath, ldigest = read(QWEN_LADDER / 'metrics.json')
    for key, label in [('eventual/loso', 'Qwen last prompt (matched): eventual'),
                       ('round_near/loso', 'Qwen last prompt (matched): round')]:
        add('b', label, 'qwen-lp', ql[key], lpath, ldigest, key,
            "Last-prompt probe fit on this horizon on the same 4,844 calls as this call; paper's give-in rule")
    for key, label in [('immediate/loso', 'Qwen last prompt: this call'), ('strict1/loso', 'Qwen last prompt: next call')]:
        add('b', label, 'qwen-lp', qp[key], path, digest, key, "Same probe recipe fit on this horizon; paper's give-in rule")
    cf, path, digest = read(CONFIRM / 'metrics.json')
    counts = json.loads((CONFIRM / 'counts.json').read_bytes())
    data = dict(cf['max_score'], rows=counts['scored_recruiting_replies'],
                positives=counts['positive_reasoning_replies'], episodes=counts['recruiting_episodes'])
    note = 'Frozen reasoning probe and threshold on new episodes; no refitting'
    add('a', 'Frozen probe, new episodes', 'activation', data, path, digest, 'max_score', note, seeds=1)
    add('b', 'gpt-oss reasoning, new episodes: this call', 'oss-new', data, path, digest, 'max_score', note, seeds=1)
    ji, path, digest = read(JEV_INPUT / 'metrics.json')
    add('a', 'Jev on call input', 'text/rule', ji['loso'], path, digest, 'loso',
        'Jev 1.14 on the saved request (conversation, tool results; private reasoning removed, value masked); no fit', seeds=0)
    jq, path, digest = read(JEV_INPUT_QWEN / 'metrics.json')
    add('a', 'Jev on call input (Qwen)', 'text/rule', jq['loso'], path, digest, 'loso',
        'Qwen3-32B: Jev 1.14 on the saved request (conversation, tool results; value masked); no fit', seeds=0)
    ld, path, digest = read(LADDER / 'metrics.json')
    for key, label in [('eventual_any/loso', 'gpt-oss last prompt: eventual'), ('round_any/loso', 'gpt-oss last prompt: round')]:
        add('b', label, 'oss-lp', ld[key], path, digest, key,
            'Last-prompt probe fit on this horizon; any public emission; same 1,995 calls as this call')
    return rows


CAPTION = """Figure 3. A probe on the model's activations picks out the call that will give in; an LLM judge given the same material does reasonably on Qwen3-32B but far below the probe, and on gpt-oss-20b ranks the leaking calls below the others. This analysis is exploratory and was designed after the main results. (a) Per-call within scenario × round AUROC on held-out scenarios (0.5 is chance, 1 is perfect); whiskers are 95% family-bootstrap confidence intervals. A call is positive if it is the first to make the protected value public: for gpt-oss-20b by any public emission (1,995 calls with reasoning, 121 positive, 238 episodes), for Qwen3-32B by the paper's give-in rule (4,844 calls, 101 positive, 241 episodes). The last-prompt probe reads one position before the call generates anything; the reasoning probe takes the maximum over the call's reasoning tokens. The frozen row applies the reasoning probe and its alarm cutoff, both fixed in advance, to 84 new episodes (594 calls with reasoning, 26 leaking, from 57 recruiting episodes). Jev 1.14 is given the same conversation and tool results as the last-prompt probe and asked whether this call will write or post the value; on gpt-oss-20b, as asked, it ranks the leaking calls below the others within a stratum (0.27; 0.73 if reversed post hoc, still below the probe's 0.91) and flags nearly every pressured call; its input excludes earlier same-turn private reasoning, which the probe's activations may retain. Jev reading the reasoning sees only the call's reasoning text, as six growing snapshots scored with a running maximum and with the value masked. At a cutoff set for about 5% alarms on no-ask control calls, the share of leaking calls caught and of calls in never-leaking episodes flagged is 56% / 2% for the last-prompt probe, 85% / 4% for the reasoning probe, 54% / 2% for the frozen probe on new episodes, 98% / 87% for Jev on the same input and 92% / 9% for Jev on the reasoning; on Qwen3-32B, Jev on the same input is 71% / 28%. Qwen3-32B runs without reasoning. Further checks and baselines are in Figure 3b. (b) Matched ladders: within each series the model, the outcome, the reading position and the calls are fixed, and only the label horizon changes; lines join points of the same series, and the series are not compared with each other. Qwen3-32B, last prompt token, the paper's give-in rule, on the same 4,844 calls from 241 episodes (ever, 0.54, 1,105 positives; this round or next, 0.67, 352 positives; this call, 0.95, 101 positives); these round-level values differ from the paper's 0.52 and 0.58, which use the original 4,697-step cohort without the give-in calls. gpt-oss-20b, last prompt token, any public emission rather than the paper's give-in rule, on the same 1,995 panel-a calls from 238 episodes (ever, 0.61, 330 positives; this round or next, 0.64, 304 positives; this call, 0.91, 121 positives). Retrained to ask whether this call will leak, the paper's last-prompt probe reaches 0.91 before the model writes anything; reading the reasoning adds a little (0.93, the panel-a headline). One-call-ahead results (Qwen3-32B 0.71, gpt-oss-20b 0.62) use different call sets that exclude the give-in calls and are left to the appendix. Values and exact source keys are in figure3_streaming.csv.
"""

CAPTION_APPX = """Figure 3b. Further checks on the gpt-oss-20b per-call result (exploratory). Same metric, calls and alarm cutoff as Figure 3a; the reasoning-token probe is repeated for reference. "Reasoning written before it names the secret" ignores every reasoning token from the first time the value appears in the reasoning. *A separate probe trained on this label that reads only what arrives before the call, the peer's message and tool results, with a reduced recipe (one seed, layer 18; 2,199 calls, 143 leaking); it also ranks well, so much of the signal is present before the model reasons, but it flags far more normal calls. Keyword search never fires because the rule matches more than 5% of control calls. Reasoning length uses the final length of the reasoning, known only after the call, so it is not a usable alarm. GPT-5-nano reads only the reasoning text, as six growing snapshots with a running maximum and the value masked. †The probe applied to calls before the peer asks, against whether the episode ever leaks (628 calls, 388 positives); it stays at chance, as it should. Values and exact source keys are in figure3_streaming.csv.
"""

TEAL, SLATE, GREY = '#087f8c', '#334155', '#64748b'
# Forest rows: (kind, CSV label or heading text, display label, indent). Rows whose CSV value is blank are skipped.
MAIN_ROWS = [('head', 'gpt-oss-20b'),
             ('row', 'Last-prompt probe retrained per call', 'probe on last prompt token, before the call starts', 0),
             ('row', 'Reasoning-token probe', 'probe on reasoning tokens, as they stream', 0),
             ('row', 'Frozen probe, new episodes', '\u21b3 same probe frozen, on 84 new episodes', 1),
             ('row', 'Jev on call input', 'Jev given the same conversation + tool results', 0),
             ('row', 'Jev on reasoning', 'Jev reading the reasoning', 0),
             ('head', 'Qwen3-32B (no reasoning)'),
             ('row', 'Qwen last prompt: this call', 'probe on last prompt token, before the call starts', 0),
             ('row', 'Jev on call input (Qwen)', 'Jev given the same conversation + tool results', 0)]
APPX_ROWS = [('head', 'Linear probe on activations, reading:'),
             ('row', 'Reasoning-token probe', 'reasoning tokens, as they stream (Figure 3a)', 0),
             ('row', 'Before value mention', '\u21b3 reasoning written before it names the secret', 1),
             ('row', 'Incoming-message probe*', 'the incoming message + tool results*', 0),
             ('head', 'Rule or LLM reading the text:'),
             ('row', 'Keywords', 'keyword search', 0),
             ('row', 'Length (hindsight)', 'reasoning length (known only afterwards)', 0),
             ('row', 'GPT-5-nano on reasoning', 'GPT-5-nano reading the reasoning', 0),
             ('head', 'Sanity check:'),
             ('row', 'Pre-ask placebo\u2020', 'probe before any request (expect ~0.5)\u2020', 0)]
BOLD = {'Reasoning-token probe'}
# Alarm column for the appendix figure: % of leaking calls flagged / % of normal held-episode calls flagged,
# at a cutoff set for ~5% alarms on no-ask control calls. Sources: report/paper.md Appendix J.8 "Alarms and
# lead" (reasoning probe 84.8/4.4, Jev 91.7/9.0-9.4, GPT-5-nano 5.0/34.6; keyword rules never alarm);
# runs/20261026-1128-e05-stream-layer18-loso/report.md (incoming probe 95.1/19.1);
# runs/20261026-1221-e05-lastprompt-percall-6013/metrics.json matched/immediate/loso seed means (56.5/1.6);
# runs/20261026-1302-e05-stream-confirm-score/report.md (new episodes 14/26, 12/490);
# runs/20261026-1306-e06-percall-input-jev/report.md (Jev on the call's input 98.3/86.5);
# runs/20261026-1309-e06-percall-input-jev-qwen/report.md (Qwen, LOSO 71.3/27.7).
# The main-figure values are quoted in CAPTION.
ALARMS = {'Reasoning-token probe': '85% / 4%', 'Incoming-message probe*': '95% / 19%',
          'GPT-5-nano on reasoning': '5% / 35%', 'Keywords': 'never fires'}

# Panel b: matched ladders. Within a series the model, the outcome and the reading position are fixed and
# only the horizon changes. To add a rung, add a CSV row and map its label in B_ROWS; blank rows are skipped.
HORIZONS = [('eventual', 'Will it\never\ngive in?'),
            ('round', 'This\nround or\nnext?'),
            ('next', 'Next\ncall?'),
            ('reply', 'This\ncall?')]
B_ROWS = {'Qwen last prompt (matched): eventual': ('eventual', 'qwen-lp'),
          'Qwen last prompt (matched): round': ('round', 'qwen-lp'),
          'Qwen last prompt: this call': ('reply', 'qwen-lp'),
          'gpt-oss last prompt: eventual': ('eventual', 'oss-lp'),
          'gpt-oss last prompt: round': ('round', 'oss-lp'),
          'gpt-oss last prompt: this call': ('reply', 'oss-lp'),
          'gpt-oss reasoning: this call': ('reply', 'oss-reason'),
}
# Unplotted CSV rows: the gpt-oss and Qwen next-call rows (0.62, 0.71), which use different call sets, and
# the paper-cohort Qwen eventual/round rows (0.52, 0.58), replaced here by the matched same-call values.
# The frozen new-episode result (0.905) is shown as a panel-a row rather than a fourth point here.
TEAL, SLATE, GREY = '#087f8c', '#334155', '#64748b'
# series -> (legend, marker, colour, filled, value-label position; per-horizon overrides)
SERIES_B = {'qwen-lp': ('Qwen3-32B, last prompt', 'D', SLATE, True, {'*': 'below', 'round': 'left', 'next': 'right', 'reply': 'above'}),
            'oss-lp': ('gpt-oss, last prompt', 'D', TEAL, False, {'*': 'above', 'round': 'right', 'next': 'below', 'reply': 'below'}),
            'oss-reason': ('gpt-oss, reasoning', 'o', TEAL, True, {'*': 'right'})}




def style():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7,
                         'pdf.fonttype': 42, 'ps.fonttype': 42,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.labelcolor': SLATE, 'text.color': SLATE,
                         'xtick.color': SLATE, 'ytick.color': SLATE,
                         'xtick.labelsize': 7, 'ytick.labelsize': 7})


def forest(fig, ax, spec, lookup, label_x, xlim=(.2, 1), alarm_x=None):
    """Draw a labelled forest of AUROC rows; returns nothing. Labels are left-aligned at figure x label_x."""
    col = blended_transform_factory(fig.transFigure, ax.transData)
    items = []
    for item in spec:
        if item[0] == 'row' and lookup.get(item[1], {}).get('estimate', '') == '':
            continue
        items.append(item)
    y, ys = 0.0, []
    for item in items:
        y -= .8 if item[0] == 'head' and ys else 0  # gap before a new group
        ys.append(y)
        y -= 1
    for item, y in zip(items, ys):
        if item[0] == 'head':
            ax.text(label_x - .004, y, item[1], transform=col, ha='left', va='center', fontsize=6.4,
                    weight='bold', color=SLATE)
            continue
        _, key, label, indent = item
        r = lookup[key]
        color, marker = STYLE.get(r['group'], STYLE['activation']) if r['group'] != 'last-prompt' else STYLE['activation']
        head = key in BOLD
        ax.errorbar(r['estimate'], y, xerr=[[r['estimate'] - r['low']], [r['high'] - r['estimate']]],
                    fmt=marker, color=color, ecolor=color, markersize=4.4 if head else 3.8,
                    capsize=1.8, linewidth=.9, zorder=3)
        ax.text(xlim[1] + .012, y, f"{r['estimate']:.2f}", ha='left', va='center', fontsize=6.8,
                color=GREY if r['group'] == 'control' else color, weight='bold' if head else 'normal')
        ax.text(label_x + .016 * indent, y, label, transform=col, ha='left', va='center',
                fontsize=6.5, weight='bold' if head else 'normal')
        if alarm_x is not None:
            alarm = ALARMS.get(key, '\u2013')
            ax.text(alarm_x, y, alarm, transform=col, ha='center', va='center', fontsize=6.6,
                    color=GREY if alarm in ('\u2013', 'never fires') else SLATE, weight='bold' if head else 'normal')
    top, bottom = ys[0] + .7, ys[-1] - .6
    ax.set(xlim=xlim, ylim=(bottom, top))
    ax.set_yticks([])
    ax.set_xticks([.3, .5, .7, .9])
    ax.spines['left'].set_visible(False)
    ax.axvline(.5, color=GREY, linestyle='--', linewidth=.8, zorder=0)
    ax.text(.5, top, 'chance', ha='center', va='bottom', fontsize=6, color=GREY)
    ax.grid(axis='x', alpha=.15)
    return col


def render(rows, output):
    style()
    lookup = {r['label']: r for r in rows}
    W, H = 6.5, 2.6
    fig = plt.figure(figsize=(W, H), facecolor='white')
    left = fig.add_axes([.375, .2, .19, .66])
    right = fig.add_axes([.71, .2, .27, .66])
    forest(fig, left, MAIN_ROWS, lookup, label_x=.016)
    left.set_xlabel('AUROC per call (0.5 = chance)', fontsize=6.8, labelpad=2)
    fig.text(.012, .955, '(a) Which call will give in?', weight='bold', fontsize=7.8)

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
        for (h0, x0, r0), (h1, x1, r1) in zip(pts, pts[1:]):  # join adjacent horizons only; skipped rungs leave a gap
            if used.index(h1) - used.index(h0) == 1:
                right.plot([x0, x1], [r0['estimate'], r1['estimate']], color=color, lw=.7, alpha=.45, zorder=2)
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
    fig.text(.575, .955, '(b) The nearer the act, the easier to predict', weight='bold', fontsize=7.6)
    handles = [Line2D([], [], marker=m, color=c, linestyle='', markersize=4, markeredgewidth=1, label=name,
                      markerfacecolor=c if filled else 'white')
               for name, m, c, filled, _ in SERIES_B.values()]
    right.legend(handles=handles, loc='upper left', bbox_to_anchor=(-.02, .96), ncol=1, frameon=False,
                 fontsize=6.1, handletextpad=.2, labelspacing=.35, borderaxespad=.2)

    for ext in ['png', 'pdf']:
        fig.savefig(output / f'figure3_streaming.{ext}', dpi=300, facecolor='white')
    plt.close(fig)
    return W, H


def render_appendix(rows, output):
    style()
    lookup = {r['label']: r for r in rows}
    W, H = 6.5, 2.5
    fig = plt.figure(figsize=(W, H), facecolor='white')
    ax = fig.add_axes([.36, .2, .3, .64])
    alarm_x = .82
    forest(fig, ax, APPX_ROWS, lookup, label_x=.016, alarm_x=alarm_x)
    ax.set_xlabel('AUROC per call (0.5 = chance)', fontsize=6.8, labelpad=2)
    fig.text(.012, .955, 'gpt-oss-20b: further checks on which call will leak', weight='bold', fontsize=7.8)
    fig.text(alarm_x, .905, 'Catch / false alarm', ha='center', va='bottom', fontsize=6.4, weight='bold')
    fig.text(alarm_x, .87, '(% leaks / % normal)', ha='center', va='bottom', fontsize=6, color=GREY)
    auroc_x = ax.transData.transform((1.012, 0))[0] / fig.bbox.width
    fig.text(auroc_x, .905, 'AUROC', ha='left', va='bottom', fontsize=6.4, weight='bold')
    fig.text(.012, .03, '* Separate probe trained on this label; one seed, reduced recipe.   '
             '\u2020 Scored on calls before the peer asks.', fontsize=6.2, color=GREY)
    for ext in ['png', 'pdf']:
        fig.savefig(output / f'figure3b_appendix_checks.{ext}', dpi=300, facecolor='white')
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
    (args.output_dir / 'figure3b_appendix_checks_caption.md').write_text(CAPTION_APPX)
    w, h = render(rows, args.output_dir)
    wa, ha = render_appendix(rows, args.output_dir)
    print(f'{len(rows)} saved estimates; Figure 3 {w} × {h} in; Figure 3b {wa} × {ha} in.')


if __name__ == '__main__':
    main()
