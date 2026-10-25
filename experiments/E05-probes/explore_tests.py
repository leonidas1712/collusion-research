"""Offline tests for causal trajectory construction and supplied-fold alignment."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[k]='2'
import tempfile
import unittest
from pathlib import Path
import numpy as np
from explore_features import trajectory_links, feature_values
from explore_trajectories import load_inputs, cases, fit_one
from threadpoolctl import threadpool_limits


class ExploreTests(unittest.TestCase):
    def test_predecessor_does_not_cross_episodes_or_use_future_anchor(self):
        rows=[{'episode':'a','request_idx':i,'ordinal':i+1,'first_read':1,'token_in_context':i>0} for i in range(3)]
        rows += [{'episode':'b','request_idx':0,'ordinal':1,'first_read':1,'token_in_context':False}]
        previous,anchor=trajectory_links(rows)
        np.testing.assert_array_equal(previous,[-1,0,1,-1])
        np.testing.assert_array_equal(anchor,[-1,1,1,-1])
        prefix_prev,prefix_anchor=trajectory_links(rows[:2])
        np.testing.assert_array_equal(prefix_prev,previous[:2]);np.testing.assert_array_equal(prefix_anchor,anchor[:2])

    def test_delta_and_scalar_geometry(self):
        d,s=feature_values(np.array([0.,2.]),np.array([2.,0.]),np.array([0.,2.]))
        np.testing.assert_allclose(d,[-2,2]);np.testing.assert_allclose(s,[np.sqrt(8),0,1])

    def test_shared_state_without_read_ordinal_has_no_anchor(self):
        rows=[{'episode':'shared','request_idx':0,'ordinal':None,'first_read':None,'token_in_context':True}]
        previous,anchor=trajectory_links(rows)
        self.assertEqual(previous.tolist(),[-1]);self.assertEqual(anchor.tolist(),[-1])

    def test_saved_fit_reconstruction(self):
        with threadpool_limits(limits=2), tempfile.TemporaryDirectory() as tmp:
            x=np.array([[-2.,1],[-1,1],[1,1],[2,1],[3,1]])
            y=np.array([0,0,1,1,1]);r=np.ones(5,dtype=int)
            values=fit_one(x,y,np.arange(4),np.array([4]),r,42,Path(tmp)/'fit.npz')
            self.assertTrue(np.isfinite(values).all())

    def test_real_split_identity_without_fit(self):
        rows,eligible,near=load_inputs();splits=cases(rows,eligible)
        self.assertEqual(len(splits),33);self.assertEqual(len(eligible),4184)
        self.assertEqual(int((near>=0).sum()),2910);self.assertEqual(int(near[near>=0].sum()),168)

if __name__=='__main__':unittest.main()
