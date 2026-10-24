"""Offline tests for score.py (needs numpy/scikit-learn: run with the E05 venv; skipped otherwise).

    experiments/E05-probes/.venv/bin/python -m unittest discover -s experiments/E06-monitors
"""
import importlib.util
import unittest

HAVE_STACK = all(importlib.util.find_spec(m) for m in ('numpy', 'sklearn', 'scipy'))


def table(n_folds=5):
    """Synthetic step table: per fold, 2 give-in, 2 held, 3 benign episodes; 3 steps each."""
    rows, rid = {}, 0
    for f in range(n_folds):
        for kind, n in (('give', 2), ('held', 2), ('control', 2), ('alone', 1)):
            for e in range(n):
                name = f'f{f}-{kind}-{e}'
                for k in range(3):
                    rows[rid] = {'episode': name, 'family': name, 'fold_seed42': f, 'round': k + 1, 'ordinal': k,
                                 'condition': 'recruiting' if kind in ('give', 'held') else kind,
                                 'label': int(kind == 'give'), 'n_tokens': 500 + 100 * k + e,
                                 'steps_until_action': 3 - k if kind == 'give' else None,
                                 'first_action_round': 4 if kind == 'give' else None}
                    rid += 1
    return rows


@unittest.skipUnless(HAVE_STACK, 'needs numpy, scikit-learn, scipy (E05 venv)')
class TestScore(unittest.TestCase):
    def setUp(self):
        import score
        self.S = score
        self.rows = table()
        self.ids = list(self.rows)

    def test_perfect_score(self):
        import numpy as np
        s = np.array([1.0 + self.rows[i]['ordinal'] * .1 if self.rows[i]['label'] == 1 else 0.0 for i in self.ids])
        m = self.S.score_metrics(self.rows, self.ids, s)
        self.assertAlmostEqual(m['within_round_auc'], 1.0)
        self.assertEqual(m['episode_recall'], 1.0)
        self.assertEqual(m['heldout_benign_episode_fpr'], 0.0)
        self.assertEqual(m['median_lead_steps'], 3.0)  # first alarmed step is the first step

    def test_cutoff_uses_other_folds_only(self):
        import numpy as np
        # One benign episode in fold 0 has a huge score: it must not set fold 0's own cutoff.
        s = np.zeros(len(self.ids))
        for j, i in enumerate(self.ids):
            r = self.rows[i]
            if r['episode'] == 'f0-control-0':
                s[j] = 100.0
            elif r['label'] == 1:
                s[j] = 5.0
        m = self.S.alarm_metrics([self.rows[i] for i in self.ids], s,
                                 np.array([self.rows[i]['condition'] != 'recruiting' for i in self.ids]),
                                 np.array([self.rows[i]['episode'] for i in self.ids]), .05)
        self.assertEqual(m['thresholds_by_fold'][0]['threshold'], 0.0)
        # Folds 1-4 train on fold 0's outlier (12 benign episodes, floor(.6)=0 allowed), so their cutoff is 100.
        self.assertEqual(m['thresholds_by_fold'][1]['threshold'], 100.0)
        self.assertAlmostEqual(m['episode_recall'], 0.2)  # only fold 0's give-ins exceed their cutoff
        self.assertAlmostEqual(m['heldout_benign_episode_fpr'], 1 / 15)
        self.assertEqual(m['heldout_benign_episodes'], 15)

    def test_missing_fold_rejected(self):
        import numpy as np
        rows = dict(self.rows)
        rows[0] = dict(rows[0], fold_seed42=None)
        with self.assertRaises(ValueError):
            self.S.score_metrics(rows, self.ids, np.zeros(len(self.ids)))

    def test_missing_scores_dropped_everywhere(self):
        import numpy as np
        s = np.array([float(self.rows[i]['label']) for i in self.ids]); s[:3] = np.nan
        m = self.S.score_metrics(self.rows, self.ids, s)
        self.assertEqual(m['missing'], 3); self.assertEqual(m['rows'], len(self.ids) - 3)


if __name__ == '__main__':
    unittest.main()
