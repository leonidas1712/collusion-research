# Final PDF viewer check

Date: 2026-10-26 (Asia/Singapore)

## Inputs

| Build | Path | SHA-256 | Pages |
|---|---|---|---:|
| Canonical | `paper-arxiv/main.pdf` | `48e6929dcd0fcc177e70816c4a51ac4f6d9103574896dace57e54f58a2e1fdea` | 33 |
| Clean arXiv package | `paper-arxiv/dist/arxiv-final/clean-build/main.pdf` | `c56fae86fbdc53533bd2e682e5e456b66d60b4844137c0dab0a5a3d357400f41` | 33 |

The two files have identical extracted text. Rendering every page at 120 dpi also produced identical page images for all 33 page pairs.

## Checklist

| Check | Result | Evidence / defect |
|---|---|---|
| Opens without errors or warnings | **BLOCKED in Preview; PASS in independent PDF renderers** | Four attempts to start macOS Preview through the computer-use service failed with `Sky Computer Use service startup request failed`, before either file could be opened. Both PDFs parse with `pdfinfo`, `pypdf`, `pdftotext`, and Poppler rendering without errors. |
| Fonts and glyphs | **PASS in rendered-page inspection** | All 26 font resources are embedded and subset. Pages 1-33 show no missing-glyph boxes or odd substitutions. Native Preview confirmation remains blocked as above. |
| Figures sharp at normal zoom | **PASS in rendered-page inspection** | Figures 1-7 on pp. 2, 4, 6, 20, 22-24 are sharp and legible; line work, markers, legends, error bars, and labels render cleanly. |
| Math and tables | **PASS in rendered-page inspection** | Display math on pp. 3 and 5 and Tables 1-25 render without clipping, overlap, broken rules, or illegible symbols. |
| Hyperlinks display correctly | **PASS in rendered-page inspection** | The initial build's colored borders were fixed and both PDFs rebuilt. Internal references, citations, and URLs now use one dark-blue text color with no visible borders. |
| Cross-references and citations are clickable | **PASS structurally; BLOCKED for Preview click test** | Both PDFs contain the same 250 valid link annotations: 201 internal and 49 external, with 0 missing/unsupported actions. The native Preview click test could not run because the viewer service did not start. |
| No overflow or overlap | **PASS in rendered-page inspection** | Pages 1-33 were inspected page by page. No text, figure, table, header, footer, or annotation runs off the page or overlaps other content. |
| Canonical/package equivalence | **PASS** | All 33 raster page pairs are pixel-identical; extracted text is identical; page and link counts match. |

## Page-by-page inspection log

| Pages | Result | Notes |
|---|---|---|
| 1-2 | PASS | Title, abstract, introduction, Figure 1. |
| 3-4 | PASS | Table 1, formal definitions, Figure 2. |
| 5-6 | PASS | Table 2, equation, Figure 3. |
| 7-8 | PASS | Related work, limitations, usage statement, start of references. |
| 9-11 | PASS | References; URLs remain inside margins. Page 11 ends the bibliography with intentional white space. |
| 12-14 | PASS | Appendix A-C; Tables 3-7. |
| 15-16 | PASS | Tables 8-10 and probe method text. |
| 17-19 | PASS | Tables 11-14 and monitor details. |
| 20-22 | PASS | Figures 4-5; Tables 15-17. |
| 23-25 | PASS | Figures 6-7; Tables 18-20. |
| 26-28 | PASS | Tables 21-24; risk and analysis-history sections. |
| 29-31 | PASS | Table 25 and verbatim prompt material. |
| 32-33 | PASS | Monitor prompt continuation and decision-model prompts. |

## Overall gate

**CONDITIONAL PASS: all executable visual and structural checks pass; native Preview is blocked by infrastructure.** The canonical and clean-package builds are visually clean, structurally valid, and mutually equivalent. The colored-border defect found in the first build is fixed in these final hashes. The only incomplete checklist item is a genuine macOS Preview open-and-click pass, because the computer-use service could not start after four attempts.
