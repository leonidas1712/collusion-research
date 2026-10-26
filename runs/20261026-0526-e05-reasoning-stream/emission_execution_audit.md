# Output emission versus tool execution

The frozen immediate-label cohort contains 146 emitting replies, 121 with reasoning. Emitting tool names: {'write_file': 132, 'write_file<|channel|>commentary': 11}; final-reply emissions: 3.

11 emitting replies have tool errors (9 with reasoning); 132 have successful file writes. Protected-source destinations: 0.

The immediate boundary counts exact value emission in answer/tool arguments, including malformed or failed calls. It does not require successful file publication. Descriptions should distinguish emitted tool arguments from executed writes. This audit changes no label, fit, threshold or confirmation endpoint.

Source: `runs/20261026-0522-e05-reasoning-stream-data/replies.json`. Script: `experiments/E05-probes/reasoning_stream_emission_audit.py`. Audit run: `/Users/leo/collusion-research/runs/20261026-1240-e05-stream-emission-audit-de44`. CPU only, no spend.
