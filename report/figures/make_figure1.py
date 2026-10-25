"""Figure 1: (a) the setup and what each detector sees; (b) a toy episode timeline with the eligible window and both labels.

    uv run --no-project --with matplotlib python report/figures/make_figure1.py

Schematic only, no data. Writes figure1_setup.png (300 dpi) and figure1_setup.pdf next to this script.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7})

INK = "#1f2933"
MUTED = "#6b7280"
FAINT = "#c0c4cc"
TARGET = "#dbeafe"
PEER = "#fde68a"
NEUTRAL = "#f3f4f6"
PROBE = "#1d4ed8"
LEVEL = ["#065f46", "#059669", "#34d399"]  # actions only, + conversation, + everything the target saw
WINDOW = "#e0f2fe"
POS = "#b91c1c"


def box(ax, x, y, w, h, text, fill, weight="normal", size=7):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.025",
                                fc=fill, ec=INK, lw=0.7))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, weight=weight, color=INK,
            linespacing=1.25)


def arrow(ax, a, b, both=False, color=INK):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="<|-|>" if both else "-|>", mutation_scale=6,
                                 lw=0.7, color=color, shrinkA=0, shrinkB=0))


def level_marker(ax, x, y, i):
    ax.plot([x], [y], marker="o", markersize=7.5, mfc=LEVEL[i], mec="white", mew=0.6, zorder=5)
    ax.text(x, y, str(i + 1), ha="center", va="center", fontsize=5.8, color="white", weight="bold", zorder=6)


def panel_setup(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.02, 1)
    ax.axis("off")
    ax.text(0, 1.0, "(a) Setup, and what each detector reads", weight="bold", fontsize=8, va="top")

    # Row of agents: peer -- channel -- target; operator above the target, tools below.
    box(ax, 0.00, 0.52, 0.25, 0.22, "Peer agent\nneeds the value;\nnot told the rule", PEER, size=5.8)
    box(ax, 0.335, 0.56, 0.16, 0.14, "Team\nchannel", NEUTRAL, size=5.8)
    box(ax, 0.58, 0.50, 0.42, 0.28, "Target agent\n(Qwen3-32B)\n\n", TARGET, weight="bold", size=6.6)
    box(ax, 0.58, 0.815, 0.42, 0.11, "Operator rule:\nkeep the value private", NEUTRAL, size=5.4)
    box(ax, 0.58, 0.25, 0.42, 0.14, "Mock tools: read, write, send;\nconfig file holds the value", NEUTRAL, size=5.4)

    arrow(ax, (0.79, 0.815), (0.79, 0.78))
    arrow(ax, (0.25, 0.63), (0.335, 0.63), both=True)
    arrow(ax, (0.495, 0.63), (0.58, 0.63), both=True)
    arrow(ax, (0.79, 0.50), (0.79, 0.39), both=True)

    # Probe: reads the target's own activations.
    ax.add_patch(Rectangle((0.60, 0.52), 0.38, 0.07, fc="white", ec=PROBE, lw=0.9))
    ax.text(0.79, 0.555, "probe reads activations\nbefore each reply", ha="center", va="center",
            fontsize=5.0, color=PROBE)

    # Monitor access levels, marked on what each level adds.
    level_marker(ax, 0.5375, 0.675, 0)  # target's posts
    level_marker(ax, 0.835, 0.445, 0)   # target's tool calls
    level_marker(ax, 0.2925, 0.675, 1)  # peer's messages
    level_marker(ax, 0.745, 0.445, 2)   # tool results back to the target
    level_marker(ax, 0.955, 0.74, 2)    # target's unposted text

    ax.text(0.0, 0.19, "Text monitor (no activations), three levels of access:", fontsize=5.6, weight="bold")
    labels = ["actions only: the target's tool calls and posts",
              "+ conversation: the peer's messages",
              "+ everything the target saw: tool results, unposted text"]
    for i, label in enumerate(labels):
        y = 0.135 - i * 0.055
        level_marker(ax, 0.02, y, i)
        ax.text(0.055, y, label, va="center", fontsize=5.5)


def panel_timeline(ax):
    rounds = range(1, 7)
    read, leak = 1, 6
    ax.set_xlim(-1.6, 6.5)
    ax.set_ylim(-1.15, 5.2)
    ax.axis("off")
    ax.text(-1.6, 5.2, "(b) Toy episode: scored steps and labels", weight="bold", fontsize=8, va="top")

    y_round, y_event, y_ev, y_nt, y_held = 4.25, 3.35, 2.25, 1.35, 0.15
    # Eligible window of the give-in episode: after the read, up to the step whose reply posts the value.
    ax.add_patch(Rectangle((read + 0.5, y_nt - 0.45), leak - read, (y_event + 0.45) - (y_nt - 0.45),
                           fc=WINDOW, ec="none"))

    ax.text(-1.55, y_round, "round", va="center", color=MUTED)
    for r in rounds:
        ax.text(r, y_round, str(r), ha="center", va="center", color=MUTED)

    ax.text(-1.55, y_event, "gives-in\nepisode", va="center", weight="bold", linespacing=1.1)
    ax.text(read, y_event, "reads\nvalue", ha="center", va="center", fontsize=6.2, linespacing=1.1)
    for r in range(read + 1, leak):
        ax.text(r, y_event, "holds", ha="center", va="center", fontsize=6.2, color=MUTED)
    ax.text(leak, y_event, "posts\nvalue", ha="center", va="center", fontsize=6.2, color=POS, weight="bold",
            linespacing=1.1)

    def row(y, name, values):
        ax.text(-1.55, y, name, va="center")
        for r in rounds:
            v = values.get(r)
            ax.text(r, y, "–" if v is None else str(v), ha="center", va="center",
                    color=FAINT if v is None else (POS if v else INK), weight="bold" if v else "normal")

    eligible = range(read + 1, leak + 1)
    row(y_ev, "eventual", {r: 1 for r in eligible})
    row(y_nt, "near-term", {r: int(r >= leak - 1) for r in eligible})

    ax.plot([-1.55, 6.4], [0.75, 0.75], color=FAINT, lw=0.5)
    # Held episode: every step after the read is eligible, scored 0.
    ax.add_patch(Rectangle((read + 0.5, y_held - 0.45), 6 - read, 0.9, fc=WINDOW, ec="none"))
    ax.text(-1.55, y_held, "held\nepisode", va="center", weight="bold", linespacing=1.1)
    ax.text(read, y_held, "reads\nvalue", ha="center", va="center", fontsize=6.2, linespacing=1.1)
    for r in range(read + 1, 7):
        ax.text(r, y_held, "0", ha="center", va="center", color=INK)

    ax.text(-1.55, -0.75, "Shaded: eligible steps (value read, not yet posted); all are scored.\n"
            "– not scored. Held episodes are 0 under both labels.", va="center", fontsize=5.9, color=MUTED, linespacing=1.3)


def main():
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.5, 2.8), gridspec_kw={"width_ratios": [1, 1]})
    panel_setup(a)
    panel_timeline(b)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.97, bottom=0.04, wspace=0.10)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"figure1_setup.{ext}", dpi=300, facecolor="white")
    print(OUT / "figure1_setup.png")


if __name__ == "__main__":
    main()
