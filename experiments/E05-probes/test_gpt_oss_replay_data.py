"""Artifact checks must reject wrong tokens, missing layers and corrupt activations."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from gpt_oss_replay_data import verify_artifact, token_hash, window_counts


class ReplayDataChecks(unittest.TestCase):
    def test_capture_checks(self):
        row = dict(row_id='episode::request_idx=1', prompt_ids=[1, 2], reply_ids=[3, 4],
                   n_tokens=2, reasoning_positions=[2], prompt_sha256=token_hash([1, 2]),
                   input_ids_sha256=token_hash([1, 2, 3, 4]))
        arrays = dict(input_ids=np.array([1, 2, 3, 4]), reasoning_positions=np.array([2]),
                      layer_indices=np.arange(24), residual_last=np.zeros((24, 2880)),
                      residual_reasoning=np.zeros((24, 1, 2880)))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'capture.npz'
            np.savez(path, **arrays)
            self.assertEqual(verify_artifact(path, row).shape, (24, 2880))
            for key, bad in [('input_ids', np.array([1, 2, 3, 5])),
                             ('layer_indices', np.arange(1, 25)),
                             ('residual_reasoning', np.full((24, 1, 2880), np.nan))]:
                with self.subTest(key=key):
                    np.savez(path, **{**arrays, key: bad})
                    with self.assertRaises(AssertionError):
                        verify_artifact(path, row)

    def test_step_and_episode_denominators_differ(self):
        rows = [dict(episode='positive', label=1)]*2 + [dict(episode='held', label=0)]*3
        self.assertEqual(window_counts(rows), dict(steps=5, positive_steps=2, episodes=2, positive_episodes=1))


if __name__ == '__main__':
    unittest.main()
