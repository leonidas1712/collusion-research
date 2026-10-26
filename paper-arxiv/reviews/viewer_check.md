# Final PDF viewer check

Date: 2026-10-27 (Asia/Singapore)

## Inputs

| Build | Path | SHA-256 | Pages |
|---|---|---|---:|
| Canonical | `paper-arxiv/main.pdf` | `38d66cdb57b14faa28b54455144d48f947d48406698b7cb0b5eb7ed988dd71e1` | 39 |
| Clean arXiv package | `paper-arxiv/dist/arxiv-final/clean-build/main.pdf` | `c982b92e9b9a24085796a7714a9d2728632e2bd86c4a43ba60c83d69c9b97e93` | 39 |
| arXiv source archive | `paper-arxiv/dist/arxiv-final/arxiv-source.tar.gz` | `697a8d40574f3a297407e45ccea815c0a4b13bfaf461b3a9ffd0be73ad48d30f` | - |

The file hashes were checked before and after inspection and remained stable. The two PDFs have identical extracted text. Rendering every page at 144 dpi produced byte-identical PNGs for all 39 canonical/package page pairs.

## Checklist

| Check | Result | Evidence / defect |
|---|---|---|
| Opens without errors or warnings | **PASS in independent PDF renderers; UNVERIFIED in Preview** | Both PDFs parse with `pypdf` and `pdftotext` and render with Poppler without errors. The final macOS Preview retry failed before the app opened with `Sky Computer Use service startup request failed`; no native-Preview claim is made. |
| Fonts and glyphs | **PASS** | Every listed font resource is embedded and subset in both PDFs. Pages 1-39 show no missing-glyph boxes or substitutions. |
| Figures sharp at normal inspection scale | **PASS** | All figures are sharp and legible; line work, markers, legends, error bars, labels, and raster elements render cleanly. |
| Math and tables | **PASS** | Display math and all tables, including the policy-counterfactual table on p. 28, render without clipping, overlap, broken rules, or illegible symbols. |
| Link appearance | **PASS** | Internal references, citations, and URLs use dark-blue text with no visible link borders. |
| Contents links | **PASS structurally** | All 41 Contents links on pp. 13-14 resolve, in order, to their printed destination pages: 1-9 and 15-39 as listed. No destination is missing or out of range. |
| Cross-references and citations | **PASS structurally** | Each PDF has 326 valid link annotations: 277 internal and 49 external, with 0 missing or unsupported actions. Representative first-page citations resolve to the bibliography, cross-references resolve internally, and external reference URLs are non-empty. Native click interaction remains unverified because Preview did not start. |
| No overflow or overlap | **PASS** | Every page was inspected. No text, figure, table, header, footer, or annotation runs off the page or overlaps other content. |
| Canonical/package equivalence | **PASS** | All 39 raster page pairs are byte-identical; extracted text is identical; page, font, and link counts match. |
| Placeholder scan | **PASS** | Extracted text contains no `??`, `Undefined`, `TODO`, `PENDING`, or `[?]` markers. |

## Page-by-page inspection log

| Pages | Result | Notes |
|---|---|---|
| 1-4 | PASS | Title/footnote, abstract, introduction, setup, definitions, early figures and tables. |
| 5-9 | PASS | Results, deployment-cost discussion, related work, discussion, limitations, and usage statement. |
| 10-12 | PASS | References; linked text and URLs remain within margins. |
| 13-14 | PASS | Contents; all 41 entries are legible and mechanically resolve to the printed pages. |
| 15-20 | PASS | Appendices A-D; scenario, intervention, behaviour, intent, and pressure material. |
| 21-27 | PASS | Probe, monitor, transfer, calibration, and exploratory analyses; figures and tables remain legible. |
| 28 | PASS | Policy counterfactual table is readable, aligned, and inside the margins. |
| 29-34 | PASS | Remaining analyses, histories, settings, provenance, and generated tables. |
| 35-39 | PASS | Verbatim scenario and monitor prompts; monospace text, bullets, and nested lists remain inside margins. |

## Overall gate

**PASS for every executable visual, structural, equivalence, and link-destination check. Native macOS Preview remains explicitly unverified because the computer-use service could not start.** No PDF defect was found in either final artifact.
