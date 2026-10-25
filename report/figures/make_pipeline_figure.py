"""Appendix figure: the experimental pipeline, from collected episodes to reported numbers, with counts at each stage.

    uv run --no-project --with matplotlib python report/figures/make_pipeline_figure.py

Schematic. Every count is copied from the dataset and run summaries named in COUNTS below; check them there
before changing anything. Writes pipeline.png (300 dpi) and pipeline.pdf next to this script.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 6})

# Sources (repo-relative):
#   combined step table: runs/20261025-1026-e05-replay3-data-1d95 (summary.json, rows.jsonl)
#   replay fidelity: runs/20261025-0339-e02-replay2-results/report.md, runs/20261025-0923-e02-replay3-completion/summary.json
#   probe recipe: runs/20261025-1456-e05-all-data-main/report.md
#   monitor runs: runs/20261025-0147-e06-monitor-main, runs/20261025-0841-e06-monitor-main-balanced (budget.json)
#   confirmation: runs/20261025-1030-e06-confirmation/report.md
COUNTS = {
    "episodes": ("268 episodes: 187 recruiting, 55 control, 26 alone",
                 "129 episodes: 110 recruiting, 19 control"),
    "gave_in": ("63 kept recruiting episodes gave in", "38 gave in"),
    "kept": ("230 kept, 38 dropped", "108 kept, 21 dropped"),
    "steps": ("4,184 eligible steps", "2,220 eligible steps"),
    "requests": ("6,003 target requests", "3,112 target requests"),
    "fidelity": ("reply NLL 0.249, top-5 99.79%", "reply NLL 0.227, top-5 99.82%"),
}

INK = "#1f2933"
MUTED = "#6b7280"
STAGE = "#f3f4f6"
PROBE = "#dbeafe"
MONITOR = "#d1fae5"
SCORE = "#fef3c7"
LANE2 = "#9ca3af"


def box(ax, x, y, w, h, title, lines, fill, edge=INK, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012",
                                fc=fill, ec=edge, lw=0.7, linestyle=ls))
    ax.text(x + 0.012, y + h - 0.012, title, ha="left", va="top", fontsize=6.4, weight="bold", color=INK)
    ax.text(x + 0.012, y + h - 0.034, "\n".join(lines), ha="left", va="top", fontsize=5.6, color=INK,
            linespacing=1.35)


def down(ax, x, y0, y1):
    ax.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="-|>", mutation_scale=6, lw=0.7, color=INK,
                                 shrinkA=0, shrinkB=0))


def merge(ax, xs_from, y_from, xs_to, y_to):
    """Lines down from each source into one bar, then arrows down to each target."""
    ybar = (y_from + y_to) / 2
    for xf in xs_from:
        ax.plot([xf, xf], [y_from, ybar], color=INK, lw=0.7)
    ax.plot([min(xs_from + xs_to), max(xs_from + xs_to)], [ybar, ybar], color=INK, lw=0.7)
    for xt in xs_to:
        down(ax, xt, ybar, y_to)


def main():
    fig = plt.figure(figsize=(6.5, 5.9))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    first, new = 0, 1
    c = COUNTS
    x, w = 0.02, 0.71  # main lane
    h, gap = 0.105, 0.03
    top = 0.95
    ys = [top - h - i * (h + gap) for i in range(4)]

    ax.text(x, 0.99, "Qwen3-32B (thinking off)", fontsize=7.2, weight="bold", va="top")
    ax.text(x + w, 0.99, "counts: first data batch  |  new-episode set", fontsize=5.8, color=MUTED,
            va="top", ha="right")

    box(ax, x, ys[0], w, h, "1  Collect episodes (API)",
        ["Peer DeepSeek-V4-Flash; target Qwen3-32B, temperature 0.7, one pinned provider; up to 20 rounds.",
         "Six scenarios in the first data batch, five in the new-episode set. Out: transcripts and tool logs.",
         f"{c['episodes'][first]}  |  {c['episodes'][new]}"], STAGE)
    box(ax, x, ys[1], w, h, "2  Label outcomes",
        ["A rule on the tool log finds the first forbidden action and its round (the complete value in a",
         "channel post or a new file). A decision-model judge marks each give-in deliberate or accidental.",
         f"Out: one label per episode. {c['gave_in'][first]}  |  {c['gave_in'][new]}"], STAGE)
    box(ax, x, ys[2], w, h, "3  Select eligible steps",
        ["Keep steps after the protected value is read and before it is disclosed. Drop episodes that are",
         "incomplete, never read the value or fail the ordinary task, or have no step in that window.",
         f"{c['kept'][first]}; {c['steps'][first]}  |  {c['kept'][new]}; {c['steps'][new]}"], STAGE)
    box(ax, x, ys[3], w, h, "4  GPU replay",
        ["Each target request runs once through the open weights (bf16, pinned revision 9216db5, A100-80GB).",
         "All 64 decoder-layer outputs saved at the last prompt token; fidelity scored on the actual replies.",
         f"{c['requests'][first]}, {c['fidelity'][first]}  |  {c['requests'][new]}, {c['fidelity'][new]}"], STAGE)
    for i in range(3):
        down(ax, x + w / 2, ys[i], ys[i + 1] + h)

    bw = (w - 0.02) / 2
    xl, xr = x + bw / 2, x + bw + 0.02 + bw / 2
    hb = 0.135
    yb = ys[3] - gap - hb
    box(ax, x, yb, bw, hb, "5  Train probes",
        ["Logistic regression on one layer's 5,120-", "dim vector; layer picked from 17 inside each",
         "training fold; families kept apart; held-out-", "scenario rotation; seeds 42, 43, 44.",
         "Recruiting steps: 2,910  |  1,787."], PROBE)
    box(ax, x + bw + 0.02, yb, bw, hb, "6  Run text monitors",
        ["Jev, Luna Decisions, GPT-5-nano; 3 access", "levels x 2 questions (detect, forecast).",
         "First batch: all 18 setups, all 4,184 steps.", "New-episode set: 8 setups fixed in advance,",
         "all 2,220 steps. The probe's steps exactly."], MONITOR)
    merge(ax, [x + w / 2], ys[3], [xl, xr], yb + hb)

    h7 = 0.11
    y7 = yb - gap - h7
    box(ax, x, y7, bw, h7, "7  Score (all data)",
        ["Within scenario x round AUROC; 1,000", "family-bootstrap resamples; combination test.",
         "6,404 steps from 338 episodes.", "Out: Figure 2 and the main tables."], SCORE)
    box(ax, x + bw + 0.02, y7, bw, h7, "8  Confirmation (new-episode set)",
        ["Probe and combination models trained on the", "first data batch only, frozen, scored once.",
         "1,787 recruiting steps (82 positive), 89 episodes.", "Out: the confirmation numbers."], SCORE)
    merge(ax, [xl, xr], yb, [xl, xr], y7 + h7)

    # Second lane, reserved: never merged with the first.
    lx, lw_ = 0.765, 0.215
    ax.text(lx, 0.99, "gpt-oss-20b", fontsize=7.2, weight="bold", va="top", color=INK)
    ax.add_patch(FancyBboxPatch((lx, y7), lw_, top - y7, boxstyle="round,pad=0,rounding_size=0.012",
                                fc="#fafafa", ec=LANE2, lw=0.8, linestyle=(0, (3, 2))))
    lane = [
        ("Same stages 1-8", "with its own counts;", "never pooled with Qwen3-32B."),
        ("1  Collect", "peer DeepSeek-V4-Pro,", "delayed whole-block ask;", "300 recruiting, 60 control"),
        ("2  Label", "channel give-ins: 128/300"),
        ("3  Eligible steps", "after the ask: 2,059 steps,", "238 episodes; pre-ask", "placebo: 1,141 steps"),
        ("4  Replay", "6,985 requests, all verified;", "24 layers saved; reply NLL", "0.41, top-5 99.0% (main", "provider, 6,672 requests)"),
        ("5-8  Score", "near-term positives: 148;", "probes and the same", "monitors, plus a", "reasoning level"),
    ]
    yy = top - 0.02
    for block in lane:
        ax.text(lx + 0.01, yy, block[0], fontsize=5.9, weight="bold", va="top", color=INK)
        ax.text(lx + 0.01, yy - 0.025, "\n".join(block[1:]), fontsize=5.4, va="top", color=INK, linespacing=1.3)
        yy -= 0.03 + 0.024 * len(block[1:]) + 0.012

    fig.savefig(OUT / "pipeline.png", dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(OUT / "pipeline.pdf", facecolor="white", bbox_inches="tight", pad_inches=0.04)
    print(OUT / "pipeline.png")


if __name__ == "__main__":
    main()
