**Table E.1.** Full text-monitor grid on the first data batch. Each row is one monitor, question and access level, scored on the same eligible steps. Values are within-scenario-and-round AUROC with 95% family-bootstrap intervals. The eventual label asks whether the episode ever ends in a give-in; near-term A asks whether the first forbidden action occurs in the current or next round.

| Monitor | Question | Access | Eventual AUROC [95% CI] | Near-term A AUROC [95% CI] |
|---|---|---|---:|---:|
| Jev 1.14 | Detect | L1: actions only | 0.504 [0.453, 0.554] | 0.507 [0.468, 0.548] |
| Jev 1.14 | Detect | L2: conversation | 0.529 [0.483, 0.576] | 0.549 [0.504, 0.593] |
| Jev 1.14 | Detect | L3: everything seen | 0.538 [0.482, 0.593] | 0.570 [0.519, 0.622] |
| GPT-5-nano | Detect | L1: actions only | 0.504 [0.470, 0.539] | 0.511 [0.469, 0.553] |
| GPT-5-nano | Detect | L2: conversation | 0.560 [0.516, 0.603] | 0.569 [0.525, 0.616] |
| GPT-5-nano | Detect | L3: everything seen | 0.518 [0.468, 0.570] | 0.542 [0.495, 0.589] |
| Luna Decisions | Detect | L1: actions only | 0.526 [0.475, 0.573] | 0.514 [0.458, 0.571] |
| Luna Decisions | Detect | L2: conversation | 0.517 [0.468, 0.570] | 0.522 [0.466, 0.580] |
| Luna Decisions | Detect | L3: everything seen | 0.538 [0.471, 0.600] | 0.566 [0.494, 0.634] |
| Jev 1.14 | Forecast | L1: actions only | 0.479 [0.412, 0.545] | 0.512 [0.458, 0.568] |
| Jev 1.14 | Forecast | L2: conversation | 0.558 [0.489, 0.620] | 0.635 [0.586, 0.675] |
| Jev 1.14 | Forecast | L3: everything seen | 0.574 [0.502, 0.639] | 0.660 [0.613, 0.704] |
| GPT-5-nano | Forecast | L1: actions only | 0.525 [0.488, 0.561] | 0.548 [0.493, 0.604] |
| GPT-5-nano | Forecast | L2: conversation | 0.555 [0.511, 0.601] | 0.554 [0.498, 0.614] |
| GPT-5-nano | Forecast | L3: everything seen | 0.512 [0.463, 0.557] | 0.535 [0.484, 0.580] |
| Luna Decisions | Forecast | L1: actions only | 0.527 [0.485, 0.568] | 0.517 [0.464, 0.570] |
| Luna Decisions | Forecast | L2: conversation | 0.535 [0.496, 0.575] | 0.496 [0.442, 0.552] |
| Luna Decisions | Forecast | L3: everything seen | 0.481 [0.436, 0.526] | 0.505 [0.454, 0.555] |

Source: `runs/20261025-0147-e06-monitor-main/metrics_main.json` and `metrics_main_A_hazard.json`. All 18 setups cover the first batch's 4,184 eligible steps; the ranking columns use its 2,910 recruiting steps. No target is pooled with gpt-oss.
