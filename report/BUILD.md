# Render the full paper

Install Python 3.11 or later, [uv](https://docs.astral.sh/uv/), Pandoc, LibreOffice, and Poppler. The commands `pandoc`, `soffice` (or `libreoffice`), `pdftoppm`, and `pdftotext` must be on PATH. Install the Old Standard TT font for consistent pagination; the reference document also contains embedded fonts.

From the repository root:

```sh
uv run --with python-docx --with lxml --with pillow --with pypdf python report/build_paper.py
```

This command installs the Python dependencies in a temporary uv environment. It uses system LibreOffice in headless mode with an isolated temporary profile and Poppler for page images. It does not require Codex or a private runtime. Tested with Pandoc 3.12.1 and LibreOffice 26.2.5.2 on macOS. Font availability and renderer versions can change line breaks; check the generated page count and images on the submission machine.

Outputs are `report/build/paper.docx` and `paper.pdf`. The build also saves the exact Markdown snapshot, source and image hashes, Pandoc log, page images, extracted page text, and `paper.pagination.json`. Main-body pages are physical pages containing Title through Conclusion; a partially occupied final page counts. The fractional count measures the final body's occupied text-area height. References and Appendix begin on fresh pages. No prose is removed or shortened; source TODOs remain visible. Figures remain at their Markdown positions.

The builder uses Pandoc `--citeproc`, `report/references.bib`, the vendored `report/apa.csl`, and `--reference-doc=report/template.docx`. The CSL comes from https://github.com/citation-style-language/styles/blob/master/apa.csl (CC BY-SA 3.0; license recorded in the file). It formats native tables and restores the template's Old Standard TT font. It also repairs Pandoc's missing content-type declaration for the template's embedded TTFs. The builder enables Pandoc citation links, places reference bookmarks inside their paragraphs for correct PDF destinations, and preserves internal citation hyperlinks. It defines the Pandoc paragraph styles absent from the template, which prevents LibreOffice from adding stray `X` characters to linked paragraphs. Bibliography URLs remain clickable. The template’s title footnote retains its original hyperlink.

The build fails on missing references or unresolved citation markers. `--allow-missing-bibliography` is for provisional layout work only. `--no-render` builds DOCX only. Source, bibliography, CSL, template and output paths can be overridden. `--renderer /path/to/render_docx.py` optionally uses a compatible external renderer accepting `INPUT --output_dir DIR --emit_pdf`; its dependencies must be available to the same Python interpreter.

For the section-by-section page budget after rendering:

```sh
uv run --with python-docx --with lxml --with pillow --with pypdf python report/page_budget.py
```

This writes `build/page_budget.md` and `.json`; section spans include figures, tables and page-break whitespace. These estimate occupied space, not guaranteed savings from cuts.

`build_docx.py` holds the table and cell formatting helpers that `build_paper.py` imports, so keep it next to the builder. Run on its own, it builds only an early Methods draft for layout testing; use `build_paper.py` for the whole manuscript. The builder records whether the source changed while building. Rebuild after prose or figure changes and visually inspect the pages before submission.


## Template fidelity checks

`template_layout.py` reuses the template’s native ruled title block, the author/affiliation layout, “With / Apart Research”, italic narrow abstract, and title footnote. It applies the actual direct heading formatting (14-point bold main headings and 13-point bold subheadings) and numbered reference layout. The title text is unchanged, with all-capitals display. Captions and data tables have no template example; both use 9-point Old Standard TT, single-spaced. The κ glyph uses Arial explicitly because the installed Old Standard TT lacks it; Arial is also embedded in the template.

To reproduce the numeric comparison and citation-link verification after building:

```sh
mkdir -p report/build/template-check
soffice --headless --convert-to pdf --outdir report/build/template-check report/template.docx
uv run --with python-docx --with lxml --with pypdf python report/audit_template.py
uv run --with lxml --with pypdf python report/check_citation_links.py
```

The audit writes `template-check/audit.md`, JSON, and `pdffonts` evidence. Citation verification checks every in-text link’s reference page and its destination within 20 points of the correct entry. Multi-line link rectangles are grouped before comparison. The audit uses `pdffonts` and the link check uses `pdftotext`, both from Poppler. The manuscript’s current placeholders remain visible; these are review renders, not a claim of submission readiness.
