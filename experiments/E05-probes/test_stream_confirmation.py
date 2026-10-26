"""Boundary and arithmetic checks for frozen, inference-only confirmation."""
import unittest
import numpy as np
from score_stream_confirmation import direction, select_rows, summarize_alarms


def row(episode, ordinal, action=None, eligible=True, postask=True, condition='recruiting'):
    return dict(episode=episode, ordinal=ordinal, first_action=action, first_read=1,
                eligible=eligible, post_ask=postask, condition=condition)


class ConfirmationTests(unittest.TestCase):
    def test_action_row_added_only_for_existing_eligible_episode(self):
        rows = [row('a', 2, 3), row('a', 3, 3, False), row('a', 4, 3, False),
                row('b', 2, 2, False), row('c', 2, None, True, False)]
        result = select_rows(rows)
        self.assertEqual([(r['episode'], r['ordinal'], r['y_immediate']) for r in result],
                         [('a', 2, 0), ('a', 3, 1)])

    def test_control_requires_eligibility(self):
        rows = [row('c', 1, None, False, condition='control'),
                row('c', 2, None, True, condition='control')]
        self.assertEqual([r['ordinal'] for r in select_rows(rows)], [2])

    def test_saved_scaler_logit_equivalence(self):
        rng = np.random.default_rng(12)
        x = rng.normal(size=(50, 7))
        weights = dict(mean=rng.normal(size=7), scale=rng.uniform(.2, 2, size=7),
                       coef=rng.normal(size=7), intercept=.21)
        d, bias = direction(weights)
        np.testing.assert_allclose(x @ d + bias,
                                   ((x - weights['mean']) / weights['scale']) @ weights['coef'] + .21,
                                   rtol=1e-12, atol=1e-12)

    def test_missing_reasoning_retained_in_end_to_end_denominator(self):
        rows = []
        for name, n, action, alarm in [('leak', 0, 3, False), ('held', 4, None, True)]:
            r = row(name, 3, action)
            r.update(family=name, reasoning_tokens=n, ever_public=action is not None,
                     y_immediate=int(action is not None), alarm=alarm, first_crossing_fraction=None)
            rows.append(r)
        result = summarize_alarms(rows)
        self.assertEqual(result['all_leaking_reply_warning']['denominator'], 1)
        self.assertEqual(result['leaking_reply_with_reasoning_warning']['denominator'], 0)
        self.assertEqual(result['held_recruiting_episode_alarm']['rate'], 1)


if __name__ == '__main__':
    unittest.main()
