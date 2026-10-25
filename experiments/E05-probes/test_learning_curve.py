import json
import unittest
from near_term import ROOT, DATA, FIT
from learning_curve import plan_case


class LearningCurveSampling(unittest.TestCase):
    @unittest.skipUnless((ROOT/'runs'/DATA/'rows.jsonl').exists() and
                         (ROOT/'runs'/FIT/'loso'/'split-s42-f0.npz').exists(), 'requires replay2 cache')
    def test_nested_subsets_keep_original_test_rows(self):
        rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
        for name in ('eventual','B_round_contrast'):
            for mode in ('pooled','loso'):
                cases=plan_case(rows,name,mode,42,0)
                self.assertEqual(len(cases),12)
                for draw in range(3):
                    subset=[c for c in cases if c['draw']==draw]
                    for low,high in zip(subset,subset[1:]):
                        self.assertLessEqual(set(low['train_families']),set(high['train_families']))
                        self.assertLessEqual(set(low['train']),set(high['train']))
                        self.assertEqual(low['test'],high['test'])
                    self.assertEqual(len(subset[-1]['train_families']),subset[-1]['total_train_families'])


if __name__=='__main__':unittest.main()
