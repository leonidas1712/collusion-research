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
        return None, 'template_prompt_prefix_mismatch'
    suffix = full[len(prompt):]
    ids = tokenizer.encode(suffix, add_special_tokens=False)
    if not ids:
        return None, 'empty_serialized_reply'
    return ids, 'hf_serialized_reply_including_template_terminator'


def score_reply(model, prompt_ids, reply_ids, device, chunk_size=64):
    import torch
    ids = torch.tensor([prompt_ids + reply_ids], device=device)
    with torch.inference_mode():
        hidden = model.base_model(input_ids=ids, attention_mask=torch.ones_like(ids),
                                  use_cache=False, return_dict=True).last_hidden_state
        head = model.get_output_embeddings()
        total_nll, hits = 0.0, 0
        for offset in range(0, len(reply_ids), chunk_size):
            targets = torch.tensor(reply_ids[offset:offset+chunk_size], device=head.weight.device)
            start = len(prompt_ids) - 1 + offset
            logits = head(hidden[0, start:start+len(targets)].to(head.weight.device)).float()
            logp = logits.log_softmax(-1)
            total_nll -= logp.gather(-1, targets[:, None]).sum().item()
            hits += (logits.topk(min(5, logits.shape[-1]), dim=-1).indices == targets[:, None]).any(-1).sum().item()
    return {'n_reply_tokens': len(reply_ids), 'mean_token_nll': total_nll / len(reply_ids),
            'mean_token_logprob': -total_nll / len(reply_ids), 'top5_fraction': hits / len(reply_ids)}
