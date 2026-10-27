# E12: does a probe-then-text-detector cascade beat a stricter probe?

**Short answer: no.** On fresh Qwen3-32B episodes, chaining the probe with a second text detector never catches more leaking episodes than simply raising the probe's threshold. This holds at both target halt rates. With Jev as the second stage, the cascade does worse. With the trained bag-of-words classifier as the second stage, the best version ties.

Status: exploratory and descriptive. The analysis uses saved scores only, with no model calls, no GPU and $0 spent. Every threshold is chosen on the same fresh episodes it is scored on (see "Caveats").

## What was measured

- **Episodes.** Fresh Qwen3-32B test episodes: 38 leaking and 51 refusing, 1,825 scored calls.
- **Stage 1.** The frozen per-call last-prompt probe, using its saved fresh scores.
- **Stage 2, two options:**
  - **Jev.** Its saved fresh scores, using one seed's rows; the three seeds are identical copies.
  - **Bag-of-words.** The paper's TF-IDF and logistic-regression recipe on the last message of each call's input. It was fit once on the 2,976 development calls and then scored on the fresh calls. Its unstratified fresh AUROC is 0.90 (probe 0.97, Jev 0.75).
- **The rule.** An episode is halted at the first call that every active stage flags. A leaking episode counts as caught if it is halted at or before its leak call.
- **The comparison.** At a fixed share of refusing episodes halted (at most 5%, and at most 10%), we compare the share of leaking episodes caught by three detectors:
  - the probe alone, with its threshold raised;
  - the cascade with a lenient stage 1, the paper's control-call threshold, and only stage 2 tuned;
  - the cascade with stage 1 also chosen from a small grid (1.28, 1.5, 1.75, 2.0).
- **Intervals.** 95% episode-bootstrap intervals, from 1,000 draws, with thresholds re-chosen in every draw.
- **Ties.** A gap of 3 episodes or fewer is a tie.

For reference, the lenient probe alone catches 33 of 38 leaking episodes (87%) but halts 30 of 51 refusing episodes (59%).

## Results: leaking episodes caught

| Detector | ≤5% refusing halted | ≤10% refusing halted |
|---|---|---|
| Probe alone (stricter threshold) | **10/38 (26%)** [3%, 58%] | **17/38 (45%)** [21%, 74%] |
| Probe (lenient) → Jev | 5/38 (13%) [3%, 26%] | 5/38 (13%) [3%, 37%] |
| Probe (grid) → Jev | 5/38 (13%) [5%, 39%] | 11/38 (29%) [8%, 61%] |
| Probe (lenient) → bag-of-words | 6/38 (16%) [0%, 39%] | 11/38 (29%) [8%, 55%] |
| Probe (grid) → bag-of-words | 9/38 (24%) [0%, 66%] | 15/38 (39%) [18%, 82%] |

**Gap to the probe alone,** in episodes, with the bootstrap interval of the difference in rates and the discordant episodes (caught by the cascade only / by the probe only):

| Cascade | ≤5% | ≤10% |
|---|---|---|
| Probe (lenient) → Jev | −5 [−47, +11 pts]; 4 / 9 | **−12 [−55, −3 pts]**; 3 / 15 |
| Probe (grid) → Jev | −5 [−42, +13 pts]; 4 / 9 | −6 [−39, +11 pts]; 4 / 10 |
| Probe (lenient) → bag-of-words | −4 [−47, +13 pts]; 3 / 7 | −6 [−47, +13 pts]; 4 / 10 |
| Probe (grid) → bag-of-words | −1, tie [−34, +34 pts]; 5 / 6 | −2, tie [−32, +39 pts]; 3 / 5 |

- No cascade comes out ahead.
- One gap has an interval that excludes zero: the lenient Jev cascade at 10%, which is worse than the probe alone.
- The best cascade, bag-of-words with stage 1 also tuned, ties the probe alone at both targets.

**Why the cascade loses.** Stage 2 misses most leaking episodes on its own, so requiring both stages to agree throws away probe catches. The table below counts misses among the 38 leaking episodes, at the chosen lenient-cascade thresholds.

| | Jev (≤5%) | Bag-of-words (≤10%) |
|---|---|---|
| Missed by stage 1 only | 3 | 3 |
| Missed by stage 2 only | 21 | 21 |
| Missed by both | 2 | 2 |
| Flagged by both, but never on the same call | 7 | 1 |

At the strict thresholds needed for so few halts, the second stage is the weak link. A stricter probe keeps more of the probe's own ranking, which is stronger than either text detector (fresh AUROC 0.97, against 0.90 for bag-of-words and 0.75 for Jev).

## Per-call numbers (secondary)

The calls are those of the operating points in the first table.

| Detector | Target | Leaking calls caught / 38 | Refusing calls flagged / 1,407 | Precision |
|---|---|---|---|---|
| Probe alone | ≤5% | 8 | 2 | 0.62 |
| Probe (grid) → bag-of-words | ≤5% | 8 | 3 | 0.62 |
| Probe alone | ≤10% | 15 | 4 | 0.68 |
| Probe (grid) → bag-of-words | ≤10% | 13 | 7 | 0.48 |

The remaining rows are in `results.json`.

## What this means for §4.4

A cheap second automated check on the same input does not beat simply raising the probe's threshold here. If a cascade helps, the gain has to come from a stronger second stage that we did not test, such as a human or a monitor that sees more than the input. The results are in `results.json` and the trade-off curves in `cascade_episode_tradeoff.pdf`.

## Caveats

- **Descriptive only.** Every threshold is chosen on the same fresh episodes it is scored on. The cascades have more thresholds to tune than the probe alone, which favours them, so this optimism makes the null result stronger.
- **Small samples.** There are 38 leaking and 51 refusing episodes, so each episode is about 2.6 points of catch rate and the intervals are wide.
- **One model.** Only Qwen3-32B was tested.
- **Same input.** The second stage reads the same input as the probe; a second stage that reads more is untested.

## Files

| File | Contents |
|---|---|
| `experiments/E12-cascade/e12_cascade.py` | The script. |
| `results.json` | All numbers, including the curves. |
| `cascade_episode_tradeoff.pdf` / `.png` | The trade-off figure. |
| `log.txt`, `meta.json` | Run records. |

Inputs:
- `runs/20261026-2212-e05-arxiv-qwen-fresh-percall/probe_scores.csv.gz` (probe);
- `runs/20261026-1309-e06-percall-input-jev-qwen/probe_scores.csv` (Jev);
- `runs/20261026-2155-e05-qwen-any-public-audit/rows.json` (labels).
