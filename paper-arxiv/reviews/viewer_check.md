# Final PDF viewer check

Date: 2026-10-27 (Asia/Singapore)

## Final E11 inputs

| Build | Path | SHA-256 | Pages |
|---|---|---|---:|
| Canonical | `paper-arxiv/main.pdf` | `497834a0daf5a3110b81022adae4a33dd1c7c032edfe635d06f3260c91b93663` | 41 |
| Clean arXiv package | `paper-arxiv/dist/arxiv-final/clean-build/main.pdf` | `7feb4b52aebb6f39a254612c253242c293dfb114d427b97b772f2b15fdefe6b8` | 41 |
| arXiv source archive | `paper-arxiv/dist/arxiv-final/arxiv-source.tar.gz` | `48aa905ac569515d1c2899745811495ed0d7219de9b1ddbe447dd44aedd95de0` | - |

The hashes matched the handoff before inspection and remained stable afterward. Both PDFs were rendered in full at 144 dpi.

## Checklist

| Check | Result | Evidence / defect |
|---|---|---|
| Opens without errors or warnings | **PASS in independent PDF renderers; UNVERIFIED in Preview** | Both PDFs parse with `pypdf` and `pdftotext` and render all 41 pages with Poppler without errors. The final macOS Preview retry failed before the app opened with `Sky Computer Use service startup request failed`; no native-Preview claim is made. |
| Fonts and glyphs | **PASS** | All 29 listed font resources are embedded and subset in both PDFs. Pages 1-41 show no missing-glyph boxes or substitutions. |
| Figures sharp | **PASS** | All figures are sharp and legible; line work, markers, legends, error bars, labels, and raster elements render cleanly. |
| Math and tables | **PASS** | Display math and all tables render without clipping, overlap, broken rules, or illegible symbols. The new E11 table on p. 27 is aligned, readable, and inside the margins. |
| Link appearance | **PASS** | Internal references, citations, and URLs use dark-blue text with no visible link borders. |
| Contents appearance and links | **PASS** | The 41 entries on pp. 14-15 are legible and aligned. Every link resolves in order to its printed destination page: `1, 2, 3, 4, 5, 5, 6, 7, 7, 8, 9, 16, 17, 18, 21, 22, 22, 23, 23, 25, 26, 26, 28, 29, 30, 30, 33, 33, 33, 33, 33, 35, 35, 35, 36, 36, 37, 37, 38, 39, 40`. |
| Cross-references and citations | **PASS structurally** | Each PDF has 340 valid link annotations: 288 internal and 52 external, with 0 missing or unsupported actions. First-page citations resolve to bibliography pp. 10-13, the first-page Section O link resolves to p. 35, and sampled reference URLs are non-empty. Native click interaction remains unverified because Preview did not start. |
| No overflow or overlap | **PASS** | Every page was inspected. No text, figure, table, header, footer, or annotation runs off the page or overlaps other content. The short final bibliography page (p. 13) and final prompt page (p. 41) have intentional white space. |
| Canonical/package equivalence | **PASS** | All 41 canonical/package raster page pairs are byte-identical; extracted text is identical; page, font, and link counts match. |
| Placeholder scan | **PASS** | Extracted text contains no `??`, `Undefined`, `TODO`, `PENDING`, or `[?]` markers. |

## Page-by-page inspection log

| Pages | Result | Notes |
|---|---|---|
| 1-4 | PASS | Title/footnote, abstract, introduction, setup, definitions, Figures 1-2, and Table 1. |
| 5-9 | PASS | Method, main results, Figures 3-5, Tables 2, related work, discussion, and limitations. |
| 10-13 | PASS | Usage statement and complete references; linked URLs remain inside margins. Page 13 ends the bibliography with intentional white space. |
| 14-15 | PASS | Contents; all 41 entries are legible and mechanically resolve to their printed pages. |
| 16-21 | PASS | Appendices A-C, scenario/rule tables, episode excerpts, dataset checks, replay fidelity, settings, and probe-training setup. |
| 22-26 | PASS | Probe metric, monitor setup/results, frozen fresh tests, robustness tables, and Figure 6. |
| 27 | PASS | New E11 table and surrounding shortcut/input-text analysis are clean, aligned, and within margins. |
| 28-32 | PASS | Figures 7-9, policy counterfactual, alarm trade-offs, and round-level results/robustness tables. |
| 33-36 | PASS | Leak routes, screens, dual-use discussion, analysis history, and reproducibility index. |
| 37-41 | PASS | Verbatim target, peer, and monitor prompts; monospace text, bullets, and nested lists remain within margins. Page 41 ends with intentional white space. |

## Overall gate

**PASS for every executable visual, structural, equivalence, and link-destination check on the final E11 artifacts. Native macOS Preview remains explicitly unverified because the computer-use service could not start.** No PDF defect was found in either final artifact.
