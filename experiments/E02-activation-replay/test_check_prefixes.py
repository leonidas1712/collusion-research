import unittest
from check_prefixes import common_prefix, selected_calls

class StepPlanTests(unittest.TestCase):
    def test_cutoff_includes_action_input_but_no_later_request(self):
        calls=[(0,), (2,), (5,), (7,)]
        self.assertEqual(selected_calls(calls,5),calls[:3])
        self.assertEqual(selected_calls(calls,0),calls[:1])
        self.assertEqual(selected_calls(calls,None),calls)

    def test_generation_suffix_is_not_a_history_prefix(self):
        history=[10,11,12]
        prompt=history+[151667,271,151668,271]
        later=history+[55,56,57]
        self.assertEqual(common_prefix(prompt,later),3)
        self.assertEqual(later[:len(prompt)-4],prompt[:-4])
        self.assertEqual(common_prefix(prompt,prompt),len(prompt))
        self.assertEqual(common_prefix(history,prompt),len(history))
        self.assertEqual(common_prefix([],prompt),0)

if __name__=='__main__':unittest.main()
