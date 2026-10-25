# Saved disclosure-kind metadata join

Matched all 200 first-public-emission judgments to the 360-episode canonical manifest by path and SHA256. No API call, primary-label change or eligibility change was made.

The judge describes the first public emission, usually a file write; it does not necessarily judge the later channel publication and does not establish internal intent. The activation cache leaves kind null; analyses needing this sensitivity must join episode_kinds.json on episode and verify episode_sha256. Episodes without a public emission are absent from the judgment table, not assigned an inferred kind. Two saved labels are null; the report calls these uncertain, matching the source judge report.

Counts: {"deliberate": 198, "uncertain": 2}. Channel-positive episode kinds: {"deliberate": 127, "uncertain": 1}.
