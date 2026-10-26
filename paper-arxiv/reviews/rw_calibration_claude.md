# Related-work rigour calibration for "Recruited"

Date: 26 October 2026. Author: Claude (review agent).

Purpose: to check how much rigour and robustness work the closest published papers do, so that a solo arXiv preprint grown from a 3-day hackathon is held to a fair bar. In particular, to check whether three blind-reviewer requests go beyond the field norm:

- (a) a trained text-classifier baseline;
- (b) a write_file-conditioned (file-action) confound check;
- (c) full reproducibility settings.

## Sources and method

Each paper was fetched with plain WebFetch from the URL in `paper-arxiv/references.bib`. Text was extracted from the arXiv PDFs with `pdftotext`. Claims below point to a section, table or figure. "Not stated" means I did not find it in the text that I read. It does not mean the paper lacks it.

| Paper (bib key) | Source read |
|---|---|
| Rose et al. 2026, NARCBench (`rose2026`) | arXiv 2604.01151v5, full PDF |
| Kortukov et al. 2026 (`kortukov2026`) | arXiv 2606.11172v1, full PDF |
| Fayyazi et al. 2026, "The Agent Knew" (`fayyazi2026agent`) | arXiv 2610.17301v1, full PDF |
| Dong et al. 2026 (`dong2026`) | arXiv 2608.02657v2, full PDF |
| Yu et al. 2026 (`yu2026`) | arXiv 2610.05295v1, full PDF |
| Goldowsky-Dill et al. 2025 (`goldowskydill2025`) | arXiv 2502.03407, full PDF |
| MacDiarmid et al. 2024 (`macdiarmid2024simple`) | Anthropic blog post (HTML) |
| Kirch et al. 2025 (`kirch2025what`) | arXiv 2411.03343v3, full PDF |
| Advani et al. 2026 (`advani2026reading`) | alphaXiv abstract/summary page only; full text not read |

### Bib discrepancies found

1. **The brief misattributes "the agent knew".** It is Fayyazi, Kamal & Pedram (`fayyazi2026agent`, arXiv 2610.17301), not Kortukov. `kortukov2026` is "Predicting Future Behaviors in Reasoning Models Enables Better Steering" (arXiv 2606.11172). Both bib entries match their arXiv pages. Only the brief's label is wrong. Check that the paper text does not repeat the mix-up.
2. **Some keys differ from the short names in the brief.** The keys are `goldowskydill2025`, `macdiarmid2024simple` (an Anthropic blog post from 2024, not an arXiv paper), `kirch2025what` (arXiv v3, Nov 2025) and `advani2026reading`.
3. **`advani2026reading` has a non-standard URL** (`alphaxiv.org/abs/2610.frozen-states-future-action-prediction`). It is a workshop paper. I could read only the alphaXiv summary page, so its row is less certain. That page names Qwen2.5-7B, but the abstract claims "three architectures spanning a 3.4x parameter range" without naming the other two.
4. **The other entries match.** Titles and authors of `rose2026`, `kortukov2026`, `fayyazi2026agent`, `dong2026`, `yu2026`, `goldowskydill2025` and `kirch2025what` match the fetched PDFs.

## 1. Comparison table

Abbreviations:

- "Instr./situation control": does the paper control for the confound that the probe detects the instruction or situation rather than the behaviour?
- Rows marked "Ours" summarise "Recruited" from the brief.
- Cell text after the main answer gives the supporting section.

| Paper | Models | Positives / negatives | Instr./situation control | Held-out generalisation | CIs / significance | Pre-reg. | Baselines | Causal test | Reproducibility |
|---|---|---|---|---|---|---|---|---|---|
| **Rose 2026** (NARCBench) | 4: Qwen3-32B, Llama-3.1-70B, DeepSeek-R1-Distill-Qwen-32B, gpt-oss-20b (App. I) | **Instructed**: two of four agents get a secret collusion instruction; control runs give all four agents "identical honest instructions" (App. J.1; §5.1) | Partial. The instruction is only in the system prompt, and names, styles and options are diversified (App. J.2–J.3). A null probe on a random split of honest agents scores near chance (§5.2). They state: "In NARCBench, agents are explicitly told to collude. Therefore, to control for prompt differences…" and test emergent collusion, where transfer is only partial (§6.3, Table 1: 0.49–0.73) | Yes. Leave-domain-out on Core; zero-shot to Transfer (6 families) and Stego (§5.1–5.2) | Mean ± std over 10 seeds and layers; 95% bootstrap bands on ROC (Fig. 3). No significance tests | Not stated | LLM transcript judges on Stego, including Claude Sonnet 5 (App. L). No trained text classifier | None. "We plan to do this in future experiments" (§4, fn. 5) | Code, data and hyperparameters (Reproducibility statement; App. E, F) |
| **Kortukov 2026** | 4: DeepSeek-R1-Distill-Llama-8B, Qwen3-14B, gpt-oss-20b, QwQ-32B (§3.1) | **Sampled, not instructed.** Labels are future-behaviour probabilities from resampling (10×10 completions per prefix) on 6 behaviour datasets (§3.2) | Indirect. Labels vary within the same prompt (behaviourally uncertain prompts), and "prediction" features are contrasted with "detection" features (§3.3.2). No explicit situation control | Within-dataset only: "two disjoint subsets of 100 for training and evaluation" (§3.3.1). No cross-dataset transfer reported | Not stated (random and mean baselines only, Fig. 4) | Not stated | Random and mean predictors; difference-of-means activation steering for the steering part (§4) | Yes. Probe-guided generation (FPCG) changes behaviour rates (§4.2) | Code and data released (p. 1 footnote); T = 1.0 and layers stated (§3.1, §3.3.1) |
| **Fayyazi 2026** ("The Agent Knew") | 4: Qwen3.8-27B, Muse-Glimmer-30B, Gemma-4-26B-A4B, gpt-oss-20b (§4 setup); frontier API agents only behaviourally | **Matched twin worlds**: each task exists in an unauthorized world x⁻ and an authorized twin x⁺ that differ in one fact, with the same seed (§2, §3.1). Labels come from the environment | **Strongest.** "Hard negatives": the same critical action in the authorized twin "forces g to read whether the action is authorized, not which action it is" (§3.2). Within-(model, template) AUROC, because "a pooled AUROC would reward template recognition" (§3.2) | Yes. Fresh scenarios and seeds for every confirmatory test (§2); unseen safety families (AUROC 0.81); AgentDojo transfer (abstract, §4.3) | Cluster-bootstrap 95% CIs; permutation nulls; Holm correction (§3.2; Table 2) | **Yes**, "preregistered and hash-locked"; descriptive results are marked as such (abstract; Table 2) | **Supervised TF-IDF text classifier** plus zero-shot CoT and action LLM monitors (§3.2). Internals lead TF-IDF by only +0.034 [0.006, 0.060] (Table 2) | Yes. Gating and steering cut violations over whole episodes (§4.3–4.4) | Code, data and "the full record, including tests that did not pass" (abstract) |
| **Dong 2026** | 8, from 2B to 2.8T (Qwen3/3.5, GPT-oss-20B, Gemma-4-31B, GLM-5.2, Kimi-K3; abstract, §3) | Label = **exposure** (the latest tool result contains an injection), "independently of whether the model is ultimately compromised" (§3.1) | Not applicable: the target *is* the situation. Shortcut risk is measured by the train-minus-held-out gap as training size varies (§3.4) | Yes. Held-out attacks, instructions, suites and a "strict" split; cross-lingual; adaptive attacks (§3.1, §3.4) | ± std for random directions; seed stability; 10–90% quantiles over 256 seeds (Figs. 3–4) | Not stated | Random-direction probes for detection. Prompting/SafePath baselines for the defence (§4). No trained text classifier | Partial. A probe-gated reasoning prefill (AGRI) lowers attack success (§4). The direction is not shown to be causal | Code released; LR, batch size, epochs, T = 1, top-p 0.95 (§3.2; App.) |
| **Yu 2026** | 4: Qwen-2.5-7B (primary), Qwen-2.5-1.5B, Llama-3.1-8B, Gemma-2-9B-It (§3) | Counterfactual instruction-vs-data role prompts (1,440 per model); AgentDojo hijacked vs resisted trajectories (Table 1) | Yes, for role readout. The role–format association is reversed between train and test, so that "a classifier relying on the training role–format association should fail" (§4.1) | Yes. Held-out content, paraphrase family, format swap, leave-attack-family-out (Table 3; Fig. 3C) | Bootstrap 95% CIs; exact McNemar tests (§3; Fig. 3) | Not stated | **Structural feature classifier** (length, punctuation, wrapper tokens, format), scoring 0.508 (§4.1). Random-direction and position controls | **Yes, central.** Activation patching and direction edits (§4–5) | No own code link found; uses open TaskTracker code (App.) |
| **Goldowsky-Dill 2025** | 1: Llama-3.3-70B-Instruct (§3) | Training: **instructed** honest vs deceptive pairs (Zou et al.). Evaluation: on-policy responses labelled by GPT-4o (§3) | No control; the confound is acknowledged. The probe is sensitive to "is the scenario related to deception", not only to "is the response deceptive" (§4.1). "Spurious correlations" are listed as a failure mode (§4.2). A Roleplaying-trained comparison is offered as a partial probe of this (§4.3) | Yes. Trained on one dataset, evaluated on Roleplaying, Insider Trading and Sandbagging (§3) | Not stated (point AUROC and recall at 1% FPR) | Not stated | **GPT-4o black-box transcript monitor**; SAE probes; follow-up-question probe (§4.3, Fig. 6). No trained text classifier | None | Code at github.com/ApolloResearch/deception-detection |
| **MacDiarmid 2024** (blog) | 1 main sleeper-agent model (Claude-2-equivalent); "a range of other models" not listed | Generic yes/no contrast pairs that "never include the deployment trigger or the defection behavior" | Discussed, not controlled: "possible that the salience of this feature is an artifact of our backdoor insertion process" | Partial. Across base models and backdoor methods, but "base-to-sleeper-agent generalization wasn't reliable" | None; point AUROC | Not stated | 1,000 random directions (best 95.3%); a base model without a backdoor | None | Not stated; layer given only as "middle residual stream" |
| **Kirch 2025** | 5: Gemma-7b-it, Llama-3.1-8B, Llama-3.2-3B, Ministral-8B, Qwen-2.5-7B (§3) | Jailbreak prompts (300 requests × 35 attack methods), labelled successful/unsuccessful by the HarmBench autograder (§3) | No explicit control. Leave-attack-out transfer is weak and "attack-family-specific", so probes partly track attack type (§4.3) | Yes. Ten held-out attack methods (§4.3) | Confidence intervals on probe accuracy (Fig. 3). No significance tests | Not stated | Random guessing only. No text classifier or LLM monitor | **Yes.** Probe-guided latent interventions shift compliance; MMLU side-effect check (§4.4; App.) | Code at github.com/NLie2/jailbreak-features |
| **Advani 2026** (workshop; summary only) | 1 named (Qwen2.5-7B); abstract claims 3 | Future tool identity k = 1/3/5 steps ahead | Partial. A one-hot current-tool MLP control, which "does not isolate the hidden state from all task or trajectory context" | Task-grouped splits | 5 seeds; no CIs stated | Not stated | One-hot MLP; Markov successor; verbalised self-prediction; QLoRA. No trained text classifier | None: "It does not show that the model has a causal plan" | Not stated |
| **Ours ("Recruited")** | 2: Qwen3-32B, gpt-oss-20b | Peer recruiting episodes; leaking vs non-leaking calls | Within-scenario-and-round AUROC; keyword, read-step-flag, pre-request placebo and incoming-message-only probe checks; no action-matched (write_file) control | Held-out scenarios; fresh test episodes | Family-clustered bootstrap CIs | Yes, 1 test | Zero-shot LLM monitor (Jev); simple heuristics (keywords, read flag). No trained text classifier | None | Partial (the review lists missing settings) |

## 2. Calibration

1. **The typical bar** in the nine closest papers is:
   - about 4 models (median 4; range 1–8);
   - held-out tasks, environments or attack families (8 of 9);
   - some uncertainty reporting, usually seed std or bootstrap bands (6 of 9; only Fayyazi and Yu run significance tests);
   - code release (6 of 9).

   Pre-registration is rare (1 of 9: Fayyazi). An analysis history is also rare: only Fayyazi publishes "the full record, including tests that did not pass".
2. **A trained text-classifier baseline is rare.** Only Fayyazi trains a supervised TF-IDF classifier (§3.2). Yu trains a 7-feature structural classifier, which is closer to a heuristic. Goldowsky-Dill, Rose and Fayyazi use zero-shot LLM monitors. MacDiarmid, Dong, Kirch and Kortukov use only random or trivial baselines. However, Fayyazi is the closest agent-forecasting paper, and its probe beats TF-IDF by only +0.03 AUROC (Table 2). Fayyazi also writes that "once the plan is written, text monitors match or slightly beat them" (§1).
3. **Action-matched confound checks (the file-action or workflow analogue) are rare.** Only Fayyazi builds them in, with authorized-twin hard negatives on the same critical action (§3.2). Yu's role/format reversal is the nearest other control. Goldowsky-Dill and MacDiarmid name the situation confound but do not control it. Rose controls instruction leakage through a null probe and an emergent-collusion test, and that test transferred only partially.
4. **Causal tests are fairly common.** Five of nine papers run an intervention: Kortukov, Fayyazi, Yu, Kirch, and partly Dong. Rose, Goldowsky-Dill, MacDiarmid and Advani do not.
5. **Where "Recruited" is above the norm:**
   - pre-registration (shared only with Fayyazi);
   - an analysis-history appendix (shared only with Fayyazi);
   - family-clustered bootstrap CIs (only Fayyazi uses cluster bootstraps);
   - within-scenario-and-round AUROC (this mirrors Fayyazi's within-template AUROC; no other paper has it);
   - its set of shortcut checks.

   Its baselines are **at** the norm: a zero-shot LLM monitor plus heuristics, the same tier as Goldowsky-Dill and Rose.
6. **Where it is below the norm:**
   - model count (2 against a median of 4, but above Goldowsky-Dill and MacDiarmid at 1);
   - no causal or intervention test;
   - reproducibility settings that are still incomplete. Most papers state sampling temperature, layers and seeds; Dong, Kortukov and Rose do so explicitly.
7. **Fair reading:** for a solo hackathon-derived preprint, the statistical hygiene is already at or above most lab papers here. The two gaps a reader will notice are the missing settings and the file-action confound for gpt-oss.

## 3. Requests that are clearly beyond the field norm (safe to list as future work)

- **A trained text-classifier baseline.** Only 1 of 9 papers has one. There is one condition: the claim "catches what a text monitor misses" should be worded as "what a zero-shot monitor misses". The incoming-text-only probe already shows that the signal is present in the text.
- **Pre-registering more tests, or multiple-comparison correction.** Only Fayyazi does this.
- **Causal or steering interventions on the probe direction.** These are common, but none of the papers treats them as necessary for a detection claim. Rose, Goldowsky-Dill and MacDiarmid have none.
- **More model families** (beyond two) and frontier-scale models.
- **Transfer from engineered to emergent or persuasion-based recruiting.** Rose shows that this is hard; only Rose attempts it.
- **Per-episode deployment metrics** at strict false-positive rates beyond what is reported. Few papers report them.

**Not beyond the norm, so do these rather than defer them:**

- **Basic reproducibility settings**: temperatures, seeds, layers, reasoning effort, providers and the monitor prompt. Most comparators state them, and they cost little.
- **A write_file-conditioned AUROC for gpt-oss.** Action-matched controls are rare (1 of 9). But this is a re-analysis of existing data, and the confound is specific to this dataset. It is the same "reads the situation, not the action" critique that Fayyazi's design was built to avoid. At minimum, state it as a caveat.
