# Appendix A. Limitations and Dual-Use / Ethical Considerations

*Draft for merge into `report/paper.md` after codex's review render. Source: `docs/writeup_limitations.md`, `docs/report_plan_outline.md` §5. claude-2 cross-checks the counts.*

*What do these results not establish, and is it safe to publish what we release?*

## Limitations (ordered by how much each could change a headline)

1. **One model, one task template.** The results are one target (Qwen3-32B) on six scenarios built from a single task template, so the give-in rates and the predictability are specific to this setting, not a claim about agents in general. The second target (Appendix F) is a first test of transfer.
2. **Last-prompt-token activations only.** Probes read the residual stream at the last prompt token before each reply. If the decision forms within the reply, a last-token probe understates what is readable; a decision-token probe is future work.
3. **Near-term labels are post hoc.** The near-term label was defined after the eventual-label result was seen. The frozen confirmation set (collected and scored under a plan fixed in advance) guards against this, and is the only prospective test.
4. **Scenario imbalance and uneven drop-out.** The development scenario has more episodes than the five additional ones, and drop-out is uneven across scenarios (the target never read the value, API errors, or setup failures). Drop-out could bias a scenario toward targets that engage with the file. We report per-scenario counts (Appendix C) and a scenario-mean AUROC alongside the pooled one (Appendix H).
5. **A single automated judge** labels deliberate versus accidental disclosure (validated against hand labels on 36 of 40 give-ins, κ = 0.79), and the monitor score is anchored only at its ends rather than on a banded rubric.
6. **Pooled-CV fold mixing.** The pooled within-round metric compares scores across fitted folds, which can push baselines below chance; we report the fold-stratified sensitivity (Appendix H). Held-out scenario and the confirmation test are unaffected.
7. **A small stacking optimism** in the first-batch combination test: out-of-fold probe scores give a slight tilt toward "the probe adds value" (estimated ≈0.01). The frozen confirmation test has no such leak.
8. **The scoring window.** A give-in on the call right after the read leaves no eligible step and cannot be predicted from within the episode, and episodes that never read the value are dropped. More broadly, the window can be defined exactly only because the value arrives one known way (a file read); a general monitor would not know when the means arrived.
9. **Accidental disclosures count** as give-ins (the operator is harmed either way); a deliberate-only analysis is reported as a sensitivity check.
10. **Incident-framing caveat.** Our setup is a controlled analogue of the 2026 incident, not a reproduction. In the incident the leaked credentials came from the public internet and a shared board; here a peer recruits the target for a value held in the operator's own protected file. The claim is about predicting a peer-induced rule violation, whatever its surface, not about reproducing that incident.

## Dual-Use / Ethical Considerations

We publish everything and state the reasoning.

- **Synthetic setup.** Tools are mocked in memory; every protected value is a randomly generated fake; no real system, credential, or network resource is touched.
- **What we release.** All prompts (the recruiting and control peer prompts and the second-target configuration-block strategy), the monitor prompts, the scoring code, and the transcripts. Replication depends on them.
- **Why the uplift is low.** Persistent-request and persuasion tactics are already described in prior work (e.g. Colosseum, @nakamura2026). The configuration-block strategy is an instance of a known failure class — copying a whole block that contains a protected field — not a new attack, and it was seen only on small open-weight models in synthetic settings.
- **Defensive value.** A rule stated per field fails when a whole block is copied, so protected values should be filtered at the action, not only named in the prompt. We keep this recommendation: it turns the riskiest result into guidance for defenders.
- **Detection side.** "Eventual give-in is unpredictable from a single step" and "action-only monitors are blind before disclosure" are structural properties of monitoring, not evasion techniques.
