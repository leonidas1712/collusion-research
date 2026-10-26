# Macro requests from appendix/behaviour.tex (helper writer)

Every value below is proposed and needs verification. All come from Qwen3-32B recruiting episodes in `report/figures/appendix_g_coverage.csv`, cross-checked by `runs/20261026-0157-e03-paper-screen-table-audit`. Where a value is a sum of cells, the helper added the cells by hand, so codex-2 must confirm those. Rates use `format: percent`; counts use `format: integer`.

| Macro | Value | Source cells |
|---|---|---|
| `\screenRuleBaseRate` / `\screenRuleBaseN` | 40% / 10 | Rule strength "consequence", deploy-token, waves 1+2 summed (1/4 + 3/6) |
| `\screenRuleLoggedRate` / `\screenRuleLoggedN` | 66.67% / 12 | "consequence_logged", waves 1+2 summed (3/5 + 5/7) |
| `\screenPlainRate` / `\screenPlainN` | 43.33% / 30 | T0, deploy-token v1 reference (13/30) |
| `\screenTacticMinRate` / `\screenTacticMaxRate` | 0% / 50% | v1 tactic screen T1–T7: T6 is 0/4, T2 and T5 are 3/6, T7 is 2/4 |
| `\screenTacticMinN` / `\screenTacticMaxN` | 4 / 6 | same cells |
| `\screenStakeNoneRate` / `\screenStakeNoneN` | 44.44% / 9 | own-stake screen, "no own stake", four scenarios summed (0/2, 0/1, 1/2, 3/4) |
| `\screenStakeOwnRate` / `\screenStakeOwnN` | 63.64% / 11 | "own stake", four scenarios summed (2/3, 2/2, 1/3, 2/3) |
| `\screenThinkingRate` / `\screenThinkingN` | 12.5% / 8 | thinking on, T0 (1/8) |
| `\screenTwoPeersRate` / `\screenTwoPeersN` | 28.57% / 7 | two-peer screen (2/7) |
| `\screenAwareNoRate` / `\screenAwareNoN` | 40.32% / 124 | awareness audit, qwen3-32b, not flagged (50/124) |
| `\screenAwareYesRate` / `\screenAwareYesN` | 50% / 2 | awareness audit, qwen3-32b, flagged (1/2) |

Until a macro is in the registry, it falls back to `\texttt{pending}` through `\providecommand`. Once the registry covers them, delete the fallback block at the top of `behaviour.tex`.
