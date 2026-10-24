# Forced-continuation branching review

`branch.py` accepts a complete saved episode and a branch round `t`. It reconstructs the state at
the start of that round, then can sample `N` continuations of exactly `K` rounds. The default is
estimate-only. Model requests require an explicit `--execute` after the estimate is printed.

## Exactness checks

- Actor histories come from the exact saved request bodies at round `t`. Messages delivered during
  the parent version of round `t` are removed, leaving the start-of-round history.
- Channel events and tool events are retained only for rounds before `t`.
- Workspace files and environment state start from the saved scenario specification. Every earlier
  tool call is replayed through the scenario handler, and its result must exactly equal the recorded
  result. A mismatch aborts reconstruction.
- At `t = parent rounds + 1`, replayed files and environment state must also equal the saved final
  state.
- Target and peer model identifiers, temperature, token limit, reasoning settings, and pinned
  provider request options come from the parent episode settings.
- Branches do not early-stop after a forbidden action. Every complete branch runs all `K` rounds.

## Outputs

Each branch episode records the absolute parent path, parent episode id, branch round, branch index,
and requested continuation length. `summary.json` reports complete branches, the share with a first
forbidden action inside the window, and the absolute rounds of those first actions.

The selection mode stratifies candidates across held, give-in, and control parents and across early
and late branch points. Any point from a parent with a forbidden action is capped at that parent's
first-action round so the saved prefix does not already contain the outcome.

## Commands

```bash
# Estimate only (default)
python experiments/E01-behaviour-pilot/branch.py PARENT.json --round 8 --next-rounds 3 --branches 5

# Select approximately 50 points from run directories
python experiments/E01-behaviour-pilot/branch.py --select-from runs/MAIN_RUN --limit 50 --selection-output branch-points.json

# After review
python experiments/E01-behaviour-pilot/branch.py PARENT.json --round 8 --next-rounds 3 --branches 5 --execute
```
