# Render the full paper

Install Python 3.11 or later, [uv](https://docs.astral.sh/uv/), Pandoc, LibreOffice, and Poppler. The commands `pandoc`, `soffice` (or `libreoffice`), `pdftoppm`, and `pdftotext` must be on PATH. Install the Old Standard TT font for consistent pagination; the reference document also contains embedded fonts.

From the repository root:

```sh
uv run --with python-docx --with lxml --with pillow --with pypdf python report/build_paper.py
```

This command installs the Python dependencies in a temporary uv environment. It uses system LibreOffice in headless mode with an isolated temporary profile and Poppler for page images. It does not require Codex or a private runtime. Tested with Pandoc 3.12.1 and LibreOffice 26.2.5.2 on macOS. Font availability and renderer versions can change line breaks; check the generated page count and images on the submission machine.

Outputs are `report/build/paper.docx` and `paper.pdf`. The build also saves the exact Markdown snapshot, source and image hashes, Pandoc log, page images, extracted page text, and `paper.pagination.json`. Main-body pages are physical pages containing Title through Conclusion; a partially occupied final page counts. The fractional count measures the final body's occupied text-area height. References and Appendix begin on fresh pages. No prose is removed or shortened; source TODOs remain visible. Figures remain at their Markdown positions.

The builder uses Pandoc `--citeproc`, `report/references.bib`, the vendored `report/apa.csl`, and `--reference-doc=report/template.docx`. The CSL comes from https://github.com/citation-style-language/styles/blob/master/apa.csl (CC BY-SA 3.0; license recorded in the file). It formats native tables and restores the template's Old Standard TT font. It also repairs Pandoc's missing content-type declaration for the template's embedded TTFs. Visible reference URLs are preserved as ordinary text because one LibreOffice build adds a stray `X` to OOXML hyperlinks; they are not clickable DOCX links.

The build fails on missing references or unresolved citation markers. `--allow-missing-bibliography` is for provisional layout work only. `--no-render` builds DOCX only. Source, bibliography, CSL, template and output paths can be overridden. `--renderer /path/to/render_docx.py` optionally uses a compatible external renderer accepting `INPUT --output_dir DIR --emit_pdf`; its dependencies must be available to the same Python interpreter.

For the section-by-section page budget after rendering:

```sh
uv run --with python-docx --with lxml --with pillow --with pypdf python report/page_budget.py
```

This writes `build/page_budget.md` and `.json`; section spans include figures, tables and page-break whitespace. These estimate occupied space, not guaranteed savings from cuts.

`build_docx.py` is the Methods-only layout exercise; use `build_paper.py` for the whole manuscript. The builder records whether the source changed while building. Rebuild after prose or figure changes and visually inspect the pages before submission.
