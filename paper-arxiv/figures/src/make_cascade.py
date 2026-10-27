"""Figure: leaking episodes caught vs refusing episodes halted, probe alone vs probe-then-text cascades (E12)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from style import CONTROL_COLOR, MODEL_COLORS, configure  # noqa: E402

RUN = ROOT / 'runs/20261027-2007-e12-cascade'


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    configure()
    curves = json.loads((RUN / 'results.json').read_text())['curves']
    fig, ax = plt.subplots(figsize=(4.5, 3.0))
    series = [('probe_alone', 'Probe alone, stricter threshold', '-', MODEL_COLORS['qwen']),
              ('jev_lenient', 'Probe then Jev', '--', CONTROL_COLOR),
              ('bow_lenient', 'Probe then bag-of-words', ':', 'black')]
    for key, label, style, color in series:
        xs, ys = zip(*curves[key])
        ax.step(xs, ys, where='post', linestyle=style, color=color, label=label)
    for t in (0.05, 0.10):
        ax.axvline(t, color='#bbbbbb', lw=0.6, zorder=0)
    ax.set_xlabel('Share of refusing episodes halted')
    ax.set_ylabel('Share of leaking episodes caught')
    ax.set_xlim(0, 0.6)
    ax.set_ylim(0, 1)
    ax.legend(loc='lower right', frameon=False)
    fig.tight_layout()
    out = HERE.parent / 'fig9_cascade.pdf'
    fig.savefig(out)
    fig.savefig(out.with_suffix('.png'), dpi=150)
    print(out)


if __name__ == '__main__':
    main()
