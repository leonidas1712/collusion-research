"""Reconstruct frozen TF-IDF predictions from saved vocabularies and coefficients."""
import json
import sys
import numpy as np
from threadpoolctl import threadpool_limits
from text_baseline import ROOT,FIT,TEXTS,load_text,vectorizer,start_run
from metrics import position_weights,within_round,threshold_at_fpr
from report import write_json

SOURCE='20261024-2011-e05-text-baselines'

def main():
    source=ROOT/'runs'/SOURCE;fit=ROOT/'runs'/FIT
    run=start_run('e05-text-validation',experiment='E05',parents=[SOURCE,FIT],settings={'purpose':'reconstruct every held-out prediction and calibration cutoff from saved artifacts'})
    try:
        rows=[json.loads(s) for s in (fit/'rows.jsonl').read_text().splitlines()];texts=load_text(rows,run.dir)
        pred=np.load(source/'predictions.npz');eligible=pred['eligible'];ep=np.array([r['episode'] for r in rows]);rounds=np.array([r['round'] for r in rows]);y=pred['y'];seeds=list(pred['seeds']);audit=[]
        source_notes=json.loads((fit/'main'/'folds.json').read_text());notes={(r['method'],r['seed'],r['fold']):r for r in json.loads((source/'fits.json').read_text())}
        with threadpool_limits(limits=4):
            for note in source_notes:
                select=lambda key:eligible[np.isin(ep[eligible],note[key])]
                train=select('train_episodes');test=select('test_episodes');cal=select('calibration_episodes');si=seeds.index(note['seed'])
                w=position_weights(y[train],rounds[train]);train=train[w>0]
                assert not {rows[i]['family'] for i in train}&{rows[i]['family'] for i in test}
                for method in TEXTS:
                    prefix=f'{method}-s{note["seed"]}-f{note["fold"]}';model=np.load(source/(prefix+'.npz'))
                    vocab=json.loads((source/(prefix+'-vocabulary.json')).read_text());vec=vectorizer();vec.set_params(vocabulary=vocab);vec.idf_=model['idf']
                    x=vec.transform([texts[method][i] for i in test]);values=np.asarray(x@model['coef'][0])+model['intercept'][0]
                    err=float(np.max(np.abs(values-pred[method][si,test])));assert err<1e-10
                    cx=vec.transform([texts[method][i] for i in cal]);cv=np.asarray(cx@model['coef'][0])+model['intercept'][0]
                    cutoff,_=threshold_at_fpr(cv,ep[cal]);assert np.allclose(pred['threshold_'+method][si,test],cutoff,atol=1e-12,rtol=0)
                    tx=vec.transform([texts[method][i] for i in train]);tv=np.asarray(tx@model['coef'][0])+model['intercept'][0]
                    # Re-fit only the feature extractor to verify the saved vocabulary and IDF came from these training texts.
                    check=vectorizer();check.fit([texts[method][i] for i in train]);assert check.vocabulary_==vocab
                    np.testing.assert_array_equal(check.idf_,model['idf'])
                    audit.append(dict(method=method,seed=note['seed'],fold=note['fold'],max_score_error=err,train_within_round_auc=within_round(y[train],tv,rounds[train])[0],
                        test_zero_feature_rows=int(np.sum(np.diff(x.indptr)==0)),test_rows=len(test),vocabulary_idf_train_only_verified=True,cutoff_verified=True))
        write_json(run.dir/'validation.json',audit)
        summary={m:dict(max_score_error=max(r['max_score_error'] for r in audit if r['method']==m),mean_train_within_round_auc=float(np.mean([r['train_within_round_auc'] for r in audit if r['method']==m]))) for m in TEXTS}
        write_json(run.dir/'summary.json',summary);run.result(all_45_models_verified=True);run.finish();print(json.dumps(summary,indent=2));print('VALIDATION_RUN',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':main()
