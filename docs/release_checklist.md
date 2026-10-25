# Release checklist (submission and going public)

We keep this repo for the submission. It isn't copied to a fresh one, because the commit history and `EXPERIMENT_LOG.md` show what was done during the sprint. Tidy it in place, and tag the submitted commit.

## Before submission (Mon 26 Oct)

- [ ] **Pre-existing note** in README and report.
  - The sprint start is taken as Fri 23 Oct 00:00 AoE (= 12:00 UTC = 20:00 SGT); the page gives only dates and an AoE deadline.
  - Only one commit is before that: `a5bd6f93` (23 Oct 00:50 SGT), with planning docs, infra notes, the idea doc, related-work notes and a report skeleton. It contains no code.
  - The next commit, the run helper and E01 harness, is at 23 Oct 21:41 SGT.
  - Everything from the harness onwards is sprint work.
- [ ] **README:** a repo map; how to reproduce the headline (scripts and run folders, in order); what is not in git and how to regenerate it (activations on the Modal volume, monitor caches, prompt renders).
- [ ] **Tag** the submitted commit `apart-submission` and link the tag.
- [ ] **Dead ends:** list them in the README, or move them to `archive/`. Don't delete them; history is evidence.
- [ ] **Self-contained text pass:** remove the "because Leo…" remarks, Aboard task IDs and references to chat context from code, READMEs and docs; state the reason itself. `EXPERIMENT_LOG.md` stays as a dated lab notebook. Internal-only files (`AGENT_BRIEF.md`, `docs/overview.html`, `.claude/`) are either moved to `archive/internal/` or labelled internal in the README.
- [ ] **Report read cold:** a fresh agent with no project context reads the report and lists every term, step or reference it can't follow. Fix those.
- [ ] **Reproducibility table** (paper appendix and README):
  - **Target:** `qwen/qwen3-32b` via OpenRouter, pinned to DeepInfra with fp8 requested and no fallbacks. All 10,939 target calls were served by DeepInfra; the served quantization isn't reported back, so fp8 is the requested filter, not a verified fact.
  - **Peer:** `deepseek/deepseek-v4-flash`, same pinning (8,438 calls).
  - Temperature 0.7.
  - **Replay:** HF `Qwen/Qwen3-32B` at revision `9216db5781bf21249d130ec9da846c4624c16137`, bf16, A100-80GB on Modal, transformers version as pinned in `requirements-lock.txt`.
  - **Fidelity:** reply NLL about 0.23–0.25 and top-5 about 99.8%. This bounds the gap between the fp8-served and bf16-replayed model.
  - **Monitors:** model IDs, prompt hashes and caches in the run folders. Probe seeds 42/43/44; bootstrap seed 20261025.
- [ ] **Licence** file. MIT is suggested for code; data terms are a separate decision.

## Before making the repo public

- [ ] **Secret scan of the full history** with gitleaks or trufflehog.
  - A regex pass on 25 Oct found no API keys.
  - The only hits were GPT-5-nano encrypted-reasoning blobs in monitor caches. They're harmless, and they go anyway with the cache purge below.
- [ ] **Purge from history** with `git filter-repo --path ... --invert-paths`. This keeps commit dates (the hashes change), so keep the original as a private record.
  - Remove: `runs/*/diff.patch`, `runs/*/prompts/`, `runs/*/cache/`, `runs/*/tokenizer/`, `apart_sprint_raw.md`, `resources.md`. These are now untracked, but they're still in older commits.
  - Don't squash, because squashing loses the timestamps.
- [ ] **Personal paths:** about 1,000 tracked files contain `/Users/leo/...`, mostly run metadata. Leave them, or rewrite them in bulk.
- [ ] **Dual-use:** decide what peer prompts and tactic text to publish. Baseline prompts are needed for replication; the strongest tactic variants could be described in the report but held back. Record the choice in the dual-use appendix.
- [ ] **Data:** the episodes are in git (the transcripts dataset); activations are not. Optionally publish a summary table or a Hugging Face dataset.

## While working (habits)

- No secrets in code or logs. Keys stay in `.env` only.
- New run folders stay small in git. Big or regenerable outputs go under the ignored patterns in `.gitignore`.
- Use relative paths in new code.
- Stage selectively. Never use `git add -A`.
- Log decisions with real timestamps in `EXPERIMENT_LOG.md`. This is the record of what was done when.
