import unittest
import numpy as np
from replay2_data import eligible_step
from replay2_models import fit_mlp,score_mlp,scenario_rates
from replay2_core import outer_cases,split_inner
from replay2_evaluate import alarm_results

class Replay2Tests(unittest.TestCase):
    def test_alarms_count_episodes_and_use_separate_ema_cutoff(self):
        rows=[]
        for ep,label,condition in [('p',1,'recruiting'),('h',0,'recruiting'),('c',0,'control')]:
            for step in (1,2):rows.append(dict(episode=ep,family=ep,label=label,condition=condition,round=step,steps_until_action=3-step,action_round=3))
        scores=np.array([[0,2,0,0,0,2.]])
        raw=np.ones((1,6,1));smooth=np.full((1,6,1),1.5)
        result,records=alarm_results(rows,np.arange(6),scores,raw,smooth,[.1],reps=20)
        self.assertEqual(result['raw_0.1']['recall']['mean'],1)
        self.assertEqual(result['raw_0.1']['control_fpr']['counts_by_seed'][0],dict(alarms=1,episodes=1))
        self.assertEqual(result['raw_0.1']['lead_steps_conditional_on_detection']['median'],1)
        self.assertEqual(result['ema_0.1']['recall']['mean'],0)

    def test_strict_completed_request_window(self):
        row=dict(shared_branch_history=False,valid_for_comparison=True,first_token_read_request=2,first_action_target_request=5)
        self.assertFalse(eligible_step(dict(row,target_completed_ordinal=2)))
        self.assertTrue(eligible_step(dict(row,target_completed_ordinal=3)))
        self.assertFalse(eligible_step(dict(row,target_completed_ordinal=5)))
        self.assertFalse(eligible_step(dict(row,target_completed_ordinal=None)))
        self.assertFalse(eligible_step(dict(row,target_completed_ordinal=3,shared_branch_history=True)))
        self.assertTrue(eligible_step(dict(row,target_completed_ordinal=8,first_action_target_request=None)))

    def test_scenario_rate_uses_episodes_and_training_only_fallback(self):
        rows=[dict(episode='a',scenario='seen'),dict(episode='a',scenario='seen'),dict(episode='b',scenario='seen'),dict(episode='c',scenario='unknown')]
        values,note=scenario_rates(rows,[0,1,2],[2,3],[1,1,0])
        np.testing.assert_array_equal(values,[.5,.5]);self.assertEqual(note['unseen_scenario_fallback'],.5)

    def test_loso_purges_shared_families_and_inner_holds_scenario(self):
        rows=[]
        for scenario in range(6):
            for family in range(4):
                for label in [0,1]:
                    rows.append(dict(scenario=str(scenario),family=f'{scenario}-{family}',episode=f'{scenario}-{family}-{label}',label=label,condition='recruiting'))
        rows[8]['family']=rows[0]['family']
        for _,train,test,note in outer_cases(rows,np.arange(len(rows)),42,True):
            self.assertFalse({rows[i]['family'] for i in train}&{rows[i]['family'] for i in test})
            self.assertFalse({rows[i]['scenario'] for i in train}&{rows[i]['scenario'] for i in test})
            fit,val,_=split_inner(rows,train,42,True)
            self.assertFalse({rows[i]['family'] for i in fit}&{rows[i]['family'] for i in val})
            self.assertFalse({rows[i]['scenario'] for i in fit}&{rows[i]['scenario'] for i in val})

    def test_small_mlp_trains_on_cpu_with_finite_scores(self):
        x=np.random.default_rng(42).normal(size=(64,8)).astype('float32');y=(x[:,0]*x[:,1]>0).astype(int)
        model=fit_mlp(x,y,np.ones(64,dtype=int),42)
        self.assertEqual(next(model[1].parameters()).device.type,'cpu')
        self.assertLess(model[2][-1],model[2][0])
        self.assertTrue(np.isfinite(score_mlp(model,x)).all())

if __name__=='__main__':unittest.main()
