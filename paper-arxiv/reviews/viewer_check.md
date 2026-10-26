# Final PDF viewer check

Date: 2026-10-27 (Asia/Singapore)

## Final Round 2 inputs

| Build | Path | SHA-256 | Pages |
|---|---|---|---:|
| Canonical | `paper-arxiv/main.pdf` | `f99a4d7623aab3fa2bcd722c2087ac1458028a4090ee45c4aefbd0b9c19f0751` | 39 |
| Clean arXiv package | `paper-arxiv/dist/arxiv-final/clean-build/main.pdf` | `c8069cd70b85d4c465ebf30de5059b3587e9e7b2df610e9dd4256a87fec3a911` | 39 |
| arXiv source archive | `paper-arxiv/dist/arxiv-final/arxiv-source.tar.gz` | `77d1fda57b12e46571ac177a94d1a1480030247ab9160a165dd31c58339baad6` | - |

The hashes matched the handoff before inspection and remained stable afterward. This was the requested focused Round 2 re-check of the title/abstract page, Contents pages and links, and representative references. The earlier full 39-page visual pass applied to superseded Round 1 hashes and is not represented as a full visual pass on these artifacts.

## Round 2 checklist

| Check | Result | Evidence / defect |
|---|---|---|
| PDF parsing and focused rendering | **PASS** | Both 39-page PDFs parse with `pypdf` and render the checked pages with Poppler without errors. |
| Title and abstract, p. 1 | **PASS** | The title has the intended two-line break after the colon; “Probing When a Recruited Agent Gives In” remains on one line. The abstract, author block, first-page footnote, Introduction heading, and opening paragraphs are legible and inside the margins. No overlap or missing glyph was visible. |
| Link appearance, p. 1 | **PASS** | Citations and the Section O footnote link use dark-blue text without visible borders. |
| Contents appearance, pp. 13-14 | **PASS** | All 41 entries are legible, aligned, inside the margins, and use dark-blue linked text without visible borders. |
| Contents destinations | **PASS** | All 41 links resolve in order to the printed destination pages: `1, 2, 3, 4, 5, 5, 6, 7, 7, 8, 9, 15, 16, 17, 20, 21, 21, 22, 22, 24, 25, 25, 26, 28, 28, 29, 31, 31, 32, 32, 33, 33, 33, 34, 35, 35, 35, 36, 36, 37, 39`. |
| Representative citations and references | **PASS structurally** | First-page citation links resolve to bibliography pp. 10-12, and the footnote cross-reference resolves to Appendix O on p. 34. Sample reference URLs are non-empty. Across each PDF, all 329 annotations resolve: 280 internal and 49 external, with 0 missing or unsupported actions. |
| Canonical/package equivalence on checked pages | **PASS** | The 168-dpi PNGs for pp. 1, 13 and 14 are byte-identical between the canonical and clean-package PDFs. Link counts and destinations also match exactly. |
| Native macOS Preview | **UNVERIFIED** | The required retry failed before Preview opened with `Sky Computer Use service startup request failed`. No native open or click claim is made. |

## Overall gate

**PASS for the requested final Round 2 viewer re-check.** No defect was found on the title/abstract page, Contents pages, Contents destinations, or sampled reference links. Native macOS Preview remains explicitly unverified because the computer-use service could not start.
