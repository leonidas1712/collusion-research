"""Synthetic checks for near-term labels, group splits and the saved CPU model path."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from gpt_oss_probes import make_plan, label_rows, fit_case


def fixture():
    rows = []
    for scenario in range(6):
        for family in range(16):
            for condition in ['recruiting', 'control']:
                label = int(condition == 'recruiting' and family % 2 == 0)
                for ordinal, rnd in [(2, 1), (3, 2), (4, 3)]:
                    rows.append(dict(episode=f'{scenario}/{family}/{condition}', family=f'{scenario}-{family}',
                        scenario=f's{scenario}', condition=condition, ordinal=ordinal, first_read=1,
                        first_action=5 if label else None, action_round=4 if label else None,
                        steps_until_action=5-ordinal if label else None, round=rnd, label=label,
                        eligible=ordinal >= 3, eligible_pre_ask=ordinal == 2, n_tokens=100+ordinal))
    return rows


class ProbeChecks(unittest.TestCase):
    def test_labels_and_group_splits(self):
        rows = fixture()
        keep, y = label_rows(rows, 'post_ask', 'A_hazard')
        positive = [i for i, r in enumerate(rows) if r['label'] and r['ordinal'] == 3]
        self.assertTrue(keep[positive].all())
        self.assertTrue((y[positive] == 0).all())
        contrast, _ = label_rows(rows, 'post_ask', 'B_round_contrast')
        self.assertFalse(contrast[positive].any())
        step_contrast, step_y = label_rows(rows, 'post_ask', 'C_step_contrast')
        self.assertTrue(step_contrast[positive].all())
        self.assertTrue((step_y[positive] == 1).all())
        plans = make_plan(rows)
        self.assertEqual(len(plans), 165)
        for p in plans:
            split = p['split']
            self.assertFalse({rows[i]['family'] for i in split['train']} &
                             {rows[i]['family'] for i in split['test']})
            self.assertTrue(all(rows[i]['condition'] == 'control' for i in split['calibration']))
            if p['mode'] == 'loso':
                self.assertFalse({rows[i]['scenario'] for i in split['train']} &
                                 {rows[i]['scenario'] for i in split['test']})

    def test_fit_exports_finite_test_and_calibration_scores(self):
        rows = fixture()
        plan = next(p for p in make_plan(rows) if p['variant'] == 'A_hazard')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root/'data'; data.mkdir()
            (data/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            x = np.random.default_rng(7).normal(size=(len(rows), 24, 8)).astype('float32')
            np.save(data/'features.npy', x)
            result = fit_case((data, root/'output', plan))
            self.assertIn(result['layer'], [0, 1, 3, 4, 6, 7, 9, 10, 12, 13, 15, 16, 18, 19, 20, 22, 23])
            path = root/'output'/plan['window']/plan['variant']/plan['mode']/f"s{plan['seed']}-f{plan['fold']}"/'scores.npz'
            with np.load(path) as saved:
                self.assertTrue(np.isfinite(saved['nested']).all())
                self.assertEqual(len(saved['nested']), len(saved['test'])+len(saved['calibration']))


if __name__ == '__main__':
    unittest.main()
