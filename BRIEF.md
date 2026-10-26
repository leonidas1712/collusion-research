# Brief: rewrite the paper as a clear arXiv draft

From Leo, for the agents working on the collusion-research repo. Read this first, then `WRITING.md`. The ICLR 2027 style files are attached alongside.

## 1. Where things stand

- The sprint paper ("Recruited") was submitted to the Apart AI Collusion Research Sprint. The deadline has passed and judging takes about a week. The submitted version is frozen at the `apart-submission` tag.
- You already know about the two planned follow-up experiments: causal steering, and transfer to the Shi et al. environment. **They are not part of tonight's work.**
- The new plan: turn this work into an **arXiv preprint**, possibly sent to a workshop later. It should show solid GPU and interpretability work, written so that people actually understand it.

## 2. Why this rewrite matters to me

I pushed hard for clarity during the sprint. I said repeatedly: don't obfuscate, don't scatter caveats everywhere. It wasn't followed well enough. The result is correct and rigorous, but hard to read. Now every fresh LLM I give the paper to says it is unclear. A blind subagent you spawned yourselves said the same. That is frustrating, because the substance is good and the writing is what hides it.

This time, clear communication is a primary goal, on equal footing with rigour and accuracy. It is not a polish step at the end.

`WRITING.md` explains why the sprint version drifted: each caveat felt locally justified, and together they buried the findings. It also sets out the rules and process to prevent that. Follow it. When your instinct says to add another qualifier, assume that is the failure mode.

## 3. The standard

Write it like a top-tier, impactful AI safety paper. It should be rigorous enough for a conference, and clear enough that people would share it on X.

To be clear, we are not optimising for virality. That framing just makes the bar concrete. Nobody shares a paper that has ten hedges and three confidence intervals in every paragraph. A reader on X sees a headline figure and a few sentences, and needs to get it from those.

What this means in practice:
- Write plain, confident sentences that are precisely true.
- Include one headline figure near the top that carries the main result on its own.
- Use more diagrams and charts where they help, but not more main-text tables. Tables add cognitive load.
- Use short formal definitions where they make the setup clearer, as is normal in good papers. `WRITING.md` §6 gives the scale.
- Aim for **9–10 pages of main text.** arXiv has no limit, but this keeps us brief.
- **The appendix must be clean too.** The sprint appendix was bloated. That was forgivable in a sprint, but not now. The same rules apply there.

**Nothing about rigour is negotiable.** Every number must stay correct and traceable. Every claim must stay exactly as strong as its evidence. Confirmed and exploratory results must stay clearly separated. Rigour is just expressed through structure, not through hedges scattered everywhere.

## 4. The cohort problem, specifically

The single biggest source of hedging in the sprint paper was the tangle of overlapping call sets: two confirmation sets, label definitions that differ between models, and analyses added after seeing earlier results. Agents tried to carry all of that inside every sentence.

`WRITING.md` §4 sets out how to handle it. In short:
- **Name a few datasets once.** For example, development episodes and fresh test episodes. Use only those names afterwards.
- **Fix one evaluation per question.** Other evaluations go to an appendix robustness section.
- **Remove mismatches by recomputing, not by explaining them.** Do this from saved scores and activations, as new run folders. Never overwrite anything, and never change a pre-registered confirmation result.
- **Show confirmed vs exploratory by structure:** one sentence in Method, separate Results subsections, and figure markers. Do not repeat it in every sentence.
- **Keep provenance in `numbers.yaml`,** with every number written through a generated LaTeX macro. Provenance then has a proper home, and sentences no longer need to carry it.
- **Put analysis history in one appendix section,** stated once and completely.

Treat this as a design problem to solve in the plan, not something to patch while writing.

## 5. Repository and branch

1. **Work from a fresh clone of the public repo** (`github.com/leonidas1712/collusion-research`). Do not use the old local checkout. It still has history from before the rewrite, and pushing from it could restore what was removed.
2. **Create the `followup` branch from `main` and work only there.** Push to it freely.
3. **Do not commit to `main` until judging is over.** Judges clicking the repo link land on `main`, and it must keep matching the submitted PDF.
4. **Never move or delete the `apart-submission` tag.**
5. Put the new paper in `paper-arxiv/`, laid out as in `WRITING.md` §6. Leave the sprint `report/` folder untouched. Put `WRITING.md` and this brief at the repo root.

## 6. Tonight's work (overnight, unattended)

I'm asleep while you work. Make reasonable decisions, record them, and keep going. Do not stop to ask questions. Collect questions for the morning.

**The focus tonight is one thing:** a solid, rewritten arXiv-style LaTeX source and rendered PDF that we can keep working from. Everything you do should serve that. The follow-up experiments come later (§7).

### Phase 1: plan together (before writing any prose)
Discuss among yourselves and produce `paper-arxiv/PLAN.md`, covering:
- **The claims list** (`docs/claims.md`, per `WRITING.md` §7). Mark it "proposed," since I haven't signed off.
- **The new structure:** section-by-section outline as paragraph-opening sentences, and appendix sections as questions with one-line answers.
- **The dataset plan:** which named datasets, which single evaluation per question, which mismatches need recomputing, and how.
- **The figure plan:** the headline figure, what each figure answers, and whether each is new or adapted.
- **The notation:** what gets formally defined and what stays in words.
- **What gets cut or moved,** compared with the sprint version.
- **Where the follow-up results will slot in later** (see §7 below).
- **Who owns which files.** Exactly one writer per file at a time, plus one editor, plus one owner for `numbers.yaml`.

Run the blind outline review (`WRITING.md` §7, Step 3) before moving on.

### Phase 2: build the draft
1. Set up the ICLR template in `paper-arxiv/`, de-anonymised with `\iclrfinalcopy`.
2. Build `numbers.yaml` and the macro generator.
3. Do any recomputations.
4. Write the main text, then the appendix.
5. Make the figures.
6. Run the cut pass, the caveat audit and the number audit.

### Phase 3: review and iterate
1. Run the two blind reviews, clarity and rigour, from `WRITING.md` §8 on the compiled PDF.
2. Fix what they find, using the order of preference in `WRITING.md` §7.
3. Repeat until both pass, or until you are clearly getting diminishing returns.
4. **Check the rendered PDF in a real viewer, not just the CLI build.** Have an agent with computer use, ideally a Codex-harness agent, open `main.pdf` in Preview or a similar viewer. It should look through every page and confirm the file opens cleanly, with fonts, figures, math, tables and links all rendering properly. Do the same for a build compiled from the packaged arXiv source in a clean directory. `WRITING.md` §6 has the checklist.

**Do not game the reviews.** The rules are in `WRITING.md` §7. No pleasantries, no overstating, no priming the reviewer, no dropping required caveats. A good verdict is a useful signal. It is not the final judgement. I am.

## 7. Tomorrow and after

- **Tomorrow** I review the rewrite and the plan, sign off or change the claims list, and we revise.
- **After that,** we run the follow-up experiments (causal steering, Shi transfer) and add their results to this draft. Design the structure so they can slot in cleanly. For example, the Results section and figures should leave an obvious place for a "Does it generalise?" section and a "Is the direction causal?" section, without restructuring the paper. Do not write placeholder text for them in the draft itself. Just note the slots in `PLAN.md`.

## 8. What I want to find in the morning

On the `followup` branch, pushed:

1. `paper-arxiv/main.pdf`, building cleanly from source.
2. `paper-arxiv/PLAN.md` and `docs/claims.md` (proposed).
3. `paper-arxiv/numbers.yaml`, with every number traced to a run folder.
4. Any new run folders from recomputation, each with a one-line note on what it recomputes and why.
5. `paper-arxiv/HANDOVER.md`, which is short and contains:
   - what you did,
   - the main decisions you made and why,
   - every number that changed from the sprint version and why,
   - the final verdicts from the clarity and rigour reviews,
   - the result of the viewer check on both the local build and the packaged arXiv build,
   - open questions and decisions for me,
   - anything you were unsure about, or think I should look at first.

The goal is a draft I'm excited to review. It should keep all the rigour we already have and say it clearly. A fresh reader should find it easy and pleasant to read.
