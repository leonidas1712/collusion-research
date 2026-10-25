# Render the full paper

Install Python 3.11 or later, [uv](https://docs.astral.sh/uv/), Pandoc, LibreOffice, and Poppler. The commands `pandoc`, `soffice` (or `libreoffice`), `pdftoppm`, and `pdftotext` must be on PATH. Install the four vendored report/fonts/xcharter/*.otf files and Old Standard TT for consistent pagination. On macOS, copy the OTF files into ~/Library/Fonts/. Old Standard TT is also embedded in the reference document. Licenses and font alternatives are documented in report/fonts/README.md.

From the repository root:

```sh
uv run --with python-docx --with lxml --with pillow --with pypdf python report/build_paper.py
```

This command installs the Python dependencies in a temporary uv environment. It uses system LibreOffice in headless mode with an isolated temporary profile and Poppler for page images. It does not require Codex or a private runtime. Tested with Pandoc 3.12.1 and LibreOffice 26.2.5.2 on macOS. Font availability and renderer versions can change line breaks; check the generated page count and images on the submission machine.

The default layout is `balanced-xcharter`: 11pt XCharter body, 1.08 line spacing, justified text, 0.25in first-line indents except after headings/lists/figures/tables, and 0.9in margins. The title and headings retain Old Standard TT. `--paragraph-layout template` restores the original template body layout; other named alternatives are listed by `--help`.

Outputs are `report/build/paper.docx` and `paper.pdf`. The build also saves the exact Markdown snapshot, source and image hashes, Pandoc log, page images, extracted page text, and `paper.pagination.json`. Main-body pages are physical pages containing Title through Conclusion; a partially occupied final page counts. The fractional count measures the final body's occupied text-area height. References and Appendix begin on fresh pages. No prose is removed or shortened; source TODOs remain visible. Figures remain at their Markdown positions.

The builder uses Pandoc `--citeproc`, `report/references.bib`, the vendored `report/apa.csl`, and `--reference-doc=report/template.docx`. The CSL comes from https://github.com/citation-style-language/styles/blob/master/apa.csl (CC BY-SA 3.0; license recorded in the file). It formats native tables and applies the selected body-font layout. It also repairs Pandoc's missing content-type declaration for the template's embedded TTFs. The builder enables Pandoc citation links, places reference bookmarks inside their paragraphs for correct PDF destinations, and preserves internal citation hyperlinks. It defines the Pandoc paragraph styles absent from the template, which prevents LibreOffice from adding stray `X` characters to linked paragraphs. In-text citation links, linked cross-references and bibliography URLs use navy (#000080), without underlines or PDF annotation borders, and remain clickable. The template’s title footnote retains its original hyperlink.

The build fails on missing references or unresolved citation markers. `--allow-missing-bibliography` is for provisional layout work only. `--no-render` builds DOCX only. Source, bibliography, CSL, template and output paths can be overridden. `--renderer /path/to/render_docx.py` optionally uses a compatible external renderer accepting `INPUT --output_dir DIR --emit_pdf`; its dependencies must be available to the same Python interpreter.

For the section-by-section page budget after rendering:

```sh
uv run --with python-docx --with lxml --with pillow --with pypdf python report/page_budget.py
```

This writes `build/page_budget.md` and `.json`; section spans include figures, tables and page-break whitespace. These estimate occupied space, not guaranteed savings from cuts.

`build_docx.py` holds the table and cell formatting helpers that `build_paper.py` imports, so keep it next to the builder. Run on its own, it builds only an early Methods draft for layout testing; use `build_paper.py` for the whole manuscript. The builder records whether the source changed while building. Rebuild after prose or figure changes and visually inspect the pages before submission.


## Template fidelity checks

`template_layout.py` reuses the template’s native ruled title block, the author/affiliation layout, “With / Apart Research”, italic narrow abstract, and title footnote. It applies the actual direct heading formatting (14-point bold main headings and 13-point bold subheadings) and an unnumbered alphabetical bibliography with hanging indents. The title preserves the casing in paper.md. Captions and data tables use 9-point body-family text, single-spaced. In the template and Old Standard variants, κ uses Arial because Old Standard TT lacks it. The numeric template audit will show intentional body-font, spacing and margin differences for the default balanced layout.

To reproduce the numeric comparison and citation-link verification after building:

```sh
mkdir -p report/build/template-check
soffice --headless --convert-to pdf --outdir report/build/template-check report/template.docx
uv run --with python-docx --with lxml --with pypdf python report/audit_template.py
uv run --with lxml --with pypdf python report/check_citation_links.py
```

The audit writes `template-check/audit.md`, JSON, and `pdffonts` evidence. Citation verification checks every in-text link’s reference page and its destination within 20 points of the correct entry. Multi-line link rectangles are grouped before comparison. The audit uses `pdffonts` and the link check uses `pdftotext`, both from Poppler. The manuscript’s current placeholders remain visible; these are review renders, not a claim of submission readiness.

## PDF compatibility

The default requests LibreOffice PDF/A-2b export using standalone XCharter OTF fonts. The XCharter export was visually confirmed in Acrobat after system Charter's italic subset displayed an incorrect glyph there. Poppler, MuPDF and PDFium did not reproduce the system-Charter defect. Font rendering and PDF/A conformance are separate checks: the export has not been independently certified as PDF/A compliant.

Use `--no-pdfa` for ordinary PDF export. `--paragraph-layout balanced-charter` retains the earlier system-Charter comparison (10.5pt, 1.05 spacing); `balanced-charis` is another diagnostic font alternative. All balanced layouts use 0.9in margins. PDF/A still subsets fonts.

## Prompts, lists and cross-references

Put each verbatim prompt in a separate fenced div. Keep its label outside:

```markdown
Recruiting peer:

::: {.prompt}

Verbatim prompt text.

:::
```

Prompt blocks use 9.5pt text, light grey shading, ragged-right alignment and no
first-line indent. Their punctuation is preserved literally; smart punctuation
remains enabled in prose. Markdown lists still need a blank line before them.
Lists and paragraphs containing paths or URLs are ragged-right. Body paragraphs
immediately after a heading, list or table have no first-line indent. Table
captions have space after them and remain attached to their own table.

`paper_crossrefs.py` links explicit references such as `Appendix D`, `Section 5`,
`§4.3`, `Figure 1` and `Table C.1` to numbered headings and captions. It leaves
visible numbering under the author's control and does not rewrite prompt text,
code, citations or existing links. The build manifest records the targets and
links. Caption labels must be unique.

The link audit accepts a non-default build location:

```sh
uv run --with lxml --with pypdf python report/check_citation_links.py --stem report/build/crossref-review/paper
```

It verifies DOCX bookmarks and that every referenced destination has a PDF link
landing within 20 points of the corresponding text. It checks destinations,
not whether every wrapped clickable rectangle covers precisely the visible text.
