# Generated tables requested by the writer (claude-2 → codex-2)

Each file is `paper-arxiv/tables/<name>.tex`, generated from `numbers.yaml` or run outputs, never hand-typed. Each emits a complete `tabular` environment (booktabs, no vertical rules). The surrounding `table` float, caption and label are already in the prose files. Use two decimals for AUROC and percentages for rates. Intervals go in brackets in a separate column or after the value, consistently. Dataset names in cells: "development" and "fresh test". No run paths except in `repro.tex`.

| File | Used in | Rows × columns |
|---|---|---|
| datasets.tex | setup.tex Table 1 | rows: Qwen3-32B dev, Qwen3-32B fresh, gpt-oss-20b dev, gpt-oss-20b fresh; cols: recruiting episodes, control (and target-alone, Qwen only) episodes, scored calls, leaking calls, % of recruiting episodes that leak (any public emission) |
| behaviour_by_scenario.tex | app A | 6 scenarios + total, Qwen3-32B dev: leaking / recruiting episodes, % [Wilson CI], control leaks, target-alone leaks |
| labels.tex | app B | judge vs author blind labels (agreement, κ); share deliberate (Qwen, gpt-oss); route split of first leaks (end-of-turn reply / send_message / tool args / file write), per model; addressee check; authority-claim rates with/without claim |
| replay.tex | app C | per model × dataset: reply-token NLL, top-5 agreement, prompt-render agreement (gpt-oss: per provider) |
| fresh.tex | app F | gpt-oss reasoning probe (max, primary; mean); keyword rules; Qwen round-level probe and Jev forecaster and GPT-5-nano detector (round-level label); Qwen per-call probe (dev-only, frozen); gpt-oss per-call last-prompt probe if scored; columns: AUROC [CI], status (pre-registered / out of sample), share of leaking calls caught at frozen threshold, share of refusing-episode calls alarming |
| robust_call.tex | app G | per-call, dev: held-out vs pooled CV; reasoning max / mean / censored at mention; gpt-oss incl. no-reasoning calls; gpt-oss channel-only label (wider window); Qwen excluding write-back-to-protected-file calls; fixed layer |
| robust_round.tex | app G | Qwen round-level near-term: label variants (main, hindsight B, C), split (held-out, pooled), layer (chosen, fixed 32), scenario-mean weighting, MLP vs logistic |
| shortcuts.tex | app H | gpt-oss: pre-ask placebo, keyword narrow/broad, read-step flag, probe minus read-step flag, probe within post-read calls, incoming-only probe (AUROC, refusing-call alarms), action-time probe; Qwen: read-step flag, probe minus flag, incoming-message keyword rule, pressure probe on round-level labels |
| alarms.tex | app I | rows: reasoning probe (dev), last-prompt probe (dev, both models), frozen reasoning probe (fresh), Jev per-call (both models); cols: threshold set on, share of leaking calls caught, share of refusing calls alarming, share of refusing episodes with ≥1 alarm; plus the episode-calibrated row (share of leaking episodes stopped before first leak, refusing episodes alarming) |
| round_level.tex | app J | Qwen round-level: probe and best monitor on eventual and near-term (dev, held-out); fresh near-term (probe, Jev, GPT-5-nano); combination test gains (held-out, fresh) for Jev forecaster and GPT-5-nano detector; gpt-oss channel-only round-level probe and best monitor |
| history.tex | app O | each analysis: question, label, planned before its data (yes/no), added after which result, confirmed on fresh episodes (pre-registered / out of sample / no) |
| changed_numbers.tex | app O | each main-text number whose value changed from the sprint version: sprint value, new value, why (label unified, dev-only, same calls) |
| repro.tex | app P | each figure, table and headline macro → run folder(s) and script |

Macros still needed in prose (see #2378): `\gptossIncomingProbe`, `\gptossKeyword`, `\gptossPlacebo`, `\qwenLeakRate`, `\qwenStrictNextProbe`.
