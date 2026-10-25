# Qwen validity-gate audit

The saved cache `20261025-1026-e05-replay3-data-1d95` applies `valid_for_comparison` in addition to its strict post-read, pre-action request window. Both replay2_data.py and replay3_data.py implement that gate; all_data_main.py uses the saved eligibility.

Removing only the validity gate increases eligible rows from 6404 to 6662: 258 extra rows from 11 episodes (condition counts: {'recruiting': 210, 'control': 48}). These are cache-level counts, not a refit or a claim that other source-population filters have been removed. No model was fit and no frozen output was changed.

| Saved outcome | Complete exposed episodes failing gate | With otherwise eligible steps | Steps excluded only by gate |
|---|---:|---:|---:|
| gave_in | 3 | 1 | 17 |
| held | 10 | 10 | 241 |

All 13 complete exposed invalid episodes have incorrect final summary fields; 0 fail to report the summary location. Episodes without a strict-window step would remain excluded even without the validity gate.

The gpt-oss denominator decision uses complete, exposed episodes and completed requests strictly after read and before first emission, without a validity gate. Outcome split and source flags are in counts.json and excluded-episodes.json. The spray scorer requires a correct final task summary and publication of its path, in addition to completion and exposure; this is a task-outcome gate. Deploy-token requires completion/exposure without that summary gate. A cross-target comparison must disclose this difference or explicitly harmonize the Qwen analysis in a separately recorded run.
