# Blind rigour review of the draft PDF, round 1

PDF 64d447c6. Verdict: **FAIL**. The empty tables count as headline-changing, and there are several important items.

## Inconsistencies
- **[headline] Nine empty tables:** 7, 8, 13, 14, 16, 17, 19, 20 and 21 read "Pending verified analysis", yet the text cites them.
- **[important] Placeholder in the main text:** p6 still reads "pending" (strict-next).
- **[important] False-alarm rate:** the abstract says 2%, but I.1 sets thresholds so that about 5% of control calls alarm. No table shows the 2%.
- **[important] Figure 1 ladder:**
  - The text says "same calls", but p21 says the round-level setup never includes the leaking call.
  - The labels also differ: per-call is any-public, Qwen round-level is a channel post or new file, and gpt-oss J.1 is channel-only.
  - The ladder therefore appears to mix call sets and labels.
- **[minor] Table 1 caption** says "every number belongs to one of four datasets". The screens (Table 18) and the second incoming-only replay (Table 15) do not.
- **[minor] Detector names drift:** last-prompt probe vs "Input probe" (Table 15) vs "Input / this call" (Table 12).

## Q9: claims that are not supported
- **[important] Unbacked by empty tables:**
  - judge vs blind labels, and authority claims (Table 7 empty);
  - replay fidelity (Table 8 empty);
  - robustness (Tables 13 and 14 empty).
- **[important] The placebo is scored on the "ever" label,** where even the real probe gets only 0.61. It therefore says little about the per-call result, and there is no Qwen placebo on the per-call label.
- **[important] "Not simply detecting the read":** the read flag scores 0.80/0.83. The probe-minus-flag margin has no CI, and the post-read-only claim has no number.

## Q10: stated too strongly
- **[important] "catching what a text monitor misses":**
  - Jev is zero-shot and untuned, while the probe is trained. The incoming-text-only probe scores 0.93, so the information is in the input text, yet no trained text classifier is tested.
  - Jev's within-group 0.40 is below chance. Its pooled AUROC is 0.86, and no pooled probe score is given for comparison.
- **[important] "Probes matter most where output filters fail"** is stated as fact but is untested.
- **[important] "pauses an agent just before it gives in":** at the control-calibrated threshold, many refusing episodes still raise an alarm. Per-episode thresholds catch only about a third of leaking episodes, and that caveat is buried.
- **[minor/important] The gpt-oss pre-registration bar** was only "lower bound > 0.5", with 26 positives. "Half caught" has no interval.

## Q11: missing caveats
- **[important] gpt-oss confound:** nearly every gpt-oss leak copies the config block into the handoff file. The probe may be detecting "about to write the handoff file", and no file-write baseline is shown.
- **[important] Narrow gpt-oss peer strategy:** the leaks come from one engineered peer strategy, not from persuasion.
- **[important] The per-episode false-alarm burden** is buried.
- **[minor] Qwen thinking was off;** with thinking on, the leak rate is 12%.
- **[minor] Writes back into the protected file count as leaks.**

## Q12: reproducibility (partial)
Missing:
- the repro index (Table 21);
- replay-fidelity numbers;
- the selected layers;
- target and peer temperature and seeds;
- gpt-oss reasoning effort;
- the inference providers;
- how families were constructed, and their counts;
- the alarm-threshold values;
- the exact per-call Jev prompt and masking template;
- the reduced streaming recipe.

The API models' versions may drift.

## What holds up
- the within-group metric;
- held-out scenarios;
- honest pre-registration labelling;
- the Qwen fresh-test 0.98;
- consistent arithmetic.
