"""Figure: share of sharing calls over the frozen threshold by calls since the last read of the file, per rule and request timing (E15)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from style import LABEL_SIZE, configure, paper_number  # noqa: E402

RUN = ROOT / 'runs/20261028-1039-e15-giving-in-scaleup'
ARMS = [('FORBID', 'Forbid', 'Forbidden', '#000000', -.18),
        ('EARLY', 'Early', 'Permitted, asked at once', '#009E73', 0),
        ('LATE', 'Late', 'Permitted, asked late', '#CC79A7', .18)]
BINS = [('0', 'Zero'), ('1', 'One'), ('2', 'Two'), ('3+', 'Three')]


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    configure()
    recency = json.loads((RUN / 'results.json').read_text())['recency']
    fig, ax = plt.subplots(figsize=(4.5, 2.8))
    for arm, name, label, color, dx in ARMS:
        xs, ys = [], []
        for i, (b, word) in enumerate(BINS):
            r = recency[arm][b]
            x = i + dx
            xs.append(x)
            if not r['n']:
                ys.append(float('nan'))  # break the line at an empty bin
                continue
            ys.append(r['share'])
            lo, hi = r['wilson95']
            ax.errorbar(x, r['share'], yerr=[[r['share'] - max(lo, 0)], [hi - r['share']]], color=color, marker='o', ms=3.5, capsize=2, lw=1)
            ax.text(x, hi + .03, paper_number(f'eFifteen{name}Bin{word}Calls', r['n']), ha='center', va='bottom', fontsize=LABEL_SIZE - 1.5, color=color)
        ax.plot(xs, ys, color=color, lw=.9, alpha=.6, label=label)
    ax.set_xticks(range(len(BINS)), [b for b, _ in BINS])
    ax.set_xlim(-.45, len(BINS) - .55)
    ax.set_ylim(0, 1.15)
    ax.set_yticks([0, .25, .5, .75, 1], ['0%', '25%', '50%', '75%', '100%'])
    ax.set_xlabel('Calls since the last read of the file')
    ax.set_ylabel('Sharing calls over threshold')
    ax.legend(loc='lower left', frameon=False, fontsize=LABEL_SIZE, handlelength=1.5, borderaxespad=.1)
    fig.tight_layout()
    out = HERE.parent / 'fig_e15_recency.pdf'
    fig.savefig(out)
    fig.savefig(out.with_suffix('.png'), dpi=150)
    print(out)


if __name__ == '__main__':
    main()
