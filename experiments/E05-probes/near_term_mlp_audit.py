"""Check near-term MLP selections, stored weights and paired OOF joins offline."""
import argparse
import csv
import json
from pathlib import Path
from near_term_mlp import inputs, reconstruct, DATA, NEAR, ROOT, CANDIDATES
import numpy as np
from metrics import within_round
from threadpoolctl import threadpool_limits


def audit(directory):
    rows,labels,cases,reference,columns=inputs()
    x=np.load(ROOT/'runs'/DATA/'features.npy',mmap_mode='r')
    expected={};errors=[];selected={};inner_count=0
    for variant,mode,seed,fold,split in cases:
        dest=directory/variant/mode/f's{seed}-f{fold}'
        fit=json.loads((dest/'fit.json').read_text());selection=json.loads((dest/'selection.json').read_text())
        assert fit['threads']==2 and fit['epochs']==80 and fit['seed']==seed+fold
        assert set(map(int,selection))==set(CANDIDATES)
        va=split['inner_validation'];y=labels[variant][1]
        for layer in CANDIDATES:
            with np.load(dest/f'inner-l{layer}.npz') as inner:
                assert np.array_equal(inner['validation'],va)
                a,_=within_round(y[va],inner['scores'],[rows[i]['round'] for i in va],
                                 stratum_key=[rows[i]['scenario'] for i in va])
                assert a==selection[str(layer)]['auc'];inner_count+=1
        layer=max(CANDIDATES,key=lambda k:(selection[str(k)]['auc'],-k))
        assert fit['layer']==layer
        selected[f'{variant}/{mode}/s{seed}-f{fold}']=layer
        with np.load(dest/'model.npz') as model:
            assert len(model['training_loss'])==80 and np.isfinite(model['training_loss']).all()
            assert model['w1'].shape==(32,5120) and model['w2'].shape==(1,32)
        with np.load(dest/'scores.npz') as data:
            for key in split:assert np.array_equal(split[key],data[key])
            assert int(data['layer'])==layer and np.array_equal(data['y_test'],y[split['test']])
            rebuilt=reconstruct(dest/'model.npz',x[split['test'],layer])
            assert np.allclose(rebuilt,data['mlp'],rtol=1e-4,atol=1e-4)
            errors.append(float(np.max(np.abs(rebuilt-data['mlp']))))
            for i,score in zip(split['test'],data['mlp']):
                expected[variant,mode,seed,int(i)]=float(score)
    seen=set()
    with (directory/'probe_scores.csv').open() as file:
        reader=csv.DictReader(file);assert reader.fieldnames==columns
        for r in reader:
            key=r['label_variant'],r['analysis'],int(r['seed']),int(r['row'])
            full_key=key+(r['method'],);assert full_key not in seen;seen.add(full_key)
            ref=reference[key]
            for field in columns:
                if field not in ('method','score'):assert r[field]==ref[field],field
            i=key[-1]
            assert r['row_id']==rows[i]['episode']+'::request_idx='+str(rows[i]['request_idx'])
            if r['method']=='nested':assert float(r['score'])==float(ref['score'])
            else:
                assert r['method']=='mlp' and float(r['score'])==expected[key]
    assert len(seen)==2*len(reference)==64440
    metrics=json.loads((directory/'metrics.json').read_text())
    baseline=json.loads((ROOT/'runs'/NEAR/'metrics.json').read_text())
    for key,result in metrics.items():
        variant,mode=key.split('/');old=baseline[variant][mode]['methods']['nested']
        current=result['methods']['nested']
        for field in ('within_round_auc','within_round_ci95','positive_coverage_by_seed'):
            assert current[field]==old[field]
        assert current['fold_sensitivity']['auc']==old['fold_sensitivity']['auc']
    result={'final_models':len(cases),'inner_candidates':inner_count,'csv_rows':len(seen),
            'exact_saved_splits_and_reference':True,'inner_selection_recomputed':True,
            'all_final_scores_reconstructed':True,'max_absolute_error':max(errors),
            'csv_schema_and_identity_match':True,'baseline_metrics_reproduced':True,
            'threads':2,'paid_cost_usd':0,'selected_layers':selected}
    (directory/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    report=directory/'report.md'
    marker='\n## Final audit\n'
    text=report.read_text().split(marker)[0]
    text+=marker+f"\nAll {len(cases)} final models and {inner_count} candidate-layer validation records passed reconstruction/selection checks. All {len(seen)} CSV rows match the saved fold assignments and baseline identities. Logistic primary estimates, confidence intervals and sensitivity point estimates reproduce the existing near-term report exactly. Maximum final-score reconstruction error: {max(errors):.3g}. See audit.json.\n"
    report.write_text(text)
    print(json.dumps({k:v for k,v in result.items() if k!='selected_layers'}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path)
    with threadpool_limits(limits=2):audit(parser.parse_args().run)
