# Release history provenance

History was rewritten on 26 October 2026 to remove bulk run data, internal agent configuration, and historical caches, prompts and patches. Bulk run data are in the data-v1 release.

`commit-map.txt` is git-filter-repo's original-to-release commit map. Repository commit references in ordinary text were updated; byte-preserved frozen and SHA-256-linked records retain their original identifiers. Resolve those identifiers through this map. An all-zero destination denotes a removed commit. External repository commits and model revisions are not translated.

`byte-preserved.json` records the retained files and their original SHA-256 hashes. These files were not edited during remapping. The confirmation plan and weights still equal the blobs in the mapped pre-collection freeze commit; their verification checks were retained.
