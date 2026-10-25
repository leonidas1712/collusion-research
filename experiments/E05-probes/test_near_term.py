import unittest
import json
import numpy as np
from near_term import ROOT, DATA, FIT, saved_splits
from replay2_core import split_inner
from near_term import label_rows, VARIANTS


class NearTermLabels(unittest.TestCase):
    def row(self, give_in=True, rounds=1, steps=3, **changes):
        value=dict(eligible=True,condition='recruiting',ordinal=4,first_read=1,
                   label=int(give_in),first_action=4+steps if give_in else None,
                   steps_until_action=steps if give_in else None,
                   round=2,action_round=2+rounds if give_in else None)
        value.update(changes)
        return value

    def test_round_and_step_boundaries(self):
        rows=[self.row(rounds=0,steps=1),self.row(rounds=1,steps=3),
              self.row(rounds=2,steps=3),self.row(rounds=1,steps=4),self.row(False)]
        a,ay=label_rows(rows,VARIANTS[0]);b,by=label_rows(rows,VARIANTS[1]);c,cy=label_rows(rows,VARIANTS[2])
        self.assertEqual(a.tolist(),[True]*5)
        self.assertEqual(ay.tolist(),[1,1,0,1,0])
        self.assertEqual(b.tolist(),[True,True,False,True,True])
        self.assertEqual(c.tolist(),[True,True,True,False,True])
        self.assertEqual(cy.tolist(),[1,1,1,0,0])

    @unittest.skipUnless((ROOT/'runs'/DATA/'rows.jsonl').exists() and
                         (ROOT/'runs'/FIT/'loso'/'split-s44-f5.npz').exists(), 'requires replay2 cache')
    def test_saved_stacking_splits_exact(self):
        rows=[json.loads(s) for s in (ROOT/'runs'/DATA/'rows.jsonl').read_text().splitlines()]
        for mode in ('pooled','loso'):
            notes=json.loads((ROOT/'runs'/FIT/mode/'folds.json').read_text())
            for note in notes:
                seed,fold=note['seed'],note['fold']
                with np.load(ROOT/'runs'/FIT/mode/f'split-s{seed}-f{fold}.npz') as d:
                    original_train=d['train']
                for variant in VARIANTS:
                    keep,_=label_rows(rows,variant)
                    _,stacks=saved_splits(rows,mode,note,keep)
                    for j,s in enumerate(stacks):
                        families=set(note['stacking']['folds'][j]['train_families'])
                        original=np.array([i for i in original_train if rows[i]['family'] in families])
                        fit,val,_=split_inner(rows,original,seed+fold*101+j*31,mode=='loso')
                        np.testing.assert_array_equal(s['inner_train'],fit[keep[fit]])
                        np.testing.assert_array_equal(s['inner_validation'],val[keep[val]])

    def test_action_and_benign_excluded(self):
        for variant in VARIANTS:
            keep,_=label_rows([self.row(eligible=False,steps=0),self.row(condition='control')],variant)
            self.assertFalse(keep.any())
            with self.assertRaises(AssertionError):label_rows([self.row(steps=0)],variant)


if __name__=='__main__':unittest.main()
