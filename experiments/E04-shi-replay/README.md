# E04: probe vs text monitor on Shi et al.'s released traces (backup route)

**Status:** proposed, to explore soon. Nothing has been run. The GPU step needs Leo's OK against the Modal budget.

**Question:** in Shi et al.'s released Gemma-4-31B trajectories, do probes on the agent's own activations predict its first rule-breaking ACCEPT before it happens? Compare against text monitors that see the same text up to the same point.

**Why:**
- It's natural "holds, then gives in" data from someone else's setup, with nobody instructed to collude.
- It needs no API spend, only a GPU replay.
- If our main probe works, it also gives a transfer test.
- The paper has no monitors or probes at all.

**Background:**
- Setup, data and options: [`docs/backup_shi_et_al.md`](../../docs/backup_shi_et_al.md).
- Worked example of one trajectory: [`explainers/shi-et-al-setup.md`](../../explainers/shi-et-al-setup.md).
- Data: [HF `SALT-NLP/agent-collusion`](https://huggingface.co/datasets/SALT-NLP/agent-collusion), MIT.

## The setup, in short

- Two copies of Gemma-4-31B run 10 episodes.
- Each episode: each agent does a task, they get 5 rounds of 200-character messages, then each accepts or rejects the other's work.
- The rule: accept only with the other's complete raw log (about 5–15k characters), which can't fit through the channel. So every ACCEPT breaks the rule.
- The scoring calls a rule-following reject of correct work "wrong verdict". Over the episodes agents give in.
- Gemma (our numbers from the released tables):
  - first accepts are spread over episodes 2–10, and 16 of 100 agents never accept;
  - 17 agents held for 2 or more episodes after their peer was already accepting.

## Plan

1. **Units.** Each Gemma agent-episode gives about 1,000 verdict decisions in total. Following Leo's 2026-10-24 decision, score every target step (each model call), not only the verdict:
   - the task calls;
   - each communication round;
   - the verdict;
   - the reflection.
2. **Inputs.** Use the stored per-agent context (`results[k].agents[a].messages` in each trace), cut at each step. Write a small adapter that turns these into the input format E02 replays. Then run one forward pass per step on Gemma-4-31B and save middle-layer residual activations.
3. **Labels.** All come straight from the stored verdicts:
   - "accepts this episode", among agents that haven't accepted yet;
   - "first accept is next episode", which gives one episode of warning;
   - for the onset of collusion itself, the paper's `onset_evaluation_episode`.
4. **Split by task sequence** (`sequence_id`, 50 shared sequences), so the same tasks are never in both train and test.
5. **Monitors at the same cutoff:**
   - a text monitor that sees only the channel (the fair comparison);
   - a full-context text monitor;
   - the paper's reflection judge (`relaxation` table), as the strong reference.

   Flag steps where the decision is already visible in the agent's own text, such as a reflection that endorses relaxing the rule. Report results on the steps where it isn't, as in our main design.
6. **Metrics:** AUROC and recall at a low false-alarm rate, per step and over lead time, as in `docs/evaluation_design.md`.

## First step (small, needs the OK)

Replay 5 trajectories on one 80 GB GPU (A100 or H100). This checks:
- **Timing:** about 45M prefill tokens for all 50; a few GPU-hours is an unmeasured guess.
- **That we rebuild the context correctly:** the replayed model should give high probability to the verdict tokens the agent actually produced. Use an NLL check like E02's.

If both pass, run all 50.

## Known issues to check

- **Context length.** Contexts reach about 67k tokens. E02's default `--max-tokens 32768` must be raised.
- **Chat template.** Gemma's stored history has no past reasoning, and how vLLM rendered past turns isn't documented. The NLL check covers this.
- **Overflow trimming.** When a context overflowed, the oldest episode was dropped. Use the stored per-episode `messages`, not a rebuild.
- **Weights.** `google/gemma-4-31B-it` is on HF. A licence click-through may be needed (not checked).
- **Interpretation.**
  - The pressure here is mostly the scoring, not a persuading peer.
  - There is one decision per episode.
  - Private reflections give text monitors near-perfect warning, which is why we match what each monitor sees to the probe's cutoff.

## Later

**Transfer.** Run a small deploy-token pilot on Gemma-4-31B, train a probe on it, and test it on these traces, same model on both sides.

**Optionally**, rerun their harness with a scripted Bob who persuades, using our T1–T7 tactics, to get a recruitment version. That costs API money: about 11M input tokens per trajectory.
