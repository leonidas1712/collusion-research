# Appendix C text items: scenario table columns and model choice

*Draft for merge into Appendix C of `report/paper.md` after codex's review render. The per-scenario give-in rates are already in the Appendix C table (moved from §4.1); these are the two new columns (incident type, protected value) and the model-choice table. Source: `experiments/E01-behaviour-pilot/SCENARIO_SPECS.md`, `docs/scenario_guidelines.md`, `docs/report_plan_outline.md`. claude-2 cross-checks against the specs.*

## Scenario table — new columns

Each scenario is grounded in a real incident type but does not copy its names, systems, or sequence (`docs/scenario_guidelines.md`). The protected value is a randomly generated fake.

| Scenario | Protected value | Grounded in |
|---|---|---|
| Deployment credential | A staging deploy token (credential) | The 2026 OpenAI–Hugging Face incident's credential use during task pursuit; a controlled extension in which a peer needs a target-held credential. |
| Dispatch integration code | A short integration code (code) | The same task-pursuit / shared-resource pattern; an engineering analogue, not a reported detail. |
| Handoff exception note | A free-text exception note (text) | As above. |
| Procurement reserve price | A reserve price (number) | As above. |
| Service capacity figure | A capacity figure (number) | As above. |
| Service rollout threshold | A rollout threshold (number) | As above. |

**[Cross-check, claude-2]** confirm the per-scenario `grounded_in` lines in `SCENARIO_SPECS.md`; the five additional scenarios share the incident's task-pursuit/shared-resource pattern as controlled analogues rather than each citing a distinct incident.

## Model choice

We chose Qwen3-32B for open weights, prior interpretability work on the family, clean tool use at full precision, and the ability to disable thinking (so the three monitor access levels are identical to the second target's Qwen-comparable levels). Candidates we tried and dropped:

| Candidate | Why dropped |
|---|---|
| IBM Granite (8B class) | Under an explicit rule it never shared deliberately (0 of 8) and only leaked incidentally inside refusals, giving no mixed outcomes to predict; softening the rule did not produce a mix. |
| Llama-3.3-70B | Did not open the file holding the value when its task did not require it, wasting episodes in the required-access design. |
| Various others | Tool-use failures, unusable thinking settings, or quantised-only serving at the sizes available. |

**[Cross-check, claude-2 / codex]** confirm the exact candidate list and the Granite / Llama counts against `EXPERIMENT_LOG.md`; the Granite 0/8 and the Llama "never opened the file" note are from `docs/scenario_guidelines.md`.
