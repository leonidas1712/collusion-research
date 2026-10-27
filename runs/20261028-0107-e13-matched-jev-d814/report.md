# E13: Jev at the same share of calls flagged as the probe

This analysis uses saved scores only, with no model calls, no GPU and no refitting. Script: `experiments/E13-matched-jev/matched_jev.py`.

**The rule.** The probe keeps its saved threshold, which was set on control calls. Jev's threshold is the lowest cut (score > cut) that flags no larger share of calls in refusing episodes than the probe does.

**Intervals.** 95% intervals come from 1,000 episode-bootstrap draws, resampling leaking and refusing episodes separately. Jev's cut is re-matched in every draw.

| Cohort | Probe: refusing calls flagged | Probe: leaking calls caught | Jev cut | Jev: refusing calls flagged | Jev: leaking calls caught [95% CI] |
|---|---|---|---|---|---|
| Qwen3-32B test (38 leaking, 1,407 refusing calls) | 5.5% (77) | 82% (31/38) | 0.03 | 4.8% (68) | 26% (10/38) [8%, 39%] |
| gpt-oss-20b development (121 leaking, 1,665 refusing calls; probe averaged over three seeds) | 1.6% | 56% | 0.50 | 1.6% (26) | 7% (8/121) [1%, 12%] |

This replaces the earlier Jev operating point (68% caught, 29% of refusing calls flagged on the Qwen test episodes). That point used Jev's own saved cutoff, which:
- differs by fold;
- was partly set on test controls;
- is coarse, effectively "score > 0".

The curves for the figure are in `runs/20261028-0120-e13-alarm-tradeoffs-matched/`. They use the same probe curves as before; Jev is swept over one global cut.
