import unittest
from check_peer_isolation import audit


def episode(reasoning, public, incoming=None):
    incoming = '[peer] '+public if incoming is None else incoming
    return {
        'status': 'complete', 'rounds_completed': 1,
        'scenario_spec': {'channel_format': '[{name}] {content}',
                          'actor_names': {'recruiter': 'peer'}, 'target_task': 'Task'},
        'channel': [{'actor': 'recruiter', 'content': public}],
        'requests': [
            {'actor': 'recruiter', 'response': {'choices': [{'message': {'reasoning': reasoning}}]}},
            {'actor': 'target', 'request': {'messages': [{'role': 'user', 'content': incoming}]}},
        ],
    }


class IsolationChecks(unittest.TestCase):
    def test_single_character_coincidence_retains_raw_evidence(self):
        result = audit(episode('I', 'I need the report.'))
        self.assertTrue(result['passed'])
        self.assertTrue(result['peer_reasoning'][0]['appears_in_public'])
        self.assertFalse(result['peer_reasoning'][0]['informative_public_match'])

    def test_long_reasoning_copied_to_public_fails(self):
        text = 'Private reasoning that should never be published to the target.'
        self.assertFalse(audit(episode(text, 'Prefix '+text))['passed'])

    def test_short_exact_public_copy_fails(self):
        self.assertFalse(audit(episode('Secret', 'Secret'))['passed'])

    def test_unpublished_target_input_fails_projection(self):
        self.assertFalse(audit(episode('Private', 'Public', incoming='[peer] Private'))['passed'])

    def test_missing_reasoning_is_explicit(self):
        result = audit(episode(None, 'Public'))
        self.assertTrue(result['passed'])
        self.assertFalse(result['reasoning_observed'])


if __name__ == '__main__':
    unittest.main()
