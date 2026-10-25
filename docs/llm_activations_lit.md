# What people do with LLM activations

Oct 24, 2026

People do three kinds of things with a model's activations: read them (train something to classify or describe them), write them (change them to change behaviour), and check what a reader actually picked up.

## The basics

When a model processes text, every layer turns every token into a vector, typically 4,096 numbers for an 8B model. The vector people usually read is the **residual stream**: the running sum that each layer adds to. Every method below makes three choices:

- **Which layer.** Middle layers are the usual default. Anthropic's production probes read all layers at once; Google DeepMind's use a single middle layer ([January 2026 summary](https://www.lesswrong.com/posts/JcAm6MFog6ssKooFN/ai-safety-at-the-frontier-paper-highlights-of-january-2026)).
- **Which token positions.** The last token, one specific token (for example, just before the reply starts), or all tokens ([Anthropic, cheap monitors](https://alignment.anthropic.com/2025/cheap-monitors/)).
- **How to turn many positions into one score (pooling).** Average them, take the maximum, or let the probe learn the weighting. This matters more than it sounds: ordinary average-pooled linear probes missed almost all long-context attacks, a 99% false negative rate ([Kramár et al. 2026, Gemini probes](https://arxiv.org/html/2601.11516v1)).

## 1. Reading: classifiers on activations

The methods below run from simplest to most elaborate. The plain linear probe is still the strongest default in most comparisons.

| Method | What it is | What it's good for | Watch out for |
| --- | --- | --- | --- |
| Difference of means | Average the "yes" activations, average the "no" ones, subtract. Score = dot product with that direction. No training. | Simplest baseline. The same vector doubles as a steering vector ([Arditi et al. 2024](https://arxiv.org/abs/2406.11717)). Used by [NARCBench](https://arxiv.org/abs/2604.01151). | Sensitive to anything else that differs between the two groups. |
| Linear probe | Logistic regression: one weight per dimension plus a bias, then a sigmoid. | The workhorse. [Apollo's deception probes](https://www.alphaxiv.org/audio/2502.03407) read one middle layer of Llama-3.3-70B (layer 22 of 80). | Can learn "talk about X" instead of X. [Apollo's probe](https://www.alphaxiv.org/audio/2502.03407) flagged honest confessions of past deception. |
| MLP probe | A small neural network (one or two hidden layers) instead of a linear layer. | Signals not stored along one direction. Non-linear jailbreak probes gave stronger steering effects than linear ones ([Kirch et al.](https://aclanthology.org/people/nathalie-maria-kirch/unverified/)). | Overfits more. No single direction to steer with. |
| Attention probe and pooling variants | The probe learns which tokens to weight (a small attention layer), or uses max or rolling-average pooling. | Long inputs and multi-turn conversations. DeepMind's MultiMax and rolling-mean attention probes ([Kramár et al. 2026](https://arxiv.org/html/2601.11516v1)); Anthropic smooths scores over 16-token windows ([Constitutional Classifiers++](https://www.alphaxiv.org/abs/2601.04603.md)). | More parameters to tune. |
| Multi-layer probe | Concatenate several layers' vectors (3 layers of 4,096 = 12,288 inputs), as in the [lmprobe library](https://pypi.org/project/lmprobe/). | When you don't know the best layer. | Bigger input, so more data needed. |
| SAE-feature probe | Decompose activations into sparse autoencoder features, then probe those. | Understanding what a signal is. | Usually worse at detection. Dense linear probes beat SAE probes, especially out of distribution ([DeepMind negative results](https://greaterwrong.com/posts/4uXCAJNuPKtKBsi28); [Kantamneni et al. 2025](https://arxiv.org/pdf/2502.16681.pdf)). |
| New head on the same model | Copy the model's later layers, or just its final layer, and fine-tune the copy as a classifier. | Stronger than a probe, cheaper than a separate model. A fine-tuned final layer beat standalone classifiers a quarter of the model's size ([Anthropic, cheap monitors](https://alignment.anthropic.com/2025/cheap-monitors/)). | Costs more compute than a probe. |
| Activation deltas | Probe the change in activations before vs after new input arrives. | Detecting that something new changed the model's task. TaskTracker reached near-perfect AUROC on prompt injection ([Abdelnabi et al.](https://arxiv.org/pdf/2406.00799)). | Adversarial suffixes can fool it ([Rahman & Alouani 2026](https://www.arxiv.org/pdf/2602.00750)). |
| Unsupervised readers | PCA, or contrast-consistent search, which finds a "truth" direction from logical consistency alone ([Burns et al. 2022](https://arxiv.org/abs/2212.03827)). | No labels available. | Harder to know what you found. |
| LLMs that read activations | Feed activation vectors into another model as extra input and ask questions in plain language: [LatentQA](https://arxiv.org/abs/2412.08686), [Activation Oracles](https://arxiv.org/html/2512.15674v1), [Patchscopes](https://arxiv.org/abs/2401.06102). Simpler relatives decode a layer straight into words: [logit lens](https://lesswrong.com/posts/AcKRB8wDpdaN6v6ru), [tuned lens](https://arxiv.org/abs/2303.08112). | Open-ended questions. Activation Oracles recovered hidden goals fine-tuned into models without being trained on that task; [code is public](https://github.com/adamkarvonen/activation_oracles). | Not mechanistic; answers can be wrong. |

## 2. Writing: changing activations to change behaviour

The same directions a probe finds can be used to push the model, which is also the strongest test that a direction matters.

- **Adding a direction (steering).** Add a multiple of a direction, usually a difference of means, to the residual stream at one layer. Standard methods: ActAdd ([Turner et al. 2023](https://arxiv.org/abs/2308.10248)) and contrastive activation addition, CAA ([Panickssery et al. 2023](https://arxiv.org/abs/2312.06681)).
- **Removing a direction (ablation).** Project the direction out so the model can't use it. Best-known example: removing the "refusal direction" ([Arditi et al. 2024](https://arxiv.org/abs/2406.11717)).
- **Capping.** Clamp how far along a direction activations can go. The Assistant Axis work does this to stop persona drift ([Lu et al. 2026](https://arxiv.org/pdf/2601.10387v1); [Anthropic post](https://www.anthropic.com/research/assistant-axis)).
- **Representation engineering.** Find directions with contrast prompts, then use them both to read and to steer ([Zou et al. 2023](https://arxiv.org/abs/2310.01405)).
- **Training on internals.** Circuit breakers fine-tune the model so its activations on harmful content are rerouted somewhere useless. This changes the model permanently ([Zou et al. 2024](https://arxiv.org/abs/2406.04313v4)).
- **Probe-guided intervention.** Steer along the probe's own direction. If behaviour changes, the probe found something causal, not just a correlate ([Kirch et al.](https://aclanthology.org/people/nathalie-maria-kirch/unverified/)).

## 3. Checking: is the probe reading what you think?

Most recent work is about this, and it is where a report earns its execution score.

- **Off-policy training data.** Probes trained on text the model didn't write itself generalise worse. The biggest failures are for behaviours defined by intent, such as strategic deception, rather than surface content ([Skapars, Kirch et al. 2026](https://aclanthology.org/people/nathalie-maria-kirch/unverified/)).
- **Style shifts.** Deception probes near AUROC 1.0 on clean data collapsed under changes of writing style. Training on varied styles recovered them ([Kumar et al.](https://www.catalyzex.com/author/Sachin%20Kumar)).
- **Many directions, not one.** Removing a deception direction and retraining keeps finding more: from about 20 directions in Qwen 3B to nearly 100 in larger models, using iterative nullspace projection ([Caught in the Act](https://arxiv.org/html/2508.19505v2)).
- **Model size.** On one deception task, probes on a 1.5B model were at chance; above 7B they reached 70–80%, and reasoning models over 90% ([Caught in the Act](https://arxiv.org/pdf/2508.19505)).
- **Cheap controls:**
  - random directions and shuffled labels, which should score about 0.5;
  - a matched text-monitor baseline on the same inputs, as in [Caught in the Act](https://arxiv.org/html/2508.19505v2) (LLM-as-judge comparison);
  - a causal check: steer along the direction and see whether behaviour changes ([Arditi et al. 2024](https://arxiv.org/abs/2406.11717)).

## 4. How it's used in production

Anthropic and Google DeepMind both settled on the same two-stage design in January 2026: a cheap probe screens all traffic, and an expensive LLM classifier handles only the cases the probe is unsure about ([Anthropic](https://www.anthropic.com/news/next-generation-constitutional-classifiers); [Kramár et al. 2026](https://arxiv.org/html/2601.11516v1)).

1. The probe runs on activations the model already computes, so it costs almost nothing extra ([Anthropic, cheap monitors](https://alignment.anthropic.com/2025/cheap-monitors/)).
2. Confident scores (very high or very low) are trusted as they are.
3. Scores in between are passed to an LLM classifier. Deferring about 8% of traffic to Gemini 2.5 Flash gave lower error than either the probe or Flash alone ([Kramár et al. 2026](https://arxiv.org/html/2601.11516v1)).

Probes and text classifiers catch different things, so combining them beats either one alone ([Constitutional Classifiers++](https://www.alphaxiv.org/abs/2601.04603.md)).

## 5. What maps onto Recruited

The core is a simple pair of probes scored every turn, with activation deltas and the checks above as the parts that make it new and credible.

- **Baseline pair.** A difference-of-means direction ([Arditi et al. 2024](https://arxiv.org/abs/2406.11717)) and a logistic-regression probe ([Apollo](https://www.alphaxiv.org/audio/2502.03407)) at a few middle layers, scored on the token just before the target's reply, every turn.
- **Activation deltas.** The change in the target's activations after each peer message: [TaskTracker's](https://arxiv.org/pdf/2406.00799) idea applied to recruitment over several turns. Cheap to add and easy to explain.
- **Pooling across turns.** A smoothed or max-over-turns score, as in the [Anthropic](https://www.alphaxiv.org/abs/2601.04603.md) and [DeepMind](https://arxiv.org/html/2601.11516v1) designs, gives a per-episode early warning.
- **Checks.** The off-policy result ([Skapars, Kirch et al. 2026](https://aclanthology.org/people/nathalie-maria-kirch/unverified/)) is the main thing to test for in the backup route, since inserted decisions are text the model didn't write.
- **Optional extras:**
  - an attention probe as the more elaborate comparison ([Kramár et al. 2026](https://arxiv.org/html/2601.11516v1));
  - an [Activation Oracle](https://arxiv.org/html/2512.15674v1) asked "is this agent about to share the token?";
  - steering along the found direction as the causal check ([Panickssery et al. 2023](https://arxiv.org/abs/2312.06681)).

## 6. Choosing layers, and training vs test data

Pick the layer by sweeping on a validation set, train on clean easy-to-label data, and test on harder data closer to real use; how well the probe transfers is the result.

### Choosing layers

The usual method is a sweep: train the same simple probe at every layer (or every few), score each on a validation set, and keep the best.

- **Middle layers usually win**, roughly 30–60% of the way through. Early layers still mostly encode the words; late layers are busy predicting the next token. Apollo used layer 22 of 80 on Llama-3.3-70B ([Apollo](https://www.alphaxiv.org/audio/2502.03407)); DeepMind's Gemini probes use a single middle layer ([January 2026 summary](https://www.lesswrong.com/posts/JcAm6MFog6ssKooFN/ai-safety-at-the-frontier-paper-highlights-of-january-2026)).
- **The curve is usually flat near the top.** Several neighbouring layers score about the same, so avoiding the first and last few layers matters more than the exact pick.
- **Choose on validation, never on test.** Picking the best layer on the test set makes the layer choice part of training.
- **Or skip the choice:** concatenate several layers, or all of them as Anthropic does ([Constitutional Classifiers++](https://www.alphaxiv.org/abs/2601.04603.md)). This needs more data.
- **For steering, judge layers by effect.** Arditi et al. computed a direction at every layer and kept the one that most changed behaviour on validation prompts ([Arditi et al. 2024](https://arxiv.org/abs/2406.11717)). A layer can read well but steer badly.

Practical default: sweep every 2–4 layers, plot validation AUROC against layer, pick the peak or a middle plateau, and put the plot in the appendix.

### Training data

- **Contrast pairs:** the same input with one thing changed, such as "pretend to be honest" vs "pretend to be dishonest" on the same facts. Apollo's training set, borrowed from [representation engineering](https://arxiv.org/abs/2310.01405). Labels are certain and differences small.
- **Instructed behaviour:** the model is told to do it, as in [NARCBench's](https://arxiv.org/abs/2604.01151) core set, where agents are told to collude.
- **Synthetic or off-policy text:** written by another model or by hand. Cheap, but this generalises worst for intent-like behaviours ([Skapars, Kirch et al. 2026](https://aclanthology.org/people/nathalie-maria-kirch/unverified/)).

### Test data

- **A different setting.** Apollo trained on simple contrast pairs and tested on role-play, insider trading and sandbagging ([Apollo](https://www.alphaxiv.org/audio/2502.03407)). NARCBench trained on committee deliberations and tested on code-review sabotage, pipeline poisoning and steganography ([NARCBench](https://arxiv.org/abs/2604.01151)).
- **Natural rather than instructed behaviour** where possible: the hardest and most convincing test.
- **Production-style shifts.** DeepMind trained on short prompts and tested on long context, multi-turn and adaptive red-teaming ([Kramár et al. 2026](https://arxiv.org/html/2601.11516v1)).

### Thresholds, controls and splits

- **A control set for false positives:** ordinary data where the probe should stay quiet. Apollo, as far as I know, set its decision threshold on ordinary chat data at a 1% false-positive rate. Set the threshold on control data, then report recall at that threshold, not only AUROC.
- **Split by group, not by example.** Examples from the same scenario, seed family or template are near-duplicates, so whole groups go in train, validation or test. DeepMind explicitly removed test rows overlapping training prompts ([Kramár et al. 2026](https://arxiv.org/html/2601.11516v1)).

### Applied to Recruited

- **Split by episode family**, so no family appears in more than one of train, validation and test.
- **Layer sweep on validation families only.** Freeze layer, position and threshold before touching test.
- **Main route:** train and test on natural policy-cell episodes (gave in vs resisted), families split as above.
- **Backup route:** train on the constructed share/keep pairs, test only on natural episodes, and report the transfer loss (NARCBench saw about 1.0 → 0.7).
- **Controls:** policy-control episodes (rule present, no ask) are the false-positive set; set the threshold there.
- **Transfer tests:** a reworded rule, a different peer tactic, or a second target, each held out entirely.

## Sources

- [Detecting Strategic Deception Using Linear Probes (Apollo)](https://www.alphaxiv.org/audio/2502.03407)
- [Cost-Effective Constitutional Classifiers via Representation Re-use (Anthropic)](https://alignment.anthropic.com/2025/cheap-monitors/)
- [Next-generation Constitutional Classifiers (Anthropic)](https://www.anthropic.com/news/next-generation-constitutional-classifiers)
- [Constitutional Classifiers++ (arXiv 2601.04603)](https://www.alphaxiv.org/abs/2601.04603.md)
- [Building Production-Ready Probes For Gemini (arXiv 2601.11516)](https://arxiv.org/html/2601.11516v1)
- [AI Safety at the Frontier: January 2026 highlights](https://www.lesswrong.com/posts/JcAm6MFog6ssKooFN/ai-safety-at-the-frontier-paper-highlights-of-january-2026)
- [lmprobe library](https://pypi.org/project/lmprobe/)
- [Detecting Multi-Agent Collusion Through Multi-Agent Interpretability / NARCBench (arXiv 2604.01151)](https://arxiv.org/abs/2604.01151)
- [Refusal in Language Models Is Mediated by a Single Direction (arXiv 2406.11717)](https://arxiv.org/abs/2406.11717)
- [Activation Addition / ActAdd (arXiv 2308.10248)](https://arxiv.org/abs/2308.10248)
- [Steering Llama 2 via Contrastive Activation Addition (arXiv 2312.06681)](https://arxiv.org/abs/2312.06681)
- [Representation Engineering (arXiv 2310.01405)](https://arxiv.org/abs/2310.01405)
- [Improving Alignment and Robustness with Circuit Breakers (arXiv 2406.04313)](https://arxiv.org/abs/2406.04313v4)
- [The Assistant Axis (arXiv 2601.10387)](https://arxiv.org/pdf/2601.10387v1) and [Anthropic post](https://www.anthropic.com/research/assistant-axis)
- [Discovering Latent Knowledge Without Supervision / CCS (arXiv 2212.03827)](https://arxiv.org/abs/2212.03827)
- [LatentQA (arXiv 2412.08686)](https://arxiv.org/abs/2412.08686)
- [Activation Oracles (arXiv 2512.15674)](https://arxiv.org/html/2512.15674v1) and [code](https://github.com/adamkarvonen/activation_oracles)
- [Patchscopes (arXiv 2401.06102)](https://arxiv.org/abs/2401.06102)
- [Interpreting GPT: the logit lens](https://lesswrong.com/posts/AcKRB8wDpdaN6v6ru)
- [Tuned Lens (arXiv 2303.08112)](https://arxiv.org/abs/2303.08112)
- [Negative Results for SAEs on Downstream Tasks (DeepMind)](https://greaterwrong.com/posts/4uXCAJNuPKtKBsi28)
- [Are Sparse Autoencoders Useful? (arXiv 2502.16681)](https://arxiv.org/pdf/2502.16681.pdf)
- [Get my drift? TaskTracker (arXiv 2406.00799)](https://arxiv.org/pdf/2406.00799)
- [Bypassing Prompt Injection Detectors (arXiv 2602.00750)](https://www.arxiv.org/pdf/2602.00750)
- [Caught in the Act (arXiv 2508.19505)](https://arxiv.org/html/2508.19505v2)
- [Off-policy training data and probe generalisation; non-linear jailbreak probes](https://aclanthology.org/people/nathalie-maria-kirch/unverified/)
- [Deception probes under stylistic shift](https://www.catalyzex.com/author/Sachin%20Kumar)
