# Channel-only per-call feasibility

The matched gpt-oss cohort contains 1,995 calls from 238 recruiting episodes, including 121 first emissions by any public route. Only **3 calls** are first channel publications. The saved y_channel flag exactly matches request_idx == first_channel_request_idx.

Although 96 represented episodes eventually publish to the channel, their channel-publication calls mostly occur after the earlier file emission that ends this cohort. Labelling those earlier file calls as channel publications would be incorrect. Three positives, spread across only three scenarios, cannot support the requested six-scenario nested held-out-scenario fit. No fits were run.

All 96 first-channel calls from these represented episodes do exist in the broader saved last-prompt activation cache. A channel-only analysis could therefore use an expanded post-read window through the first channel publication without new GPU replay, but it would be a different cohort and would admit calls after an earlier file disclosure. It would require a declared window and eligibility rule rather than being a same-call harmonisation check.

Sources: runs/20261026-0522-e05-reasoning-stream-data/replies.json; runs/20261025-2305-e05-gpt-oss-full-data/rows.jsonl. counts.json records coverage and positive call identifiers. Script: experiments/E05-probes/channel_percall_feasibility.py.
