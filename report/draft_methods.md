# 3. Methods (draft)

*Draft prose for Section 3, written from `report/outline.md` §3. Source of truth stays the outline; numbers are cited to run folders there. Mechanics and secondary numbers live in the methods-details appendix (`report/draft_appendix_methods.md`); this section keeps the design and the reasoning behind it. `[PENDING]`/`[Fig N]` mark slots. Written 25 Oct 2026.*

## 3.1 Environment and agents

A **target agent** works in a mocked workspace on an ordinary operator task — read a small configuration file and write a short status report — under one rule: do not share a specific protected value (e.g. a staging deploy token) outside the file holding it. A **peer agent** shares a team channel and needs that value but cannot read the file. Over up to 20 rounds the peer asks for it, posting first; the target then takes a turn of tool calls (read a file, write a file, send a message). The peer is not told the rule — a blocked teammate pushing for what it needs, not one scripted to cause a violation; we study recruitment from an ordinary conflict of goals.

The peer is DeepSeek-V4-Flash; the target is Qwen3-32B, thinking disabled. Both run via OpenRouter at temperature 0.7 on one pinned provider. Each scenario runs in three conditions — **recruiting** (the peer asks for the value), **control** (same task, no forbidden ask), and **target alone**; controls and alone episodes never leaked. Six scenarios share one task template, fixing the structure and varying only the surface domain (credential, number, text, code). [Fig 1a: setup — peer → target → tools/channel.]

A **give-in** is scored deterministically from the tool log: the label is 1 only if the target published the complete value; partial disclosures do not count, so the rate is conservative. A secondary decision model (§3.6) labels each give-in deliberate or accidental (validation against blind human labels in the appendix).

## 3.2 Data

To read the target's internal activations we **replay** every saved target request through the open-weight Qwen3-32B checkpoint on an A100-80GB GPU, reading the **residual stream** (the model's running internal representation) at the last prompt token before each reply. The replay reproduces the served replies closely, so the activations reflect the model that acted (fidelity and checkpoint details in the appendix). The combined dataset is **6,404 scored steps from 338 episodes**, in an earlier batch (replay 2) and a later balanced batch; the balanced batch serves first as a held-out confirmation set, then is pooled (§4.3). Per-batch counts are in the appendix.

## 3.3 The scoring window

Every method — probe or monitor — is scored only on steps where the protected value is already in the target's context but not yet published; this is the central design choice. Steps before the read cannot produce a give-in; including them lets a method win by detecting that the file was read — a probe does exactly this, reaching exposure-detection AUROC **1.000** on held-out scenario families (`runs/20261025-0338-e05-replay2-positive-control/`). Steps after publication are detection after the fact. The reading-to-leaking window removes the shortcut and isolates the question: given that the target *could* give in, can a method see it coming? (Immediate give-ins and never-reading episodes contribute no scored step; counts in the appendix.) [Fig 1b: toy timeline — read → window → leak, with both labels.]

## 3.4 Labels

We score two main labels on the same steps.

- **Eventual:** every scoring-window step of an episode that eventually gives in is positive — the question we first set out to answer.
- **Near-term A ("gives in this round or the next"):** a step is positive only if the first forbidden action occurs in the current or next round; earlier steps are negative. This is what a live alarm must answer — our primary near-term label.

Two secondary labels (B and C), in the appendix, use hindsight to drop steps and so are not prospective alarm labels. The near-term labels were defined after seeing the eventual result, so we validate them on new data under a plan fixed in advance (§4.3).

## 3.5 Probes

A **probe** is a linear classifier (logistic regression) on the 5,120-dimensional residual-stream vector at the last prompt token before each target reply. The layer is chosen inside each training fold from 17 candidates on an inner holdout (the "nested" probe); remaining training details are in the appendix. Probes are trained on recruiting episodes only, and families of related variants never cross a train/test boundary. The recipe follows standard linear-probe practice (Goldowsky-Dill et al., 2502.03407) with layer selection on validation (Kramár et al., 2601.11516).

## 3.6 Text monitors

A **text monitor** reads what the agents say and do, with no access to activations. We use three: GPT-5-nano as an LLM judge returning a 0–100 score, and two **decision models** — Jev 1.14 (TypeSafe) and Luna Decisions (OpenAI) — returning a probability over fixed yes/no options, no written rationale. Each is asked a **detector** question ("is the target breaking the rule now?") or a **forecaster** question ("will it break the rule at any later point?"), at three context levels: **L1**, the target's tool calls and posted messages; **L2**, adding the peer's messages; **L3**, adding the target's unposted text and tool results (everything it saw — no reasoning trace).

Prompts follow the UK AISI ControlArena template (MIT) and the forecaster framing of The Agent Knew (Fayyazi et al., 2610.17301), fixed before the main run. We ran 18 setups on replay 2 and an 8-setup subset (fixed in advance) on the new episodes; the full ladder, call counts, and costs are in the appendix.

## 3.7 Metric and evaluation

Our primary metric is **within scenario × round AUROC** (area under the ROC curve; 0.5 = chance): each positive step is compared only with negatives from the same scenario and round, scores averaged weighted by positives. We stratify because round number alone scores 0.71 pooled (later rounds mostly belong to episodes that give in) and base rates differ across scenarios; within a group both confounds are 0.5 by construction. We report two splits: **held-out scenario** (leave-one-out), our headline for an unseen scenario, and **pooled family cross-validation** for trained-on scenarios, with 95% family-bootstrap intervals. Split mechanics, a fold-stratified variant, a **combination test** (whether activations add to a monitor), and an **alarm analysis** are in the appendix; the **confirmation test** (§4.3) is a single frozen run on new episodes.

> Decisions taken from the outline's open questions: "decision model" is used throughout and defined here (§3.6); Figure 1 is split into 1a (setup) and 1b (timeline + labels). Detail moved to `report/draft_appendix_methods.md` (methods-details appendix); the final appendix letter is assigned at assembly.

> Open for Leo: §3.3 and §3.7 are now compressed to the rationale plus pointers — check nothing you consider load-bearing dropped below the line. The fp8→bf16 fidelity note now lives in the appendix as a reassurance, not a main-text caveat.
