import unittest
from precommitment import extract, body

class PriorInputTest(unittest.TestCase):
    def test_current_turn_reasoning(self):
        messages=[{'role':'assistant','content':'older public','reasoning':'old private'}, {'role':'user','content':'peer'}, {'role':'assistant','reasoning':'same turn','tool_calls':[{'function':{'name':'read_file','arguments':'{}'}}]}, {'role':'tool','content':'excluded'}]
        ak=extract(messages,'gpt-oss','AkashML')
        self.assertNotIn('old private',str(ak))
        self.assertIn('older public',str(ak))
        self.assertIn('same turn',str(ak))
        self.assertNotIn('excluded',str(ak))
        self.assertNotIn('reasoning',str(extract(messages,'gpt-oss','DekaLLM')))
        self.assertNotIn('reasoning',str(extract(messages,'qwen',None)))
    def test_no_current_reply(self):
        self.assertEqual(extract([{'role':'user','content':'share it'}],'qwen',None),[])
    def test_unknown_provider_stops(self):
        with self.assertRaises(AssertionError):extract([],'gpt-oss','unknown')
    def test_payload(self):
        b=body('[]')
        self.assertEqual(set(b['questions']['precommitment']['criteria']),{'yes','no'})

if __name__=='__main__':unittest.main()
