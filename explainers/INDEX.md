# Explainers

- [peer-tactics-and-probe-evaluation.md](peer-tactics-and-probe-evaluation.md): why test peer tactics (later, knowing give-ins), and how the probe vs monitor comparison is scored per turn.
- [shi-et-al-setup.md](shi-et-al-setup.md): the Shi et al. (2609.24967) setup worked through one real Gemma trajectory: task, 200-char channel, verdict rule that forces reject, reward that punishes it, and how Alice holds then gives in.
- [after-the-replay.html](after-the-replay.html): whole-project recap, what happens after the GPU replay (checks, baselines, nested CV, scoring, monitors, transfer), the ML concepts with worked examples, and shortcuts in our data with real numbers from the step manifest. Artifact: https://claude.ai/artifact/WWx4Sozwgc3h2JkuFx86aP
- [activation-replay.md](activation-replay.md): how E02 re-runs each saved target request through pinned Qwen3-32B in one forward pass (no generation), saves the [64 × 5120] last-prompt-token residual stream via forward hooks, checks fidelity by scoring the real reply, and hashes everything; runnable CPU toy in [toys/replay_toy.py](toys/replay_toy.py).
