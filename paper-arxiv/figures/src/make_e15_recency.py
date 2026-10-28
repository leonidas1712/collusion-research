"""Figure: share of sharing calls over the frozen threshold by calls since the last read of the file, per rule and request timing (E15)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from style import LABEL_SIZE, configure, paper_number  # noqa: E402

RUN = ROOT / 'runs/20261028-1039-e15-giving-in-scaleup'
ARMS = [('FORBID', 'Forbid', 'Forbidden', '#000000', -.25),
        ('EARLY', 'Early', 'Permitted, asked at once', '#009E73', 0),
        ('LATE', 'Late', 'Permitted, asked late', '#CC79A7', .25)]
SMALL = 2  # points from this many calls or fewer are hollow and not joined
BINS = [('0', 'Zero'), ('1', 'One'), ('2', 'Two'), ('3+', 'Three')]


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    configure()
    recency = json.loads((RUN / 'results.json').read_text())['recency']
    fig, ax = plt.subplots(figsize=(4.5, 3.0))
    for arm, name, label, color, dx in ARMS:
        joined = []
        for i, (b, word) in enumerate(BINS):
            r = recency[arm][b]
            if not r['n']:
                joined.append(None)
                continue
            x, y = i + dx, r['share']
            lo, hi = r['wilson95']
            small = r['n'] <= SMALL
            ax.errorbar(x, y, yerr=[[y - max(lo, 0)], [hi - y]], color=color, marker='o', ms=3.5, capsize=2, lw=1,
                        mfc='white' if small else color, alpha=.7 if small else 1)
            ax.text(x, hi + .03, paper_number(f'eFifteen{name}Bin{word}Calls', r['n']), ha='center', va='bottom', fontsize=LABEL_SIZE - 1.5, color=color)
            joined.append(None if small else (x, y))
        for a, b in zip(joined, joined[1:]):
            if a and b:
                ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=.9, alpha=.6)
        ax.plot([], [], color=color, marker='o', ms=3.5, lw=.9, label=label)
    ax.set_xticks(range(len(BINS)), [b for b, _ in BINS])
    ax.set_xlim(-.45, len(BINS) - .55)
    ax.set_ylim(0, 1.15)
    ax.set_yticks([0, .25, .5, .75, 1], ['0%', '25%', '50%', '75%', '100%'])
    ax.set_xlabel('Calls since the last read of the file')
    ax.set_ylabel('Sharing calls over threshold')
    fig.legend(loc='upper center', ncol=3, frameon=False, fontsize=LABEL_SIZE - .5, handlelength=1.3, columnspacing=1.0)
    fig.tight_layout(rect=(0, 0, 1, .9))
    out = HERE.parent / 'fig_e15_recency.pdf'
    fig.savefig(out)
    fig.savefig(out.with_suffix('.png'), dpi=150)
    print(out)


if __name__ == '__main__':
    main()
