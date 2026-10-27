"""Figure: leaking episodes caught vs refusing episodes halted, probe alone vs probe-then-text cascades (E12)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from style import CONTROL_COLOR, LABEL_SIZE, MODEL_COLORS, configure, paper_number  # noqa: E402

RUN = ROOT / 'runs/20261027-2007-e12-cascade'


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    configure()
    results = json.loads((RUN / 'results.json').read_text())
    curves, targets = results['curves'], results['targets']
    fig, ax = plt.subplots(figsize=(4.5, 3.0))
    series = [('probe_alone', 'Probe alone, stricter threshold', '-', MODEL_COLORS['qwen']),
              ('jev_lenient', 'Probe then Jev', '--', CONTROL_COLOR),
              ('bow_lenient', 'Probe then bag-of-words', ':', 'black')]
    for key, label, style, color in series:
        xs, ys = zip(*curves[key])
        ax.step(xs, ys, where='post', linestyle=style, color=color, label=label)
    for t in (0.05, 0.10):
        ax.axvline(t, color='#bbbbbb', lw=0.6, zorder=0)
    # Leaking episodes caught at <=5% and <=10% of refusing episodes halted (the cascade table):
    # a marker at each chosen threshold, and the values in a small column over each target line.
    macros = {'probe_alone': 'cascadeProbeAlone', 'jev_lenient': 'cascadeJevLenient', 'bow_lenient': 'cascadeBowLenient'}
    box = dict(facecolor='white', edgecolor='none', pad=.6)
    for t, target, word in ((0.05, '5%', 'Five'), (0.10, '10%', 'Ten')):
        ax.text(t, .965, f'{target}', ha='center', va='center', fontsize=LABEL_SIZE, color='#444444', bbox=box)
        for row, (key, _, _, color) in enumerate(series):
            point = targets[target][key]
            assert point['refusing_rate'] <= t
            ax.plot(point['refusing_rate'], point['leaking_rate'], 'o', ms=4, color=color, zorder=4)
            ax.text(t, .90 - .06 * row, paper_number(macros[key] + word, point['leaking_rate']),
                    ha='center', va='center', fontsize=LABEL_SIZE, color=color, bbox=box)
    ax.text(.135, .965, 'of refusing episodes halted', ha='left', va='center', fontsize=LABEL_SIZE, color='#444444')
    ax.set_xlabel('Share of refusing episodes halted')
    ax.set_ylabel('Share of leaking episodes caught')
    ax.set_xlim(0, 0.6)
    ax.set_ylim(0, 1)
    ax.legend(loc='lower right', bbox_to_anchor=(1.0, 0.0), frameon=False, borderaxespad=.1, handlelength=1.8, fontsize=LABEL_SIZE)
    fig.tight_layout()
    out = HERE.parent / 'fig9_cascade.pdf'
    fig.savefig(out)
    fig.savefig(out.with_suffix('.png'), dpi=150)
    print(out)


if __name__ == '__main__':
    main()
