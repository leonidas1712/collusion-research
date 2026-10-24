import unittest
import numpy as np
from exposure_probe import auc, episode_split, fit_predict

class ExposureProbeTests(unittest.TestCase):
    def test_auc_ties_and_group_disjointness(self):
        self.assertEqual(auc([0,1],[0,1]),1)
        self.assertEqual(auc([0,1],[1,0]),0)
        self.assertEqual(auc([0,1],[1,1]),.5)
        groups=[str(i//3) for i in range(60)]
        test=episode_split(groups)
        self.assertFalse(set(np.asarray(groups)[test]) & set(np.asarray(groups)[~test]))
        np.testing.assert_array_equal(test,episode_split(groups))

    def test_linear_signal_generalizes_and_scaler_is_train_only(self):
        rng=np.random.default_rng(4);x=rng.normal(size=(200,8));y=np.tile([0,1],100)
        x[:,0]=y*4-2
        scores,model=fit_predict(x[:140],y[:140],x[140:])
        self.assertEqual(auc(y[140:],scores),1.)
        np.testing.assert_allclose(model['mean'],x[:140].mean(0))
        self.assertLess(auc(y[140:],-scores),.01)

if __name__=='__main__':unittest.main()
