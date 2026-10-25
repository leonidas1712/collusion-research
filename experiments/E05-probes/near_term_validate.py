"""Audit saved near-term predictions, split identities, labels and CSV round trip."""
import argparse
import csv
import json
import sys
import numpy as np
from data import ROOT
from near_term import VARIANTS, MODES, SEEDS, METHODS, label_rows, DATA, FIT
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run


def main(name):
    source=ROOT/'runs'/name
    run=start_run('e05-near-term-validation',experiment='E05',parents=[name,DATA,FIT],settings={'no_refits':True})
    try:
        rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
        features=np.load(ROOT/'runs'/DATA/'features.npy',mmap_mode='r')
        tables={};errors=[];fits=0
        for variant in VARIANTS:
            keep,y=label_rows(rows,variant)
            for mode in MODES:
                path=source/variant/mode
                with np.load(path/'predictions.npz') as d:table={k:d[k] for k in d.files}
                tables[(variant,mode)]=table
                assert np.array_equal(table['eligible'],np.flatnonzero(keep))
                assert np.array_equal(table['y'],y)
                with np.load(ROOT/'runs'/FIT/mode/'predictions.npz') as old:
                    for method in ('nested','fixed32'):
                        assert np.array_equal(table['eventual_'+method][:,keep],old[method][:,keep])
                    assert np.array_equal(table['folds'][:,keep],old['folds'][:,keep])
                for si,seed in enumerate(SEEDS):
                    for fold in range(5 if mode=='pooled' else 6):
                        folder=path/f's{seed}-f{fold}'
                        fit=json.loads((folder/'fit.json').read_text())
                        with np.load(folder/'scores.npz') as d:
                            train,test=d['train'],d['test']
                            assert not {rows[i]['family'] for i in train}&{rows[i]['family'] for i in test}
                            for method,layer in [('nested',fit['chosen_layer']),('fixed32',32)]:
                                with np.load(folder/f'lr-l{layer}.npz') as model:
                                    score=((np.asarray(features[test,layer],dtype=float)-model['mean'])/model['scale'])@model['coef'][0]+model['intercept'][0]
                                error=float(np.max(np.abs(score-table[method][si,test])));errors.append(error)
                                assert error<1e-9
                            for method in METHODS:
                                assert np.isfinite(table[method][si,test]).all()
                        fits+=1
        seen=set();count=0
        for r in csv.DictReader((source/'probe_scores.csv').open()):
            i=int(r['row']); row=rows[i]; variant=r['label_variant'];mode=r['analysis'];si=SEEDS.index(int(r['seed']))
            key=(r['row_id'],variant,mode,r['method'],si);assert key not in seen;seen.add(key)
            assert r['row_id']==row['episode']+'::request_idx='+str(row['request_idx'])==r['step_id']
            assert r['request_sha256']==row['request_sha256']
            d=tables[(variant,mode)]
            assert int(r['label'])==d['y'][i]
            assert int(r['fold'])==d['folds'][si,i]
            assert float(r['score'])==d[r['method']][si,i]
            count+=1
        expected=sum(len(d['eligible'])*len(SEEDS)*len(METHODS) for d in tables.values())
        assert count==expected
        result=dict(outer_fits=fits,csv_records=count,max_logistic_reconstruction_error=max(errors),
                    labels_and_folds_match=True,frozen_eventual_scores_exact=True,csv_roundtrip_exact=True)
        write_json(run.dir/'summary.json',result);run.result(**result);run.finish();print('VALIDATION',run.id,result)
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');main(p.parse_args().run)
