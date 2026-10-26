"""Independent saved-score parity and split checks for the reduced LOSO run."""
import argparse,json
from pathlib import Path
import numpy as np
from stream_loss import inference_scores
from threadpoolctl import threadpool_limits

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--data',type=Path,required=True);a=p.parse_args()
 rows=json.loads((a.data/'replies.json').read_text());x=np.load(a.data/'full.npy',mmap_mode='r')[:,2,:];positions=np.load(a.data/'positions.npz');checks=[]
 for path in sorted(a.out.glob('*/layer18/immediate/both/loso/s42-f*/fit.json')):
  fit=json.loads(path.read_text());model=np.load(path.parent/'model.npz');z=np.load(path.parent/'scores.npz');train=fit['split']['train'];test=z['indices'].tolist();cal=fit['split']['calibration']
  assert not {rows[i]['family'] for i in train}&{rows[i]['family'] for i in test}
  assert not {rows[i]['scenario'] for i in train}&{rows[i]['scenario'] for i in test}
  assert all(rows[i]['condition']=='control' for i in cal)
  assert fit['max_train_tokens']==64 and fit['view']=='layer18' and fit['variant']=='immediate'
  assert fit['diagnostics']['tokens']<=64*fit['diagnostics']['replies']
  direction=model['coef']/model['scale'];bias=float(model['intercept'])-model['mean']@direction
  maximum=0.
  for j in sorted(set([0,len(test)//2,len(test)-1])):
   r=rows[test[j]];ix=np.arange(r['capture_start'],r['capture_stop'])
   if fit['stream']=='incoming':ix=ix[positions['roles'][ix]==0]
   with threadpool_limits(limits=1):pred=np.asarray(x[ix],dtype=float)@direction+bias
   saved=z['token_logits'][z['offsets'][j]:z['offsets'][j+1]];assert len(saved)==len(ix)
   np.testing.assert_allclose(pred,saved,rtol=1e-9,atol=1e-8);maximum=max(maximum,float(np.max(np.abs(pred-saved))))
   for method in ['raw','ema','rolling10']:
    score=inference_scores(pred)[method];np.testing.assert_allclose(score.max(),z[method+'_max'][j],atol=1e-8)
    hits=np.flatnonzero(score>fit['thresholds'][method]);assert z[method+'_first_alarm'][j]==(hits[0] if len(hits) else -1)
  checks.append({'fit':str(path),'max_abs_score_error':maximum,'test_replies':len(test),'train_replies':len(train),'train_tokens':fit['diagnostics']['tokens'],'family_scenario_disjoint':True,'calibration_controls_only':True})
 assert len(checks)==12, len(checks)
 (a.out/'independent_checks.json').write_text(json.dumps({'fits':checks,'score_parity_samples':36,'all_pass':True},indent=2)+'\n');print('PASS12fits/36scoreparitysamples')
