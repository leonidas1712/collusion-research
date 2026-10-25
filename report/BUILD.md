# Render the full paper

From the repository root, use the bundled Python runtime (the root project environment does not include python-docx):

```sh
~/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python report/build_paper.py
```

Pandoc must be on PATH. The builder uses `--citeproc`, `report/references.bib`, the vendored `report/apa.csl`, and `--reference-doc=report/template.docx`. The CSL comes from https://github.com/citation-style-language/styles/blob/master/apa.csl (CC BY-SA 3.0; license is recorded in the file). It then formats native tables, restores the template's Old Standard TT font, and invokes the documents plugin's `render_docx.py` with the bundled LibreOffice renderer. It repairs Pandoc's missing content-type declaration for the template's embedded TTFs.

Outputs are `report/build/paper.docx` and `paper.pdf`. The build also saves the exact Markdown snapshot, source and image hashes, Pandoc log, page images for visual checks, extracted page text, and `paper.pagination.json`. Main-body pages are physical pages containing Title through Conclusion; a partially occupied final page counts. References and Appendix begin on fresh pages. Code and Data is reported separately. No prose is removed or shortened; source TODOs and editorial notes remain visible. Figures remain at their Markdown positions.

The build fails on missing references or unresolved citation markers. `--allow-missing-bibliography` is only for provisional layout work; it is not a submission-ready citation check. `--no-render` builds the DOCX only. Source, bibliography, CSL, template, output and renderer paths can be overridden with CLI arguments.

`build_docx.py` remains the earlier Methods-only layout exercise; use `build_paper.py` for the whole manuscript. The renderer reads a snapshot of the shared manuscript and records if another editor changes the source during the build. Rebuild after prose or figure changes and visually inspect the resulting pages before submission.

Visible reference URLs are retained as ordinary text because this bundled LibreOffice version adds a stray `X` when rendering OOXML hyperlinks. They are not clickable DOCX links. This changes no citation wording or URL.

For a section-by-section page budget after rendering:

```sh
~/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python report/page_budget.py
```

This uses `pdftotext` and writes `build/page_budget.md` and `.json`; its section spans include figures, tables and page-break whitespace. These spans estimate occupied space, not guaranteed savings from cuts.
