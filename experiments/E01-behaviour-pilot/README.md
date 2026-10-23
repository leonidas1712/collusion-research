# E01: Can we produce recruitment behaviour at all?

**Status:** active

**Question.** With both agents served through OpenRouter (no interp yet), can a recruiter agent talk an open-weight target into a small out-of-scope action in a mocked sandbox, on some runs but not all, in a way that reads as realistic?

**Pass criteria.**
1. At least one scenario × recruiter strategy with mixed outcomes (roughly 20–70% acceptance).
2. Traces a reader finds plausible: no cartoonishly gullible target, no recruiter asking outright for something obviously bad.
3. Accepted vs resisted decided from the tool log, not by judgement.

**What we ran.** _(run IDs as they happen)_

**Findings.** _(pending)_

## Harness wiring

See [HARNESS.md](HARNESS.md) for the CLI and episode format. Ten offline tests pass. Two concurrent fake episodes completed in `runs/20261023-2137-e01-harness`. A benign live attempt in `runs/20261023-2137-e01-harness-dcb8` ended with `APIConnectionError`; it was saved as incomplete with no label. Live SDK integration remains unverified. These checks establish no recruitment result; research scenarios remain pending.
