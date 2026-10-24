import copy
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import torch
from transformers import Qwen2Config, Qwen2ForCausalLM
from replay import capture, decoder_layers, digest, parser
from fidelity import score_hidden, score_reply, reply_tokens
from replay_manifest import select_manifest


class VerifiedReplayTests(unittest.TestCase):
    def test_shared_forward_preserves_prompt_endpoint_and_scores(self):
        torch.manual_seed(9)
        model = Qwen2ForCausalLM(Qwen2Config(vocab_size=32, hidden_size=16, intermediate_size=32,
            num_hidden_layers=2, num_attention_heads=2, num_key_value_heads=2)).eval()
        _, layers = decoder_layers(model)
        prompt, reply = [1,2,3,4], [9,8,7]
        expected = capture(model.base_model, layers, prompt, 'cpu')
        calls=[]
        hook=model.base_model.register_forward_hook(lambda *args: calls.append(1))
        actual, hidden = capture(model.base_model, layers, prompt+reply, 'cpu', len(prompt), True)
        result=score_hidden(model,hidden,len(prompt),reply)
        hook.remove()
        self.assertEqual(len(calls),1)
        np.testing.assert_allclose(actual,expected,rtol=1e-5,atol=1e-6)
        reference=score_reply(model,prompt,reply,'cpu')
        self.assertAlmostEqual(result['mean_token_nll'],reference['mean_token_nll'],places=6)
        self.assertEqual(result['top5_fraction'],reference['top5_fraction'])
        self.assertTrue(parser().parse_args([]).reply_fidelity)
        self.assertFalse(parser().parse_args(['--activations-only']).reply_fidelity)

    def test_manifest_relocation_and_tampering(self):
        class Tokenizer:
            def apply_chat_template(self,*args,tokenize,**kwargs):return [1,2] if tokenize else 'prompt'
        ep={'requests':[{'actor':'target','round':1,'request':{'messages':[]}}]}
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'episode.json';source.write_text(json.dumps(ep))
            row=dict(run_id='source',episode_file='runs/source/episodes/episode.json',request_idx=0,
                episode_sha256=digest(source.read_bytes()),request_sha256=digest(ep['requests'][0]['request']),
                prompt_sha256=digest(b'prompt'),input_ids_sha256=digest([1,2]),n_tokens=2,round=1,step_in_turn=1)
            manifest=Path(tmp)/'selection.jsonl'
            manifest.write_text(json.dumps(row)+'\n')
            selection,metadata=select_manifest(manifest,[('source',source,ep)],Tokenizer(),'off')
            self.assertEqual(len(selection[source]),1)
            for field in ('prompt_sha256','input_ids_sha256','episode_sha256','n_tokens','request_sha256'):
                changed=copy.deepcopy(row);changed[field]='wrong';manifest.write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError,'mismatch'):
                    select_manifest(manifest,[('source',source,ep)],Tokenizer(),'off')
            manifest.write_text(json.dumps(row)+'\n'+json.dumps(row))
            with self.assertRaisesRegex(ValueError,'Duplicate'):
                select_manifest(manifest,[('source',source,ep)],Tokenizer(),'off')

    def test_reply_boundary_merge_keeps_original_prompt(self):
        class Tokenizer:
            def apply_chat_template(self,*args,**kwargs):return 'prompt reply'
            def encode(self,text,**kwargs):return {'prompt':[1,2],'prompt reply':[1,3,4],' reply':[5,4]}[text]
        record={'response':{'choices':[{'message':{'content':' reply'}}]}}
        self.assertEqual(reply_tokens(Tokenizer(),{'messages':[]},record,'prompt',False),
            ([5,4],'separate_reply_tokenization_at_prompt_boundary'))

    def test_empty_think_adapter_preserves_prompt_and_reply_text(self):
        class Tokenizer:
            def apply_chat_template(self,*args,**kwargs):return 'assistant\n\n reply<end>'
            def encode(self,text,**kwargs):return list(text.encode())
        prompt='assistant\n<think>\n\n</think>\n\n'
        record={'response':{'choices':[{'message':{'content':'\n reply'}}]}}
        ids,status=reply_tokens(Tokenizer(),{'messages':[]},record,prompt,False)
        self.assertEqual(bytes(ids).decode(),'\n reply<end>')
        self.assertEqual(status,'qwen_empty_think_continuation_adapter')

if __name__=='__main__':unittest.main()
