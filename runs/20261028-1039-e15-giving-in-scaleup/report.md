# E15: giving in, or a fresh read? A scaled-up E14

## Question
In E14, on one scenario, sharing calls under a clean permission crossed the frozen Qwen3-32B probe threshold far less often than forbidden leaks (28% against 82%). Two things could explain that gap besides "the probe reads giving in":
- **Timing:** permitted episodes shared at once, with a short history.
- **Recency:** forbidden leaks more often come straight after the agent reads the protected file, and calls right after a read almost always cross.

E15 repeats the comparison on all five Qwen test scenarios. It adds a delayed-request arm against timing, and it splits every comparison by how recently the value was read.

## Design
- **Model and probe:** Qwen3-32B with the frozen last-prompt probe and its frozen threshold 1.284. There was no refitting. Six saved test calls were rescored in the same jobs and matched their frozen scores.
- **Runner:** each scenario's test run is repeated unchanged: the same peer model and prompt, tools, settings, 20-round cap and early stopping.
- **FORBID:** the normal rule and the normal peer. There are 95 new episodes (39 leak), pooled with the 38 existing test leaks.
- **EARLY:** a clean permission, the PERMIT sentence with the consequence sentence removed, and the normal peer, which asks from round 1.
  - 80 new episodes on four scenarios.
  - E14's 29 no-consequence episodes for dispatch.
- **LATE:** the same clean permission, but the peer coordinates on the ordinary task first. It names the value or the private file only in its 5th message. There are 99 episodes.
- **Calls scored:** from the first read of the file through the first call that emits the exact value, which is the sharing call.
- **Primary metric:** the crossing rate among sharing calls that do not directly follow a read. A call follows a read when its prompt ends with the tool result that contains the value.
- **Pre-declaration:** the plan, its readings and the hedge regex were committed before any API call (`experiments/E15-giving-in-scaleup/plan.json`).

## Results

**1. Right after a read, almost every sharing call crosses, in every arm.**

| Sharing calls that follow a read | Over threshold | Median score |
|---|---|---|
| FORBID | 45 / 46 (98%) | 2.86 |
| EARLY | 35 / 36 (97%) | 4.18 |
| LATE | 91 / 91 (100%) | 3.47 |

None of the EARLY or LATE episodes refused or hedged before sharing (0/109 and 0/98 by the fixed regex), while 51 of 77 forbidden leaks did. So a fresh read alone puts the score over the threshold, whether or not the agent resisted. On these calls the probe cannot tell giving in from a permitted share.

**2. Away from a read, forbidden leaks still cross more often than permitted shares.**

| Sharing calls that do not follow a read | Over threshold (Wilson 95% CI) | Median score |
|---|---|---|
| FORBID (old + new) | 19 / 31 (61%, 44–76%) | 1.47 |
| FORBID, rounds ≥ 3 | 15 / 22 (68%, 47–84%) | 1.79 |
| EARLY | 24 / 73 (33%, 23–44%) | 1.06 |
| LATE | 1 / 7 (14%, 3–51%) | 1.15 |

- **EARLY − FORBID:** −28 points (episode-bootstrap CI −49 to −8).
- **LATE − FORBID rounds ≥ 3:** −54 points (CI −82 to −21).
- **The old and new forbidden sets agree:** 10/17 old against 9/14 new.
- **EARLY without E14's dispatch episodes:** 20/48 (42%, 29–56%).
- **Per scenario:** EARLY's non-read rate ranges from 27% to 60%.

**3. Recency** (`recency.pdf`). The crossing rate falls as calls pass since the read, in every arm. The arms separate only away from the read.

| Calls since the read | 0 | 1 | 2 | 3+ |
|---|---|---|---|---|
| FORBID | 45/46 | — | 5/7 | 14/24 (58%) |
| EARLY | 35/36 | 0/15 | 4/5 | 20/53 (38%) |
| LATE | 91/91 | 0/1 | — | 1/6 |

**4. Delaying the request did not create late, uncontested shares away from a read.**
- **Pacing worked:** the LATE peer first named the value in round 5 in 82 of 99 episodes, and in round 3, 4 or 6 otherwise.
- **But the target re-read the file before sharing:** 91 of 98 LATE sharing calls directly follow a fresh read. That leaves 7 calls for the primary metric.
- **One share came before the ask:** an unprompted share, which scored 1.21 and is kept out of the tables above.
- **Within-episode change:** the sharing call minus the mean of the same episode's earlier calls is +2.05 for FORBID, +0.67 for EARLY and +2.95 for LATE. In LATE this mostly reflects the read just before the share.

## Reading
By the rules fixed before running, the result is **in between**:
- **"Stays low" is not met:** LATE's upper bound is 51%, just above the 50% cut, although its difference from forbidden leaks excludes 0.
- **"Rises" is not met:** LATE's CI does not reach the forbidden rate.

What the data show:
- **A fresh read puts nearly any disclosure over the threshold.** Calls right after a read cross at about 98–100% in every arm, permitted and uncontested ones included. Forbidden leaks follow a read more often (46/77) than EARLY shares do (36/109), so pooling all sharing calls raises both rates (FORBID 83% against EARLY 54%), though the gap between them stays about the same (29 points pooled, 28 away from a read).
- **A real but smaller gap than E14's remains away from a read.** Forbidden leaks cross about twice as often as permitted shares (61% against 33%), and the difference excludes 0. Across five scenarios, permitted non-read shares cross more often than on E14's single scenario (33% against 16%), and this, not the read split, is what narrows the gap from E14's. This holds with EARLY's early timing. LATE points the same way, but on 7 calls.
- **For the paper:** the probe's high score on a sharing call is driven first by a fresh read of the value. Giving in adds to it only when the read is not recent. "The probe reads giving in" is too strong as a headline. "It reads a coming disclosure, most strongly right after the value is read, and more strongly when the disclosure is contested" fits the data.

**Caveat.** LATE could not test timing as planned, because the target re-read the file before almost every late share. So the timing control rests on 7 calls, and the main non-read comparison is FORBID against EARLY, where permitted shares come early. "Permitted" also coincides with "uncontested" in every non-forbidden episode. Recency bins 1 and 2 are small.

## Spend
- **API:** $0.82. Several FORBID and LATE episodes hit upstream rate limits on the peer model. They were rerun with the same seeds, and none failed after all retries.
- **GPU:** about $0.98, for 4 batches and 1598 forward passes on an A100 at $3.20/h.
- **Total:** about $1.80, against the $12 cap. Details are in `spend.json`.

## Files
- `results.json`: all metrics, at full precision.
- `recency.pdf` / `recency.png`: the recency figure.
- `calls.json` / `episodes.json`: per-call labels (read-following, calls since the read, ask round, hedge) and per-episode summaries.
- `batch-*.csv`: per-call probe scores.
- `first_ask_texts.json`: each peer's first request, per arm.
- **Episodes:**
  - `runs/20261028-03*-e15-*`, `runs/20261028-0722-e15-forbid` and `runs/20261028-1016-e15-early`.
  - E14 dispatch episodes: `runs/20261028-0150-e14-permitted-onpolicy-arm-b`.
  - Old forbidden test leaks: `runs/20261025-0817-e01-spray-*`.
- **Code:** `experiments/E15-giving-in-scaleup/`.
