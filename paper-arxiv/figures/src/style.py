"""Shared figure encoding; models use colors and detector types use shapes."""
MODEL_COLORS = {'qwen': '#0072B2', 'gpt_oss': '#D55E00'}
DETECTOR_MARKERS = {'activation': 'o', 'text': 's', 'rule': '^', 'control': 'D'}
CONTROL_COLOR = '#666666'


def configure():
    import matplotlib as mpl
    mpl.rcParams.update({
        'font.family': 'serif', 'font.serif': ['DejaVu Serif'],
        'font.size': 10, 'axes.labelsize': 10, 'axes.titlesize': 10,
        'xtick.labelsize': 9, 'ytick.labelsize': 9, 'legend.fontsize': 9,
        'pdf.fonttype': 42, 'ps.fonttype': 42,
        'axes.spines.top': False, 'axes.spines.right': False,
        'savefig.bbox': None, 'savefig.pad_inches': 0.04,
    })


def evidence_style(status):
    if status not in {'confirmed', 'exploratory'}:
        raise ValueError(status)
    return {'fillstyle': 'full' if status == 'confirmed' else 'none'}


# Value labels: at least ~7pt once figures are scaled to the 5.5in text width.
LABEL_SIZE = 8.5
_NUMBERS = None


def paper_number(macro, value=None, scale=1.0):
    """Return a number exactly as numbers.tex renders it; check it against the plotted value."""
    global _NUMBERS
    import re
    from pathlib import Path
    if _NUMBERS is None:
        text = (Path(__file__).resolve().parents[2] / 'numbers.tex').read_text()
        _NUMBERS = dict(re.findall(r'\\newcommand\{\\(\w+)\}\{([^{}]*)\}', text))
    shown = _NUMBERS[macro].replace(r'\%', '%')
    if value is not None:
        digits = shown.rstrip('%')
        decimals = len(digits.split('.')[1]) if '.' in digits else 0
        number = float(digits) / (100 if shown.endswith('%') else 1)
        tolerance = .5 * 10 ** -decimals / (100 if shown.endswith('%') else 1) + 1e-9
        assert abs(number - value * scale) <= tolerance, (macro, shown, value)
    return shown
