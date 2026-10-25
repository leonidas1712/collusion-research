# Concerns and next steps

24 Oct 2026, 20:45 SGT. Open concerns about the project, each with a proposed response. "Started" means it's running now.

## 1. "But this is just 2 agents"

The sprint leans towards several agents colluding. Steps up, cheapest first:

1. **Several peers on one target (many-to-one).** 2–3 recruiters in the same channel. This is a peer-count setting in the harness, already in the plan. It tests whether pressure from a group changes how and when the target gives in. Literature: Many-to-One (Bashir et al. 2512.03097); GroupGuard.
2. **Bystanders.** A 3–4 agent channel with one recruiter, one target and honest teammates who can object. The monitor then reads a group chat, which is closer to real multi-agent deployments.
3. **Spread.** A recruited target goes on to recruit a third agent. This ties to the author's co-authored Share-Borne paper (arXiv 2609.35576). It shows recruitment as how collusion forms and propagates.
4. **Mutual collusion data.** Shi et al.'s two-agent traces (E04), where both agents relax a rule together. It's a different collusion shape from ours, and a second dataset.

**Framing:** recruitment is the building block. Every collusion starts with one agent getting another to go along. We study that link and whether it can be predicted, and the steps above show it in a larger group.

## 2. If the probe doesn't work

- **The monitor comparison is a result in itself** (sprint Q2.2): how well black-box monitors at each level predict giving in.
- **Backup routes:**
  - (a) Shi et al. traces (E04);
  - (b) the constructed-decision route: train on constructed share/keep pairs, test on natural episodes;
  - (c) forced continuation (see 3), which turns held episodes into graded labels.
- **A clear negative result** with the checks done is still reportable.

## 3. Forced continuation (not done yet)

Two meanings, both cheap and both untested:

- **Resampling from a prefix (branching).** Take a saved episode prefix at step t and run the next 1–3 rounds 5–10 times with the same peer. The share that give in is a **probability label** for that step, the way Kortukov et al. label their steps. It doesn't need the original episode to have given in gradually, so every held episode becomes graded data, and it shows when the target "decides". Cost: ~200 prefixes × 5 × ~3 rounds ≈ $1–2 of API.
- **Prefill.** Force the start of the target's reply, e.g. a compliant or a refusing opening, and see whether it continues or recovers. This is a behavioural stress test of how committed the target is.

**Suggested first:** branching on ~50 prefixes from the main dataset.

## 4. Black-box monitors from the literature (started)

Adopt published monitor and judge prompts and adapt them minimally, rather than inventing our own, so the baseline is defensible. Candidates:
- the Shi et al. reflection judge (it flagged rule relaxation before the first accept for 74/84 Gemma agents);
- NARCBench judges;
- Apollo's GPT-4o baseline;
- Colosseum's judge;
- TraceGuard's constraint-adherence rubric;
- CoT monitoring (Baker et al. 2025) for the reasoning level.

The exact prompts and licences are in `docs/monitor_baselines.md`. Provenance goes in PROVENANCE.md.

## 5. Human labels to calibrate judges and monitors (started)

The viewer gets per-step and per-episode label buttons, saved in the browser. An "Export labels" button downloads a file, and `viewer.py labels import` merges it into `runs/human_labels.json`. Labelling queues are prepared as saved lists. These labels are the reference for validating the Luna judge, the "decision visible" label and the monitors.

## 6. An open-weights reasoning model

Qwen3-32B has a thinking mode, so it uses the same weights and the same replay pipeline, and it adds the "+ reasoning" monitor level. Cheap check: 10 lead-setup episodes with thinking on (~$0.15), to see whether the behaviour still holds and then gives in. Needs a `--target-reasoning` switch in `scale_up.py`, and a provider that serves Qwen3-32B with reasoning on.

## 7. Steering as an intervention

Staged plan (`docs/probe_takeaways.md`):
1. A free steerability pre-check.
2. Stage 1: a forward-only causal check (~$1–3 GPU).
3. Stage 2: generation with the direction subtracted (~$3–6 GPU), measuring the give-in rate and task success on controls.

Alternative: probe-guided sampling (FPCG, Kortukov et al.) as a defence. All GPU stages need budget approval first.

## 8. "Isn't this just prompt injection?"

How it differs:
- **Source.** The pressure comes from a teammate agent with its own goal, in a shared workspace and a cooperative frame. It isn't instructions hidden in data the target processes.
- **Dynamics.** Many targets refuse for several rounds and give in after persuasion: claimed authority, workarounds, side questions. That's a social process over turns, not a single hijack.
- **Outcome.** Two agents jointly violate the operator's policy: one recruits, the other goes along. That's collusion against the principal, the pattern in the OpenAI–Hugging Face recruiting incident.
- **Question.** Can we predict that a recruited agent will defect before it does, and do activations beat monitors? Prompt-injection detectors (e.g. TaskTracker) detect that injected instructions arrived. They don't predict whether the agent will go along later.

**Honest overlap:** mechanistically it's related to multi-turn persuasion and jailbreaks. We position it as the agent-to-agent recruitment case.

**Possible strengthening:** a condition where the same request arrives as an injected instruction in a file rather than from a peer. Compare give-in rates and probe behaviour.
