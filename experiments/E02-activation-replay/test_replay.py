import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch
from transformers import Qwen2Config, Qwen2Model

from replay import capture, decoder_layers, final_episodes, first_leak_request, normalize_messages, request_rows


class ReplayTests(unittest.TestCase):
    def test_block_outputs_match_reference_and_final_is_pre_norm(self):
        torch.manual_seed(1)
        model = Qwen2Model(Qwen2Config(vocab_size=32, hidden_size=16, intermediate_size=32,
                          num_hidden_layers=2, num_attention_heads=2, num_key_value_heads=2)).eval()
        _, layers = decoder_layers(model)
        ids = [1, 5, 8, 2]
        before = [set(layer._forward_hooks) for layer in layers]
        actual = capture(model, layers, ids, 'cpu')
        self.assertEqual(before, [set(layer._forward_hooks) for layer in layers])
        with torch.inference_mode():
            out = model(torch.tensor([ids]), output_hidden_states=True, use_cache=False)
        np.testing.assert_allclose(actual[0], out.hidden_states[1][0,-1].numpy(), rtol=1e-5, atol=1e-6)
        with torch.inference_mode():
            normalized = model.norm(torch.tensor(actual[-1])).numpy()
        np.testing.assert_allclose(normalized, out.last_hidden_state[0,-1].numpy(), rtol=1e-5, atol=1e-6)
        self.assertFalse(np.allclose(actual[-1], normalized))

    def test_source_immutable_and_json_argument_semantics(self):
        original = [{'role':'assistant', 'tool_calls':[{'function':{'name':'x','arguments':'{"content":"a\\nb"}'}}]}]
        saved = copy.deepcopy(original)
        converted, changes = normalize_messages(original)
        self.assertEqual(original, saved)
        self.assertEqual(converted[0]['tool_calls'][0]['function']['arguments']['content'], 'a\nb')
        self.assertEqual(len(changes), 1)
        with self.assertRaises(ValueError):
            normalize_messages([{'tool_calls':[{'function':{'arguments':'not json'}}]}])

    def test_retries_do_not_increment_step(self):
        ep = {'requests':[{'actor':'recruiter','round':1},
                          {'actor':'target','round':1,'attempt':1},
                          {'actor':'target','round':1,'attempt':2},
                          {'actor':'target','round':1,'attempt':1},
                          {'actor':'target','round':2,'attempt':1}]}
        self.assertEqual([(i,s) for i,s,_ in request_rows(ep)], [(1,1),(2,1),(3,2),(4,1)])

    def test_only_final_complete_nonfake_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); (p/'episodes').mkdir()
            for name, status, fake in [('episode-1.json','complete',False),
                ('episode-1.partial.json','complete',False),('episode-1.attempt-1.json','complete',False),
                ('sweep-cell.json','complete',False),('episode-2.json','incomplete',False),('episode-3.json','complete',True)]:
                (p/'episodes'/name).write_text(json.dumps({'status':status,'fake':fake}))
            self.assertEqual(len(final_episodes([p,p])), 2)

    def test_leak_call_and_suppressed_final_text(self):
        def record(msg, rnd=1):
            return {'actor':'target','round':rnd,'response':{'choices':[{'finish_reason':'stop','message':msg}]}}
        ep={'label':{'objective_success':True,'disclosure_kind_evidence':[{'token':'MARKER'}]},
            'tool_log':[{'actor':'target','round':1,'name':'send_message','call_id':'a','result':{'delivered':True}},
                        {'actor':'target','round':2,'name':'send_message','call_id':'b','result':{'delivered':True}}],
            'requests':[record({'tool_calls':[{'id':'a','function':{'arguments':'{"content":"safe"}'}}]}),
                        record({'content':'MARKER'}),
                        record({'tool_calls':[{'id':'b','function':{'arguments':'{"content":"MARKER"}'}}]},2),
                        record({'content':'later'},2)]}
        self.assertEqual(first_leak_request(ep),2)
        ep['label']['objective_success']=False
        self.assertIsNone(first_leak_request(ep))


if __name__ == '__main__':
    unittest.main()
