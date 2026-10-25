# Appendix H — Eventual-label details

*Draft for merge into Appendix H of `report/paper.md` after codex's review render. codex builds the per-layer AUROC curve and the near-term robustness table into `report/figures/`; this is the eventual-label prose that sits beside them. Numbers from `runs/20261025-1456-e05-all-data-main/report.md`; claude-2 cross-checks.*

## Eventual give-in is not predictable from a single step

Eventual give-in — whether the episode gives in at any later point — is essentially unreadable from one step. On held-out scenarios the probe scores within scenario × round AUROC 0.523 [0.486, 0.560], and pooled 0.488 [0.438, 0.537]; both intervals contain chance. A fixed-layer-32 probe is no better (pooled 0.512 [0.453, 0.567]). The strongest text monitor, the Jev forecaster with everything the target saw, reaches 0.577 [0.521, 0.628], only weakly above chance. On the same steps the near-term probe reaches 0.586 pooled and 0.579 held-out, so the signal is clearly stronger for proximity to the action than for the episode's eventual outcome.

Three checks read this as a property of the task, not of the probe:

- **Learning curve.** The eventual-label AUROC does not rise with training-set size, so more episodes of the same kind would not recover the signal. *[codex: the learning-curve points are in the robustness table/figure.]*
- **Per-layer.** No layer separates eventual outcome above chance; the eventual curve stays near 0.5 across all 64 layers, unlike the near-term curve. *[codex: per-layer AUROC figure.]*
- **Branching.** Resampling an episode from a shared prefix leads to different outcomes, so the eventual outcome is only partly settled at most steps and a single step cannot foretell it. This is the reason we lead with the near-term label. *[Branching source and the resample figure: claude-2 to confirm against the branching run.]*
