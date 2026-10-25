"""Audit all-data folds, labels, serialized probes, and the E06 score export."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from all_data_main import ROOT, DATA, LABELS, MODES, SEEDS, read_rows, labels, row_id
from report import write_json
from predict_all_data import predict
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run


def main(source_id):
    source=ROOT/'runs'/source_id
    run=start_run('e05-all-data-audit',experiment='E05',parents=[source_id,DATA],settings={'no_refits':True})
    try:
        assert json.loads((source/'meta.json').read_text())['status']=='finished'
        for name,digest in json.loads((source/'source_checksums.json').read_text()).items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
        rows=read_rows();x=np.load(ROOT/'runs'/DATA/'features.npy',mmap_mode='r')
        plans=json.loads((source/'split_plan.json').read_text());maxerror=0.;models=0
        old=[json.loads(s) for s in (ROOT/'runs/20261025-0337-e05-replay2-data/rows.jsonl').read_text().splitlines()]
        for variant in LABELS:
            old_keep,old_y=labels(old,variant);keep,y=labels(rows,variant)
            assert np.array_equal(old_keep,keep[:len(old)]) and np.array_equal(old_y,y[:len(old)])
        with threadpool_limits(limits=2):
            for p in plans:
                directory=source/p['variant']/p['mode']/f"s{p['seed']}-f{p['fold']}"
                fit=json.loads((directory/'fit.json').read_text());_,y=labels(rows,p['variant'])
                with np.load(directory/'scores.npz') as d:
                    for k,v in p['split'].items():assert np.array_equal(d[k],v)
                    tr=d['train'];ev=d['test'] if p['mode']!='deploy' else tr
                    assert not {rows[i]['family'] for i in d['inner_train']} & {rows[i]['family'] for i in d['inner_validation']}
                    if p['mode']!='deploy':
                        assert not {rows[i]['family'] for i in tr} & {rows[i]['family'] for i in ev}
                    if p['mode']=='loso':
                        assert not {rows[i]['scenario'] for i in tr} & {rows[i]['scenario'] for i in ev}
                    assert np.array_equal(d['y'],y[ev])
                    for method,layer in [('nested',fit['layer']),('fixed32',32)]:
                        with np.load(directory/f'lr-l{layer}.npz') as model:
                            pred=((np.asarray(x[ev,layer],dtype=float)-model['mean'])/model['scale'])@model['coef'][0]+model['intercept'][0]
                        error=float(np.max(np.abs(pred-d[method])));assert error<1e-9
                        maxerror=max(maxerror,error);models+=1
                        if p['mode']=='deploy':
                            subset=np.array([0,len(ev)-1])
                            deployed=predict(source,x[ev[subset]],p['variant'],p['seed'],method=='fixed32')
                            assert np.allclose(deployed['scores'],d[method][subset],rtol=0,atol=1e-9)
        arrays={};expected=0
        for variant in LABELS:
            keep,y=labels(rows,variant);ids=np.flatnonzero(keep)
            for mode in MODES:
                with np.load(source/variant/mode/'predictions.npz') as d:
                    assert np.array_equal(d['eligible'],ids) and np.array_equal(d['y'],y[ids])
                    assert np.isfinite(d['nested']).all() and np.isfinite(d['fixed32']).all()
                    arrays[(variant,mode)]={k:d[k].copy() for k in ('nested','fixed32','folds','eligible','y')}
                expected+=len(ids)*3*2
        locations={key:{int(i):j for j,i in enumerate(d['eligible'])} for key,d in arrays.items()}
        seen=set();count=0
        with (source/'probe_scores.csv').open() as f:
            for r in csv.DictReader(f):
                key=(r['label_variant'],r['analysis']);d=arrays[key];i=int(r['row']);j=locations[key][i];si=SEEDS.index(int(r['seed']))
                unique=(r['row_id'],*key,r['method'],r['seed']);assert unique not in seen;seen.add(unique)
                assert r['row_id']==r['step_id']==row_id(rows[i])
                assert r['request_sha256']==rows[i]['request_sha256']
                assert float(r['score'])==d[r['method']][si,j]
                assert int(r['fold'])==d['folds'][si,j]
                assert int(r['label'])==d['y'][j]
                count+=1
        assert count==expected
        result=dict(cases=len(plans),serialized_score_checks=models,max_reconstruction_error=maxerror,
                    csv_records=count,csv_roundtrip_exact=True,deployment_inference_checked=True,no_outer_or_inner_family_overlap=True,
                    loso_scenario_disjoint=True,original_prefix_labels_unchanged=True)
        write_json(run.dir/'summary.json',result);run.result(**result);run.finish();print('ALL_DATA_AUDIT',run.id,result)
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');main(p.parse_args().source)
