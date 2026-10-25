# Citation style

Author–year, as in ICLR / ICML / NeurIPS papers, used the same way throughout.

## In-text forms (pandoc syntax in `report/paper.md`)

| Form | Write | Renders as |
|---|---|---|
| Parenthetical (default for supporting citations) | `[@fomin2026]` | (Fomin et al., 2026) |
| Several sources (semicolons, chronological order) | `[@fomin2026; @gao2026]` | (Fomin et al., 2026; Gao, 2026) |
| With a prefix | `[e.g., @fish2024]` | (e.g., Fish et al., 2024) |
| Narrative (the paper is the subject, as in most of Related Work) | `@fomin2026 show that…` | Fomin et al. (2026) show that… |

Author counts: one author "Gao (2026)"; two "Arike and Smith (2026)"; three or more "Fomin et al. (2026)". Same authors and year: 2026a, 2026b (citeproc does this automatically).

Keys: `firstauthorsurname` + year + optional first title word if needed, lower case (e.g. `gao2026`, `shi2026persuasion`).

## Reference list

- `report/references.bib`. Get each entry from the paper's arXiv "Export BibTeX citation" link so authors, title and ID are exact.
- The list is alphabetical by first author and not numbered; citeproc builds it under `# References`.
- Each entry has authors, year, title, venue (or "arXiv preprint arXiv:XXXX.XXXXX"), and a URL or DOI.
- Non-paper sources (vendor docs, repos, incident reports): author or organisation, year, title, URL (`@misc`).

## Rendering

```
pandoc report/paper.md --citeproc --bibliography=report/references.bib --csl=<apa.csl> --reference-doc=<Apart template .docx> -o report/build/paper.docx
```

Check the rendered file: no `[@key]` or "???" left, the reference list is complete and alphabetical, then export to PDF.

## Checks

- Every cited work is verified against its arXiv or source page (authors, title, ID). No unverified references.
- Every entry in the list is cited in the text, and every in-text citation has an entry.
- No numbered "[12]"-style citations, and no bare arXiv IDs in prose.
