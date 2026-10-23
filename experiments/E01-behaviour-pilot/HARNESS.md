# Running the episode harness

`harness.py` alternates recruiter and target turns. Each turn can call tools repeatedly. Explicit `send_message` posts are delivered to the team channel; final text is posted only if the agent has not already posted during that turn. Final text remains in the originating agent's history in either case. Peer messages enter the other agent's history as attributed user messages. System prompts, tool results and reasoning stay in the originating agent's history unless that agent publishes their content.

All built-in tools operate on an in-memory workspace. `run_tests` returns the scenario's configured mock result; it does not execute code. `send_message` publishes to the simulated channel, with no external recipient. Scenario-specific tools are Python callbacks and must preserve this boundary.

## Offline wiring check

From the repo root, after `uv sync`:

```sh
uv run python experiments/E01-behaviour-pilot/harness.py --fake --output /tmp/e01-wiring --episodes 2 --parallelism 2
uv run python -m unittest discover -s experiments/E01-behaviour-pilot -p 'test_harness.py'
```

The fake client supplies deterministic tool calls. These outputs test the wiring and are not research observations. Every CLI invocation creates run metadata; omit `--output` to place episodes inside that new run. Repeating a command with the same explicit output directory skips completed episodes. Use a new output directory when changing settings or scenario content. An interrupted episode restarts from its initial state; its prior partial trace is retained as an attempt file. Do not run two processes against the same episode directory at once.

## Inspecting an episode

Each episode saves the scenario, settings, both agents' histories, the shared channel, tool log and resulting mock files. The `requests` list records each API attempt, its input and returned response, including provider usage and cost when supplied. API credentials are not part of those records. A request snapshot is saved before the network call, so a crash can leave a request with no response.

Transient API failures get up to six attempts. Backoff is 2, 4, 8, 16 and 30 seconds plus 0–1 second of jitter. A valid `Retry-After` value (seconds or HTTP date) sets a minimum wait, even above 30 seconds. Each retry records its delay and header value in the request trace; permanent API errors stop immediately.

Only complete episodes receive the scenario's label. API failures, truncated responses and exhausted tool-call limits produce an incomplete record with a stop reason and no label. Inspect the tool log separately if an action occurred before a later failure. Missing provider cost is unknown, not free; retries whose responses were lost may still have incurred charges.

The client sends native tool schemas on every call. It saves and reuses returned reasoning details within the requesting agent's history. The application records what it sends to OpenRouter; provider-side chat templates and internal prompts are outside that visibility.

## Scenario interface

Scenarios supply prompts, initial mock files, optional tools and a label function. Labels should inspect successful target actions in the tool log, rather than infer behavior from prose. Failed tool calls and actions by the other agent must not accidentally satisfy a target-action label.

`Scenario.tool_access` optionally maps both actor names to allowed tool names. The harness filters advertised schemas and rejects disallowed calls in the dispatcher. Use a recruiter allowlist of `["send_message"]` for scenarios that require target-private files. An empty list allows only ordinary text replies. Omitting this setting retains shared access for the original benign example.

`Scenario.channel_format` and `actor_names` control attribution. `Settings.target_request_options` and `recruiter_request_options` accept SDK options, including OpenRouter options in `extra_body`. Reasoning is disabled by default; the CLI has `--target-reasoning` and `--recruiter-reasoning` for models that require it.

The target defaults to DeepInfra with fallbacks disabled. `--target-provider` and `--recruiter-provider` pin either actor; the recruiter otherwise uses OpenRouter's default routing. `--target-quantization bf16` (or `--recruiter-quantization`) adds a quantization filter. These controls follow [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection). Each request records `requested_routing`, `served_provider`, `served_quantization` and their source. Served values come from the response; absent values remain null, not inferred from the requested provider or filter. Settings participate in resume checks, so changed routing needs a new output directory.

The CLI loads `scenarios.get_scenario(name)` or `scenarios.SCENARIOS[name]` for custom scenarios. Increase `scenario_version` whenever a tool handler or label function changes: callable behavior cannot be compared by the resume check. Live use requires the scenario's `recruiter_approved` flag; only the benign built-in dummy has that flag set here. The CLI reads `OPENROUTER_API_KEY` from the environment or the root `.env`.

Research scenario content is pending team review. The built-in example is only a benign workspace check. No recruitment behavior or acceptance rate has been established by these wiring checks.

Protocol references: [OpenRouter tool calling](https://openrouter.ai/docs/guides/features/tool-calling), [reasoning details](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens), [usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting).
