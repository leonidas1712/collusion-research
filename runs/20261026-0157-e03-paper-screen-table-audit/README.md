# Screening-table audit

Reproduce the saved `summary.json` with Python 3.11 or later, from the repository root:

```sh
python experiments/E03-target-screen/paper_screen_table_audit.py --check
```

The audit verifies the SHA-256 hashes of all 396 source episodes against
`report/figures/appendix_g_manifest.json`, then independently aggregates the 608
episode-factor records in `appendix_g_episodes.csv` into the 81 cells of
`appendix_g_coverage.csv`. It checks attempted, analysed, give-in, channel-give-in,
complete, incomplete, never-read, other-invalid and held counts. Reused reference
episodes occur in more than one factor; records are unique within a factor cell.
This checks saved eligibility decisions and counts, not a new semantic judgement
or a rerun of the episode scorer.

The final check matches the compact table's 21 Markdown lines (19 data rows,
header and separator) against `manuscript_table.md`. That file contains the exact
lines extracted from `report/paper.md` at revision
`0eb6521feab1c3dd7a8173d1e44cf2b6411be556`, the revision recorded by the original
audit. The current paper has presentation edits, so it is not the default input.
The saved excerpt lets this check run in a shallow clone. To check the historical
full manuscript instead, add:

```sh
--paper-revision 0eb6521feab1c3dd7a8173d1e44cf2b6411be556
```

The raw episode files must be available locally under their manifest paths. A
missing file or changed hash fails the audit; no source verification is skipped.
`--episode-root`, `--figures`, `--paper`, `--reference` and `--output` permit
explicit alternative inputs and a saved JSON result.

The script reconstructs the checks from the saved inputs and output, and its
`--check` result matches every field of the original summary. The original
`meta.json`, `log.txt` and `diff.patch` retain the initial stdin-run provenance;
they are not regenerated or rewritten.
