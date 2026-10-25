import unittest
import numpy as np
import torch
from transformers import AutoModelForCausalLM,GptOssConfig
from gpt_oss_replay import capture,score_positions,render


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.manual_seed(42)
        cfg=GptOssConfig(vocab_size=64,hidden_size=32,intermediate_size=32,num_hidden_layers=2,
            num_attention_heads=4,num_key_value_heads=2,head_dim=8,num_local_experts=4,num_experts_per_tok=2)
        cls.model=AutoModelForCausalLM.from_config(cfg,attn_implementation='eager').eval()

    def test_prompt_state_is_causal_and_reasoning_positions_match(self):
        m=self.model
        a,reason,hidden=capture(m,[1,2,3,4,5],3,[3,4],'cpu')
        b,empty,_=capture(m,[1,2,3],3,[],'cpu')
        np.testing.assert_allclose(a,b,atol=1e-6,rtol=1e-5)
        self.assertEqual(reason.shape,(2,2,32));self.assertEqual(empty.shape,(2,0,32))
        with torch.inference_mode():
            native=m.base_model(input_ids=torch.tensor([[1,2,3,4,5]]),use_cache=False,output_hidden_states=True)
        # Last native hidden state has final normalization; block 0 has none.
        np.testing.assert_allclose(reason[0],native.hidden_states[1][0,[3,4]].numpy(),atol=1e-6)
        metrics=score_positions(m,hidden,[1,2,3,4,5],[3,4])
        with torch.inference_mode():
            logits=m.get_output_embeddings()(hidden[0,[2,3]]).float()
            expected=-logits.log_softmax(-1)[[0,1],[4,5]].mean().item()
        self.assertAlmostEqual(metrics['mean_token_nll'],expected,places=6)

    def test_hooks_removed(self):
        capture(self.model,[1,2],1,[1],'cpu')
        self.assertTrue(all(not x._forward_hooks for x in self.model.model.layers))


class HarmonyTests(unittest.TestCase):
    def test_missing_response_still_has_the_exact_prompt(self):
        record={'request':{'messages':[{'role':'system','content':'Answer.'},{'role':'user','content':'Please proceed.'}], 'tools':[]}}
        empty=render(record,'2026-10-25')
        record['response']={'choices':[{'message':{'role':'assistant','content':'Done.'}}]}
        complete=render(record,'2026-10-25')
        self.assertEqual(empty['prompt_ids'],complete['prompt_ids'])
        self.assertEqual(empty['reply_ids'],[])
        self.assertEqual(empty['reasoning_positions'],[])
        self.assertEqual(empty['reply_status'],'missing_or_empty')

    def test_literal_harmony_text_is_not_promoted_to_control_token(self):
        import openai_harmony as h
        text='The literal marker is <|channel|>.'
        record={'request':{'messages':[{'role':'system','content':'Answer.'},{'role':'user','content':'Show a literal.'}], 'tools':[]},
                'response':{'choices':[{'message':{'role':'assistant','content':text}}]}}
        row=render(record,'2026-10-25');ids=row['prompt_ids']+row['reply_ids']
        enc=h.load_harmony_encoding(h.HarmonyEncodingName.HARMONY_GPT_OSS)
        body=[ids[i] for i in row['answer_positions']]
        self.assertEqual(enc.decode(body),text)
        control=enc.encode('<|channel|>',allowed_special='all')[0]
        self.assertNotIn(control,body)

    def test_reasoning_span_excludes_headers_and_raw_tool_json(self):
        import openai_harmony as h
        record={'request':{'messages':[{'role':'system','content':'Read the file.'},
                                       {'role':'user','content':'Please proceed.'}],
                           'reasoning':{'effort':'low'},
                           'tools':[{'type':'function','function':{'name':'read_file','description':'Read a file',
                                     'parameters':{'type':'object','properties':{'path':{'type':'string'}}}}}]},
                'response':{'choices':[{'message':{'role':'assistant','reasoning':'Read the requested file first.',
                              'tool_calls':[{'id':'call1','type':'function','function':{'name':'read_file','arguments':'{ "path": "example.txt" }'}}]}}]}}
        row=render(record,'2026-10-25')
        enc=h.load_harmony_encoding(h.HarmonyEncodingName.HARMONY_GPT_OSS)
        ids=row['prompt_ids']+row['reply_ids']
        self.assertEqual(enc.decode([ids[i] for i in row['reasoning_positions']]),'Read the requested file first.')
        self.assertEqual(enc.decode([ids[i] for i in row['answer_positions']]),'{ "path": "example.txt" }')
        self.assertTrue(all(i>=len(row['prompt_ids']) for i in row['reasoning_positions']))


if __name__=='__main__':unittest.main()
