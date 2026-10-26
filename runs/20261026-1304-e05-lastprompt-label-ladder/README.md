# Matched last-prompt label ladder

Post-hoc CPU refits on the same 1,995 calls as the matched immediate-label experiment. Full estimates, intervals and caveats are in report.md and metrics.json. verification.json records independent model, threshold, cohort and AUROC checks.

Run from the repository root in the E05 Python environment:

```sh
PYTHONPATH=src python experiments/E05-probes/lastprompt_label_ladder.py
PYTHONPATH=src python experiments/E05-probes/lastprompt_ladder_check.py --out runs/20261026-1304-e05-lastprompt-label-ladder
```

The first command creates a new run; substitute its path in the check. To resume this run, pass --out runs/20261026-1304-e05-lastprompt-label-ladder to the first command. Source activation caches are required; exact paths are in analysis_plan.json and the fitting script. Fitted model caches are local. probe_scores.csv.gz is the lossless OOF export. The recipe has two CPU threads, 17 candidate layers, three seeds and 66 outer fits; no GPU or paid API calls.

The threshold helper calibration_episodes field counts control-call indices in this use. Calibration is per control call, not per episode. Family-bootstrap uncertainty is conditional on saved fits and selection choices.
