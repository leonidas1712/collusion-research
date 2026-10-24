"""Teacher-forced likelihood of locally reconstructed API replies, never provider token identity."""
import copy


def reply_tokens(tokenizer, request, record, prompt, thinking):
    from replay import normalize_messages
    choices = (record.get('response') or {}).get('choices') or []
    if not choices:
        return None, 'missing_response'
    message = copy.deepcopy(choices[0].get('message') or {})
    if message.get('reasoning') or message.get('reasoning_details'):
        return None, 'provider_reasoning_requires_adapter'
    if not message.get('content') and not message.get('tool_calls'):
        return None, 'empty_reply'
    message['role'] = 'assistant'
    messages, _ = normalize_messages([*request['messages'], message])
    full = tokenizer.apply_chat_template(messages, tools=request.get('tools'), tokenize=False,
                                         add_generation_prompt=False, enable_thinking=thinking)
    if not full.startswith(prompt):
        # Qwen drops the empty generation-time thinking block when rendering history.
        empty_think = '<think>\n\n</think>\n\n'
        if prompt.endswith(empty_think) and full.startswith(prompt[:-len(empty_think)]):
            suffix = full[len(prompt)-len(empty_think):]
            ids = tokenizer.encode(suffix, add_special_tokens=False)
            return (ids, 'qwen_empty_think_continuation_adapter') if ids else (None, 'empty_serialized_reply')
        return None, 'template_prompt_prefix_mismatch'
    suffix = full[len(prompt):]
    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    full_ids = tokenizer.encode(full, add_special_tokens=False)
    if full_ids[:len(prompt_ids)] != prompt_ids:
        # Preserve the original prompt IDs when BPE would merge across the boundary.
        ids = tokenizer.encode(suffix, add_special_tokens=False)
        return (ids, 'separate_reply_tokenization_at_prompt_boundary') if ids else (None, 'empty_serialized_reply')
    ids = full_ids[len(prompt_ids):]
    if not ids:
        return None, 'empty_serialized_reply'
    return ids, 'hf_serialized_reply_including_template_terminator'


def score_reply(model, prompt_ids, reply_ids, device, chunk_size=64):
    import torch
    if model.config.model_type not in ('qwen2', 'qwen3', 'qwen3_moe'):
        return {'status': 'unsupported_likelihood_head_adapter'}
    ids = torch.tensor([prompt_ids + reply_ids], device=device)
    with torch.inference_mode():
        hidden = model.base_model(input_ids=ids, attention_mask=torch.ones_like(ids),
                                  use_cache=False, return_dict=True).last_hidden_state
        return score_hidden(model, hidden, len(prompt_ids), reply_ids, chunk_size)


def score_hidden(model, hidden, prompt_length, reply_ids, chunk_size=64):
    """Project only reply-predicting positions from the already-computed decoder output."""
    import torch
    head = model.get_output_embeddings()
    total_nll, hits = 0.0, 0
    with torch.inference_mode():
        for offset in range(0, len(reply_ids), chunk_size):
            targets = torch.tensor(reply_ids[offset:offset+chunk_size], device=head.weight.device)
            start = prompt_length - 1 + offset
            logits = head(hidden[0, start:start+len(targets)].to(head.weight.device)).float()
            logp = logits.log_softmax(-1)
            total_nll -= logp.gather(-1, targets[:, None]).sum().item()
            hits += (logits.topk(min(5, logits.shape[-1]), dim=-1).indices == targets[:, None]).any(-1).sum().item()
    return {'n_reply_tokens': len(reply_ids), 'mean_token_nll': total_nll / len(reply_ids),
            'mean_token_logprob': -total_nll / len(reply_ids), 'top5_fraction': hits / len(reply_ids)}
