"""CPU checks of fixed projections, fp16 feature storage, and hook cleanup."""
import numpy as np

def test_projected_capture_matches_saved_full_features():
    import torch
    from transformers import AutoModelForCausalLM,GptOssConfig
    from gpt_oss_replay import capture as original
    from gpt_oss_stream_capture import capture
    torch.manual_seed(7);torch.set_num_threads(1)
    c=GptOssConfig(vocab_size=64,hidden_size=32,intermediate_size=32,num_hidden_layers=2,num_attention_heads=4,num_key_value_heads=2,head_dim=8,num_local_experts=4,num_experts_per_tok=2)
    m=AutoModelForCausalLM.from_config(c,attn_implementation='eager').float().eval()
    ids=list(range(12));positions=[2,3,4,5,6,7];rng=np.random.default_rng(20261026)
    rp=(rng.integers(0,2,size=(2,32,8))*2-1).astype(np.float32)/np.sqrt(8)
    a,b,h=original(m,ids,4,positions,'cpu')
    full,sketch,last,_=capture(m,ids,4,positions,torch.tensor(rp,dtype=torch.float32),[0,1])
    np.testing.assert_array_equal(last,a);np.testing.assert_array_equal(full,b.astype(np.float16))
    np.testing.assert_allclose(sketch,np.stack([b[i]@rp[i] for i in range(2)]).astype(np.float16),atol=1e-4,rtol=1e-3)
    assert full.dtype==np.float16 and sketch.dtype==np.float16
    assert all(not layer._forward_hooks for layer in m.model.layers)
