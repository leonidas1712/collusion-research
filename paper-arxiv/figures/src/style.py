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
