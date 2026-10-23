import tempfile
import unittest
from pathlib import Path
import torch
from transformers import Qwen2Config, Qwen2ForCausalLM
from fidelity import score_reply, reply_tokens
from modal_inputs import pack_runs


class FidelityTests(unittest.TestCase):
    def test_shift_and_chunking_match_full_logits(self):
        torch.manual_seed(7)
        model = Qwen2ForCausalLM(Qwen2Config(vocab_size=32, hidden_size=16, intermediate_size=32,
            num_hidden_layers=2, num_attention_heads=2, num_key_value_heads=2)).eval()
        prompt, reply = [1, 4, 2], [7, 9, 3, 5]
        actual = score_reply(model, prompt, reply, 'cpu', chunk_size=2)
        with torch.inference_mode():
            logits = model(torch.tensor([prompt+reply])).logits[0, len(prompt)-1:-1].float()
            expected = torch.nn.functional.cross_entropy(logits, torch.tensor(reply)).item()
            hits = (logits.topk(5).indices == torch.tensor(reply)[:,None]).any(-1).float().mean().item()
        self.assertAlmostEqual(actual['mean_token_nll'], expected, places=5)
        self.assertEqual(actual['top5_fraction'], hits)

    def test_missing_and_unaligned_replies_are_not_scored(self):
        self.assertEqual(reply_tokens(None, {}, {}, '', False), (None, 'missing_response'))
        class Tokenizer:
            def apply_chat_template(self, *args, **kwargs): return 'different prefix'
        record = {'response': {'choices':[{'message':{'content':'reply'}}]}}
        self.assertEqual(reply_tokens(Tokenizer(), {'messages':[]}, record, 'prompt', False),
                         (None, 'template_prompt_prefix_mismatch'))

    def test_upload_excludes_partial_fake_and_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'runs'/'sample'/'episodes'; path.mkdir(parents=True)
            (path/'ok.json').write_text('{"status":"complete"}')
            (path/'bad.partial.json').write_text('{"status":"complete"}')
            (path/'fake.json').write_text('{"status":"complete","fake":true}')
            (path/'.env').write_text('secret')
            self.assertEqual(list(pack_runs(tmp,['sample'])['sample']), ['ok.json'])
            with self.assertRaises(ValueError): pack_runs(tmp,['../sample'])
