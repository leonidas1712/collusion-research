"""Independent row-pair bootstrap check of the per-call input monitor exports."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
import percall_input_monitor as m
from audit_stream_confirmation import within,pair_auc


def main(directory):
    meta=json.loads((directory/'meta.json').read_text());target=meta['settings'].get('target','gpt-oss')
    rows,_,_,_=m.inputs(target);lookup={r['row_id']:r for r in rows};data=list(csv.DictReader((directory/'probe_scores.csv').open()));metrics=json.loads((directory/'metrics.json').read_text());checked={}
    with threadpool_limits(limits=2):
        for mode in ['pooled','loso']:
            selected=[r for r in data if r['analysis']==mode and r['seed']=='42'];y=np.array([int(r['label']) for r in selected]);scores=np.array([float(r['score']) for r in selected]);fam,codes=np.unique([lookup[r['row_id']]['family'] for r in selected],return_inverse=True)
            weights=np.vstack([np.ones(len(selected)),np.random.default_rng(20261025).multinomial(len(fam),np.ones(len(fam))/len(fam),size=1000)[:,codes]])
            strata=[(lookup[r['row_id']]['scenario'],lookup[r['row_id']]['round']) for r in selected]
            for key,values in [('within_round',within(y,scores,weights,strata)),('pooled',pair_auc(y,scores,weights)[0])]:
                assert abs(values[0]-metrics[mode][key+'_auc'])<1e-10
                np.testing.assert_allclose(np.nanquantile(values[1:],[.025,.975]),metrics[mode][key+'_ci95'],rtol=0,atol=1e-10)
            reference={r['row_id']:r['score'] for r in selected}
            assert all(r['score']==reference[r['row_id']] for r in data if r['analysis']==mode)
            checked[mode]={'rows':len(selected),'auc_and_ci_parity':True,'seed_invariant_monitor_scores':True}
    result={'direct_row_pair_audit':checked,'bootstrap_draws':1000,'seed':20261025}
    (directory/'independent_audit.json').write_text(json.dumps(result,indent=2)+'\n');print('INDEPENDENT_INPUT_MONITOR_AUDIT_PASS',directory)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);main(p.parse_args().run)
