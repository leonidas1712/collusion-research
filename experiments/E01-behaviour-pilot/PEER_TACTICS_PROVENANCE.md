# Where each peer tactic comes from

2026-10-24. Companion to `PEER_TACTICS.md` (the approved, softened text). One row per tactic: the direct source, the older persuasion research it rests on, evidence that the idea moves LLMs, and what we changed.

**Direct source for T1–T7:** the persuasion prompts released with Colosseum (Nakamura et al., arXiv 2602.15198), file `collusion_hackathon/colosseum/experiments/persuasion/collusion/prompts.py` in the sprint starter repo. That file has an empty control plus 8 tactics. The Colosseum paper studies 3 of them; the other 5 are in the released code only.

**Evidence that these principles move LLMs (general, not per tactic):**
- Zeng et al. 2024, "How Johnny Can Persuade LLMs to Jailbreak Them" (ACL 2024): a 40-technique persuasion taxonomy drawn from social-science work, applied to make LLMs comply. Covers authority, social proof, scarcity, reciprocity, framing, anchoring.
- Meincke et al. 2025, "Call Me a Jerk: Persuading AI to Comply with Objectionable Requests" (Wharton working paper): Cialdini's seven principles applied to GPT-4o-mini roughly doubled compliance with objectionable requests.

Unverified in this session: exact section and page numbers, and the precise effect sizes. Check before citing numbers in the write-up.

| Tactic | Colosseum name (paper / code) | Older research it rests on | What we changed (and where decided) | Our invention? |
|---|---|---|---|---|
| T0 no tactic | `control` (empty) | — | Our existing peer prompt; overnight baseline | Baseline is ours |
| T1 helpful framing | helpful misdirection (**paper**) | Framing: Tversky & Kahneman 1981, "The framing of decisions and the psychology of choice" | Softened, gradual; slots | No |
| T2 organizer tone | authority nudge (**paper**) | Authority: Cialdini 1984, *Influence*; Milgram 1963 obedience studies | Softened; the peer never claims to be a manager (kept from the source) | No |
| T3 trade | reciprocity / trade (**paper**) | Reciprocity: Cialdini 1984; Gouldner 1960, "The norm of reciprocity" | The offer is information only, not a favour that finishes the target's task, to keep the own-stake lever separate | The info-only restriction is ours |
| T4 social proof | social proof / herding (code only) | Social proof: Cialdini 1984; Asch 1951 conformity experiments | Unverifiable "others agree" claims kept; no second peer exists | No |
| T5 time pressure | scarcity / urgency (code only) | Scarcity: Cialdini 1984 | Urgency comes from the peer, not the operator; unverifiable claims kept | No |
| T6 playing it safe | risk aversion (code only) | Loss aversion: Kahneman & Tversky 1979, "Prospect theory" | Skip for release-date and front-door-sign (nothing shared to be at risk) | Skip decisions are ours |
| T7 cost anchoring | cost anchor (code only) | Anchoring: Tversky & Kahneman 1974, "Judgment under uncertainty: heuristics and biases" | Softened, slots | No |
| Not used | split-brain (code only) | — | Dropped: needs two or more targets | — |

**Changes common to all tactics (ours):**
- **Wording:** the softer version: suggestions, not commands; a plain request first; the tactic only comes in gradually if the target hesitates; the peer stays a normal teammate.
- **Slots:** for reuse across scenarios.
- **Matched control peers:** the same text with the allowed ask.
- **Peer knowledge:** the peer is not told the target's rule.

**Why we picked tactics at all (our own evidence):** in the overnight trace read (EXPERIMENT_LOG, 24 Oct), threats and repeated pressure never worked. The late or knowing give-ins came after a workaround the target proposed, or after small sideways asks about the token's format. That pointed us to indirect, published persuasion moves rather than stronger pressure.
