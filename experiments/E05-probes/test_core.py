import unittest
import numpy as np
from sklearn.metrics import roc_auc_score
from metrics import auc,within_round,position_weights,threshold_at_fpr,length_match,ema_max
from splits import assign_folds,inner_split
from models import fit_logistic
from evaluate import score_bootstrap

class CoreTests(unittest.TestCase):
    def test_auc_matches_reference_with_ties_and_weights(self):
        y=np.array([0,1,1,0,1]);s=np.array([0,.5,.5,1,2]);w=np.array([2,1,3,4,1])
        self.assertAlmostEqual(auc(y,s,w),roc_auc_score(y,s,sample_weight=w))

    def test_within_round_removes_position_shortcut(self):
        y=np.array([1,1,0,0,1,0,0]);rounds=np.array([1,1,1,1,2,2,2]);s=np.array([1,2,-1,-2,-2,1,2])
        self.assertAlmostEqual(within_round(y,s,rounds)[0],2/3)
        self.assertEqual(within_round(y,-rounds,rounds)[0],.5)
        w=position_weights(y,rounds)
        for r in (1,2):self.assertAlmostEqual(w[(rounds==r)&(y==1)].sum(),w[(rounds==r)&(y==0)].sum())

    def test_scenario_strata_remove_base_rate_shortcut(self):
        y=np.array([1,1,1,0,1,0,0,0]);scenario=['high']*4+['low']*4
        scores=np.array([.75]*4+[.25]*4);rounds=np.ones(8,dtype=int)
        self.assertGreater(within_round(y,scores,rounds)[0],.5)
        value,detail=within_round(y,scores,rounds,stratum_key=scenario)
        self.assertEqual(value,.5);self.assertEqual(detail['positive_coverage'],1)
        self.assertEqual(len(detail['rounds']),2)

    def test_stratum_coverage_and_single_scenario_equivalence(self):
        y=np.array([1,1,0,1]);s=np.array([2,1,0,3]);r=np.ones(4,dtype=int)
        value,detail=within_round(y,s,r,stratum_key=['mixed']*3+['positive_only'])
        self.assertEqual(value,1);self.assertAlmostEqual(detail['positive_coverage'],2/3)
        self.assertEqual(within_round(y,s,r)[0],within_round(y,s,r,stratum_key=['one']*4)[0])
        with self.assertRaises(ValueError):within_round(y,s,r,stratum_key=['too_short'])

    def test_stratified_group_bootstrap_matches_direct_weights(self):
        y=np.array([0,1,0,1,1,0,1,0]);s=np.array([1,2,2,1,3,1,3,4]);r=np.array([1,1,1,1,2,2,2,2]);g=np.array([0,0,1,1,2,2,3,3]);scenario=['a','a','b','b','a','a','b','b']
        weights=np.array([[1,1,1,1],[0,2,1,1],[3,1,0,0]],dtype=float)
        within,pooled=score_bootstrap(y,s,r,g,weights,stratum_key=scenario)
        for k,w in enumerate(weights):
            self.assertAlmostEqual(pooled[k],auc(y,s,w[g]))
            self.assertAlmostEqual(within[k],within_round(y,s,r,w[g],stratum_key=scenario)[0])

    def test_episode_max_threshold_and_causal_ema(self):
        scores=np.arange(40);groups=np.repeat(np.arange(20),2)
        threshold,meta=threshold_at_fpr(scores,groups)
        self.assertEqual(meta['calibration_episodes'],20);self.assertEqual(meta['calibration_fpr'],.05)
        self.assertEqual(threshold,37)
        np.testing.assert_allclose(ema_max([0,2,-2,4],['a','a','a','b']),[0,1,1,4])

    def test_matching_never_crosses_rounds_and_obeys_caliper(self):
        y=np.array([1,0,1,0]);length=np.array([100,105,1000,10]);rounds=np.array([1,1,2,2])
        np.testing.assert_array_equal(length_match(y,length,rounds),[0,1])

    def test_family_groups_never_cross_folds(self):
        rows=[]
        for g in range(10):
            for c,label in [('recruiting',1),('recruiting',0),('control',0),('alone',0)]:
                rows.append(dict(episode=f'{g}-{c}-{label}',family=str(g),condition=c,label=label))
        assignment,_=assign_folds(rows,np.arange(len(rows)),42)
        for g in range(10):self.assertEqual(len({assignment[r['episode']] for r in rows if r['family']==str(g)}),1)
        train=[i for i,r in enumerate(rows) if assignment[r['episode']]!=0 and r['condition']=='recruiting']
        a,b,_=inner_split(rows,train,43)
        self.assertFalse({rows[i]['family'] for i in a}&{rows[i]['family'] for i in b})

    def test_group_bootstrap_matches_direct_weights(self):
        y=np.array([0,1,0,1,1,0,1,0]);s=np.array([1,2,2,1,3,1,3,4]);r=np.array([1,1,1,1,2,2,2,2]);g=np.array([0,0,1,1,2,2,3,3])
        weights=np.array([[1,1,1,1],[0,2,1,1],[3,1,0,0]],dtype=float)
        within,pooled=score_bootstrap(y,s,r,g,weights)
        for k,w in enumerate(weights):
            self.assertAlmostEqual(pooled[k],auc(y,s,w[g]))
            self.assertAlmostEqual(within[k],within_round(y,s,r,w[g])[0])

    def test_scaling_uses_training_only(self):
        x=np.array([[0,1],[2,3],[4,5],[6,7]],dtype=float);y=np.array([0,1,0,1])
        scaler,_=fit_logistic(x,y,None)
        np.testing.assert_allclose(scaler.mean_,[3,4])

if __name__=='__main__':unittest.main()
