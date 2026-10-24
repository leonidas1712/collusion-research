# Existing-trace label judge

`judge_labels.py` judges stored episodes, without generating agent interactions. It supports GPT-6 Luna Decisions, Jev 1.14, and a structured-output GPT-5 Nano fallback. Luna was used for the initial validation; the other adapters have not been live-tested.

```sh
uv run python experiments/E01-behaviour-pilot/judge_labels.py --dry-run
uv run python experiments/E01-behaviour-pilot/judge_labels.py
uv run python experiments/E01-behaviour-pilot/judge_labels.py --run runs/RUN_ID
uv run python experiments/E01-behaviour-pilot/judge_labels.py --report-only --run runs/RUN_ID
```

Use `--model typesafe/jev-1.14` or `--model openai/gpt-5-nano` to select another model. Reuse `--run` to retain the same $0.30 ledger; new comparisons must not silently reset a task's budget. Requests are sequential, with no SDK retry loop. Before each request the ledger reserves a conservative serialized-input byte bound plus framing and capped output. Actual returned cost settles it; missing costs and failed requests retain reservations. The request and response, including probabilities and served version, are retained. The budget limits API inference charges, not existing credit-purchase fees.

The references in `judge_reference.json` are partial labels extracted from existing annotation notes by a separate agent that did not view judge outputs or transcripts. The judge receives neither those notes nor existing heuristic intent/policy labels. Read `JUDGE_REFERENCE.md` for coverage and ambiguous cases. An omitted reference is not a negative. First-publication manner, policy mention, false completed-action claims, authority impersonation, and overlapping held behaviors have different evidence scopes; definitions are visible in the request questions.

Private-file access and exposure eligibility use code. The semantic judge sees full channel messages and the tool ledger, including failed calls. Its completed-action classification can still be wrong, and the tool ledger lacks within-round message ordering. Typed decisions provide no evidence spans or written reasoning; audit the retained inputs. No judge label overwrites the episode's existing labels.

Initial validation: `runs/20261024-1710-e01-label-judge/report.md`. Thirty-five notes match the specified four run groups (41 notes exist overall). Initial path resolution failed before an API request; it was corrected and resumed, with the prior failed metadata retained in `resume_history.json`. Nine no-access/non-sharing episodes were rejudged to include held behaviors; earlier answers are archived. Total billed cost, including these repeats: $0.0211935.

## Full labeling and shared cap

`--all-complete --join-labels` selects complete, non-fake deploy-token episodes and joins results under `label.semantic_judge`, preserving all heuristic fields. `score_episode` carries that namespace through rescoring. Use `--budget-ledger PATH --budget-cap .50` to share a sequential ledger across comparison and full labeling; the current ledger includes the original Luna validation cost as an explicit carryover. Resume after an in-flight batch finishes to collect newly completed episodes. Never run two processes against the same ledger concurrently.

Jev/Luna comparison is in `runs/20261024-1710-e01-label-judge/comparison.md`. Luna was selected because it matched one extra supported authority-impersonation reference; this small sparse comparison does not establish broad superiority. Per-turn label proposals are in `PER_TURN_LABEL_PROPOSALS.md`; none have been run.
