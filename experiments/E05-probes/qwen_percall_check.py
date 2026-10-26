"""Independent score, split, threshold and metric checks for the Qwen replication."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits
from qwen_percall import DATA, ROOT


def check(out):
    frozen=json.loads((out/'frozen_plan.json').read_text())
    for name,wanted in frozen['hashes'].items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==wanted
    committed=subprocess.check_output(['git','show',f"a4680b7cccdc5cdb4531970746789614622f9487:{out.relative_to(ROOT)}/frozen_plan.json"],cwd=ROOT)
    assert committed==(out/'frozen_plan.json').read_bytes()
    rows=json.loads((out/'rows.json').read_text());metrics=json.loads((out/'metrics.json').read_text());assert len(metrics)==4
    x=np.load(DATA/'features.npy',mmap_mode='r');fits=point_checks=0;max_error=0.;model_error=0.
    for key,m in metrics.items():
        label,mode=key.split('/');points=[];basepoints=[]
        for seed in [42,43,44]:
            ids=[];values=[];baseline=[];hits=[];bhits=[]
            for p in sorted((out/key).glob(f's{seed}-*/fit.json')):
                f=json.loads(p.read_text());z=np.load(p.parent/'scores.npz');ix=z['indices'];model=np.load(p.parent/'model.npz')
                for a,b in [('train','test'),('inner_train','inner_validation'),('calibration','test')]:
                    assert not {rows[i]['family'] for i in f['split'][a]} & {rows[i]['family'] for i in f['split'][b]}
                if label=='strict1':assert all(not rows[i]['y_immediate'] for group in f['split'].values() for i in group)
                v=((np.asarray(x[[rows[i]['index'] for i in ix],f['layer']],dtype=float)-model['mean'])/model['scale'])@model['coef'][0]+model['intercept'][0]
                err=float(np.max(abs(v-z['scores'])));assert err<1e-9;model_error=max(model_error,err)
                for field,threshold in [('calibration_scores','threshold'),('baseline_calibration_scores','baseline_threshold')]:
                    cp=z[field];t=np.sort(cp)[len(cp)-int(.05*len(cp))-1];assert t==f[threshold] and (cp>t).mean()<=.05
                ids.extend(ix.tolist());values.extend(z['scores'].tolist());baseline.extend(z['baseline_scores'].tolist());hits.extend((z['scores']>f['threshold']).tolist());bhits.extend((z['baseline_scores']>f['baseline_threshold']).tolist());fits+=1
            assert len(ids)==len(set(ids))==m['rows']
            y=np.array([rows[i]['y_'+label] for i in ids]);held=np.array([not rows[i]['label'] for i in ids]);si=[42,43,44].index(seed)
            assert np.mean(np.array(hits)[held])==m['held_step_alarms_by_seed'][si]
            assert np.mean(np.array(bhits)[held])==m['paper_A_held_step_alarms_by_seed'][si]
            assert int(y.sum())==m['positives']
            for scores,expected,target in [(values,m['within_round_by_seed'][si],points),(baseline,m['paper_A']['within_round_by_seed'][si],basepoints)]:
                groups={}
                for i,s in zip(ids,scores):groups.setdefault((rows[i]['scenario'],rows[i]['round']),[]).append((rows[i]['y_'+label],s))
                num=den=0
                for group in groups.values():
                    yy,ss=zip(*group)
                    if len(set(yy))==2:num+=roc_auc_score(yy,ss)*sum(yy);den+=sum(yy)
                value=num/den;error=abs(value-expected);assert error<1e-12;max_error=max(max_error,error);target.append(value);point_checks+=1
        assert abs(np.mean(points)-m['within_round_auc'])<1e-12
        assert abs(np.mean(basepoints)-m['paper_A']['within_round_auc'])<1e-12
    assert fits==66 and point_checks==24
    result=dict(frozen_plan_unchanged_from_commit='a4680b7cccdc5cdb4531970746789614622f9487',fits_checked=fits,independent_sklearn_checks=point_checks,max_point_error=max_error,max_model_reconstruction_error=model_error,thresholds='132 thresholds independently recomputed at strict >5% control-reply target',strict_partition_check='own-leak calls absent in all strict-next splits',source_hashes_match=True)
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with threadpool_limits(limits=2):check(a.out.resolve())
