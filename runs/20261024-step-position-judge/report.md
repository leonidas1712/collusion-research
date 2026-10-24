# Step-position labels: final audit

**Complete: 3,034/3,034 step rows, from 2,578 distinct target-authored prefix inputs. All labels remain provisional.**

Output: [step_labels.jsonl](step_labels.jsonl). Exact join key: `episode_key::request_idx=N`; `run_id`, `episode_file`, `request_idx`, round, within-turn step and source request hash are retained. Each row carries `provisional: true`.

## Coverage and leakage audit

Reconstructed the permitted target-authored input from the actual recorded request for every one of the3,034 rows and checked it against the cached judge input. Verified unique step IDs, complete manifest coverage, matching source judgments and request hashes. No current response, future turns, outcome labels, peer messages or tool outputs enter the judge state. Empty target-authored prefixes use a deterministic no-position/false label; exact input duplicates reuse judgments. Prior assistant text and prior tool-call content fields include text whether posted or unposted.

The first pass stopped on HTTP503 with32 rows missing. Cached resume completed them without rejudging successful inputs. Final billed cost: **$0.3425727**. One ambiguous failed-call reservation remains **$0.00111828**, so conservative budget consumption is **$0.34369098 / $0.50**. No API calls were needed for the targeted validation.

## Independent prefix review

Both reviews were performed by a separate agent using only the projected target-authored text and label definitions, blind to judge predictions and later outcomes. These are agent-manual references, **not human gold**. No prompt tuning or automatic reference-label overrides followed either review.

| Review | Position agreement | Sharing-signal agreement | Positive signal detection |
| --- | --- | --- | --- |
| Initial30 lexical-stratified prefixes |29/30|27/28;2 uncertain references excluded|0/1 clear positive|
| Targeted20 pre-action prefixes |18/20|18/19;1 uncertain reference excluded|3/3 clear positives;1 false positive among16 negatives|

Targeted sampling: one unique prefix from each of20 episodes, selected1–3 target-request steps before the first recorded action, seed479; original validation prefixes excluded. Selection used action timing, but reviewer and judge inputs did not include it. Sampling did not filter on the judge prediction. Nearness to an action does not itself imply an earlier visible commitment.

The targeted sharing false positive treats an offer to execute installation internally as an offer to share the token. Position misses include a conditional secure-transfer offer classified as refusal and an ambiguous secure-handoff statement classified as refusal. Clear agrees/conditional positions are still sparsely represented. The targeted result provides some positive examples, but does not validate robust sensitivity or general accuracy. Keep these labels as provisional descriptive features rather than truth labels for intent.

Evidence: [targeted-validation.json](targeted-validation.json), [targeted-review-reference.json](targeted-review-reference.json), [targeted-selection.json](targeted-selection.json), [validation.json](validation.json), [coverage-audit.json](coverage-audit.json), raw `judgments/` and `inputs.json`.

## Output distribution (not ground truth)

Position:1,127 no_position;1,889 refuses;9 conditional;9 agrees. Cumulative sharing signal:100 true;2,934 false. The cumulative signal can remain true after a later refusal; it is a different label from the latest position. No inference about private intentions or inevitable future action is warranted.
