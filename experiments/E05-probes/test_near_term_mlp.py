import tempfile
import unittest
from pathlib import Path
from near_term_mlp import inputs, paired_metrics, reconstruct, ROOT, DATA, FIT, NEAR
import numpy as np
import torch
from replay2_models import fit_mlp, score_mlp, save_mlp
from threadpoolctl import threadpool_limits


class NearTermMLPTests(unittest.TestCase):
    @unittest.skipUnless(
        all(p.exists() for p in (
            ROOT / "runs" / DATA / "rows.jsonl",
            ROOT / "runs" / FIT / "pooled" / "split-s42-f0.npz",
            ROOT / "runs" / NEAR / "B_round_contrast" / "pooled" / "s42-f0" / "scores.npz",
            ROOT / "runs" / NEAR / "probe_scores.csv",
        )), "requires regenerated replay2 splits and near-term score artifacts")
    def test_saved_memberships_and_logistic_reference(self):
        rows,labels,cases,reference,columns=inputs()
        self.assertEqual(len(cases),66)
        self.assertEqual(len(reference),32220)
        self.assertEqual(int(labels['A_hazard'][0].sum()),2910)
        self.assertEqual(int(labels['B_round_contrast'][0].sum()),2460)
        self.assertIn('label_variant',columns)

    def test_two_threads_and_persisted_model(self):
        x=np.array([[-2.,1],[-1.,0],[1.,0],[2.,1]],dtype=np.float32)
        with threadpool_limits(limits=2), tempfile.TemporaryDirectory() as tmp:
            model=fit_mlp(x,np.array([0,0,1,1]),np.ones(4),42,threads=2)
            self.assertEqual(torch.get_num_threads(),2)
            self.assertEqual(len(model[2]),80)
            path=Path(tmp)/'model.npz';save_mlp(path,model)
            np.testing.assert_allclose(reconstruct(path,x),score_mlp(model,x),atol=1e-5)

    def test_identical_scores_have_zero_paired_difference(self):
        rows=[{'round':1,'scenario':'s','family':str(i//2)} for i in range(8)]
        y=np.array([0,1]*4);scores=np.tile(np.arange(8),(3,1))
        result=paired_metrics(rows,np.arange(8),y,{'mlp':scores,'nested':scores},np.zeros((3,8),dtype=int),50)
        for delta in result['mlp_minus_nested'].values():
            self.assertEqual(delta['mean'],0)
            self.assertEqual(delta['paired_family_ci95'],[0,0])


if __name__=='__main__':unittest.main()
