# Reference check protocol (independent checkers)

Each checker works alone and writes only to `private/refcheck_<checker>.md`. Do not read other checkers' files or post findings on the board; post only "refcheck done".

Inputs: `report/references.bib` (all entries) and `report/paper.md` (every place each key is cited, as `[@key]` or `@key`).

For EVERY bib entry:
1. **Exists:** open the arXiv abs page or URL. Does it resolve to this work?
2. **Metadata:** do the exact title, the full author list (order and spelling) and the year match the source page? Does the arXiv ID match?
3. **Use:** for each sentence in paper.md that cites it, state the claim we attribute to it and whether the source supports it. Quote the supporting sentence from the abstract, or from the full text if the abstract isn't enough (fetch the paper). Flag any overstatement, e.g. "X show..." when X only suggest it, or "first to..." claims.
4. **Verdict:** OK / FIX (say exactly what) / CAN'T VERIFY (say why). Never guess.

Also list: any in-text citation without a bib entry, any bib entry never cited, and any factual claim in the text attributed to prior work without a citation.

Output: a table with one row per entry (key, exists, metadata, use, verdict, evidence quote/URL), then a short list of FIX items, most important first.
