import unittest
import numpy as np
from sklearn.metrics import roc_auc_score
from all_data_main import metric_summary, labels


class MetricsTest(unittest.TestCase):
    def test_balanced_and_fold_strata(self):
        rows=[]
        for scenario in ('a','b'):
            for family in range(8):
                rows.append(dict(scenario=scenario, family=f'{scenario}{family}', round=family//4,
                                 episode=f'{scenario}{family}',label=family%2))
        y=np.array([r['label'] for r in rows]);scores=np.array([.1,.8,.3,.7,.4,.6,.9,.5]*2)
        folds=np.array([0,0,1,1,0,0,1,1]*2)
        m,boot=metric_summary(rows,np.arange(16),y,np.tile(scores,(3,1)),np.tile(folds,(3,1)),100)
        expected=np.mean([roc_auc_score(y[k:k+4],scores[k:k+4]) for k in (0,4,8,12)])
        self.assertAlmostEqual(m['within_round_auc'],expected)
        self.assertAlmostEqual(m['balanced_auc'],expected)
        self.assertAlmostEqual(m['pooled_auc'],roc_auc_score(y,scores))
        self.assertAlmostEqual(m['fold_stratified_auc'],.75)
        self.assertEqual(set(boot),{'within_round','balanced','pooled','fold_stratified'})

    def test_scenario_mean_differs_from_positive_weighting(self):
        y=np.array([0,1,1,1,0,0,0,1]);scores=np.array([0,1,1,1,1,1,1,0])
        rows=[dict(scenario='a' if i<4 else 'b',family=str(i),episode=str(i),round=1) for i in range(8)]
        m,_=metric_summary(rows,np.arange(8),y,scores[None,:],np.zeros((1,8),dtype=int),100)
        self.assertAlmostEqual(m['within_round_auc'],.75)
        self.assertAlmostEqual(m['balanced_auc'],.5)

    def test_horizon_boundaries(self):
        rows=[dict(eligible=True,condition='recruiting',ordinal=i,first_read=0,label=1,
                   first_action=6,steps_until_action=6-i,action_round=4,round=r)
              for i,r in [(1,1),(2,2),(3,3),(4,3),(5,4)]]
        a,ya=labels(rows,'A_hazard');b,yb=labels(rows,'B_round_contrast');c,yc=labels(rows,'C_step_contrast')
        np.testing.assert_array_equal(a,[1,1,1,1,1]);np.testing.assert_array_equal(ya,[0,0,1,1,1])
        np.testing.assert_array_equal(b,[0,0,1,1,1]);np.testing.assert_array_equal(c,[0,0,1,1,1])


class DeploymentTest(unittest.TestCase):
    def test_saved_affine_model_and_shape_guard(self):
        import json
        import tempfile
        from pathlib import Path
        from predict_all_data import predict
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'A_hazard/deploy/s42-f0';path.mkdir(parents=True)
            (path/'fit.json').write_text(json.dumps({'layer':4}))
            coef=np.zeros((1,5120));coef[0,0]=2
            np.savez(path/'lr-l4.npz',mean=np.ones(5120),scale=np.full(5120,2.),coef=coef,intercept=np.array([3.]))
            x=np.zeros((2,64,5120));x[:,4,0]=[1.,5.]
            self.assertEqual(predict(temp,x,'A_hazard',42)['scores'],[3.,7.])
            with self.assertRaises(ValueError):predict(temp,x[:,0],'A_hazard',42)


if __name__=='__main__':unittest.main()
