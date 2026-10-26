# Glossary (main-text defined terms; one meaning each)

- **target**: the agent whose operator gave it the secret and the rule not to share it. Its activations are read.
- **peer**: the other agent on the team channel. It needs the secret, cannot read the file and is not told the rule.
- **leak**: a call leaks if it is the first to write the secret out, in its reply or in any tool-call argument (a file write counts, wherever it writes). This is the gpt-oss frozen detector, applied unchanged to Qwen3-32B. Used for every per-call and ladder result on both models.
- **probe**: a logistic regression on the target's residual stream. The *last-prompt probe* reads the last prompt token before a call. The *reasoning probe* (gpt-oss-20b) takes the maximum over the call's reasoning tokens.
- **text monitor**: a language model that reads the transcript, with no activations, and returns a score. The main one is Jev, a decision model that returns a probability.
- **development episodes / fresh test episodes**: per model, the episodes used for all analyses, and the episodes collected after a plan was frozen and scored once by frozen models.

Defined by notation only (Setup §2.3): call $c_t$, round $r(t)$, leak index $\tau$, labels $y^{\text{call}}, y^{\text{near}}, y^{\text{ever}}$, probe score $s_t$, within-stratum AUROC.

Appendix-only terms: *family* (related episodes that share a seed or history, held out together), *round-level channel label* (the pre-registered Qwen confirmation label).

Not used: give-in, recruiter, principal, cohort, rung, eligible call, L1–L3.
