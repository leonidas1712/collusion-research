"""Render audited all-data results and package compact reproducibility metadata."""
import argparse
import gzip
import hashlib
import json
import shutil
import sys
from pathlib import Path
from all_data_main import ROOT, LABELS, SEEDS, write_report
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run


def main(source_id, audit_id):
    source=ROOT/'runs'/source_id;audit=ROOT/'runs'/audit_id
    run=start_run('e05-all-data-main',experiment='E05',parents=[source_id,audit_id],settings={'report_only':True})
    try:
        meta=json.loads((source/'meta.json').read_text())
        assert meta['status']=='finished' and json.loads((audit/'meta.json').read_text())['status']=='finished'
        checks=json.loads((audit/'summary.json').read_text());assert checks['cases']==144 and checks['max_reconstruction_error']<1e-9
        metrics=json.loads((source/'metrics.json').read_text())
        destination=run.dir
        for name in ('metrics.json','preflight.json','source_checksums.json','probe_scores.csv'):
            shutil.copy2(source/name,destination/name)
        write_report(run,metrics,checks['csv_records'])
        with (destination/'report.md').open('a') as f:
            f.write(f"\nIntegrity audit: `runs/{audit_id}/summary.json` checks all 144 fits, family/scenario separation, unchanged development-set labels, source checksums, serialized predictions and CSV round trips. Maximum score reconstruction error: {checks['max_reconstruction_error']:.3g}. Fitted coefficients, per-fold predictions and uncompressed split indices are in `runs/{source_id}`. This report package copies the score export and deployable models without changing the fitted run.\n")
        raw=(source/'split_plan.json').read_bytes();packed=gzip.compress(raw,mtime=0)
        (destination/'split_plan.json.gz').write_bytes(packed);assert gzip.decompress(packed)==raw
        model_index=[]
        for label in LABELS:
            for seed in SEEDS:
                directory=destination/label/'deploy'/f's{seed}-f0'
                directory.parent.mkdir(parents=True,exist_ok=True)
                shutil.copytree(source/label/'deploy'/f's{seed}-f0',directory)
                fit=json.loads((directory/'fit.json').read_text())
                for method,layer in [('nested',fit['layer']),('fixed32',32)]:
                    path=directory/f'lr-l{layer}.npz'
                    model_index.append(dict(label_variant=label,seed=seed,method=method,layer=layer,
                        file=str(path.relative_to(destination)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        deploy=destination/'deployable';deploy.mkdir(exist_ok=True);write_json(deploy/'models.json',model_index)
        (deploy/'README.md').write_text(f'''# Full-data activation probes

These logistic classifiers predict whether the Qwen3-32B target violates its operator’s rule. They use residual activations at the true last prompt token, before the target’s reply. Each label has three models, using split seeds 42, 43 and 44.

- `eventual`: every eligible step of an episode that eventually violates the rule is positive.
- `A_hazard`: positive if the first forbidden action occurs this round or next; earlier steps are negative.
- `B_round_contrast`: the same positives as A, contrasted only with held episodes. Earlier steps of eventual violations are excluded using hindsight.
- `C_step_contrast`: the same clean contrast with at most three target requests until the action.

Training steps are recruiting steps strictly after the first protected-token read and before the first forbidden action. For each seed and label, a 25% family holdout selects one of 17 candidate layers. A logistic model with C=0.1 and training-only scaling is then refit on all eligible recruiting rows for that label. Positive and negative weight totals are equal within each comparable round. A fixed-layer-32 model is also saved.

## Input and scoring

Input is a NumPy array of shape `[requests, 64, 5120]` (or `[64, 5120]` for one request). Decoder blocks are zero-indexed. Use the same Qwen3-32B bf16 weights, revision, chat template and residual extraction convention as the source cache `runs/20261025-1026-e05-replay3-data-1d95`. Incompatible activations can have the correct shape while yielding invalid scores.

From the repository root:

```sh
experiments/E05-probes/.venv/bin/python experiments/E05-probes/predict_all_data.py runs/{run.id} /path/to/activations.npy --label A_hazard --seed 42
```

The command creates a tracked run containing `scores.json`. Add `--fixed32` for the secondary model. The Python function `predict_all_data.predict` also supports in-memory arrays.

`models.json` lists the selected layers, relative file paths and SHA-256 hashes. Each local NPZ file contains `mean`, `scale`, `coef` and `intercept`. The decision score is `((activation - mean) / scale) @ coef[0] + intercept[0]` at the listed layer. Higher means more positive. This is neither a calibrated probability nor a validated alarm threshold. Do not average raw scores across seeds without an explicit scale convention.

The complete model/scaler files remain in this run folder as local artifacts; they are excluded from git. Cross-validation estimates and their limitations are in `../report.md`. Full-data models have no untouched evaluation set; their training performance is not an estimate of generalization. B and C’s hindsight exclusions prevent treating them as prospective hazard monitors.
''')
        report_path=destination/'report.md'
        report_path.write_text(report_path.read_text().replace('`split_plan.json` records every split.', '`split_plan.json.gz` records every split.'))
        files=['probe_scores.csv','report.md','metrics.json','preflight.json','source_checksums.json','split_plan.json.gz','deployable/README.md','deployable/models.json']
        manifest={name:dict(bytes=(destination/name).stat().st_size,sha256=hashlib.sha256((destination/name).read_bytes()).hexdigest()) for name in files}
        assert manifest['probe_scores.csv']['sha256']==hashlib.sha256((source/'probe_scores.csv').read_bytes()).hexdigest()
        write_json(run.dir/'files.json',manifest);run.result(model_entries=len(model_index),split_plan_compressed_bytes=len(packed));run.finish();print('ALL_DATA_RELEASE',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('audit');a=p.parse_args();main(a.source,a.audit)
