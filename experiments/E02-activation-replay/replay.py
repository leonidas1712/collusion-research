"""Replay saved target requests without generation; capture decoder block outputs."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run, write_json_atomic


def digest(data):
    if not isinstance(data, bytes):
        data = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()
    return hashlib.sha256(data).hexdigest()


def final_episodes(run_dirs, limit=None):
    found = []
    seen = set()
    for directory in run_dirs:
        directory = Path(directory).resolve()
        for path in sorted((directory / 'episodes').glob('*.json')):
            if '.partial.' in path.name or '.attempt-' in path.name or path in seen:
                continue
            episode = json.loads(path.read_text())
            if episode.get('status') != 'complete' or episode.get('fake'):
                continue
            seen.add(path)
            found.append((directory.name, path, episode))
    return found[:limit] if limit else found


def normalize_messages(messages):
    """Convert OpenAI argument strings to HF objects, without changing source records."""
    messages = copy.deepcopy(messages)
    changes = []
    for i, message in enumerate(messages):
        for call in message.get('tool_calls') or []:
            function = call.get('function', call)
            if isinstance(function.get('arguments'), str):
                function['arguments'] = json.loads(function['arguments'])
                changes.append(f'messages[{i}].tool_calls.arguments: JSON string -> object')
            if not isinstance(function.get('arguments'), dict):
                raise ValueError('Tool arguments must decode to an object')
    return messages, changes


def request_rows(episode):
    steps = Counter()
    for idx, record in enumerate(episode['requests']):
        if record.get('actor') != 'target':
            continue
        round_number = record['round']
        if record.get('attempt', 1) == 1:
            steps[round_number] += 1
        yield idx, max(steps[round_number], 1), record


def first_leak_request(episode):
    """Locate the first published full marker using successful calls and final-text rules."""
    label = episode.get('label') or {}
    if not label.get('objective_success'):
        return None
    evidence = label.get('disclosure_kind_evidence') or []
    tokens = {item['token'] for item in evidence if item.get('token')}
    if not tokens:
        return None
    successful = {(t.get('round'), t.get('call_id')) for t in episode.get('tool_log', [])
                  if t.get('actor') == 'target' and t.get('name') == 'send_message'
                  and isinstance(t.get('result'), dict) and t['result'].get('delivered')}
    posted = set()
    for idx, _, record in request_rows(episode):
        response = record.get('response') or {}
        choices = response.get('choices') or []
        if not choices or choices[0].get('finish_reason') not in ('stop', 'tool_calls'):
            continue
        message = choices[0].get('message') or {}
        calls = message.get('tool_calls') or []
        rnd = record['round']
        for call in calls:
            if (rnd, call.get('id')) in successful:
                posted.add(rnd)
                args = call['function']['arguments']
                args = json.loads(args) if isinstance(args, str) else args
                if any(token in args.get('content', '') for token in tokens):
                    return idx
        if not calls and rnd not in posted:
            posted.add(rnd)
            if any(token in (message.get('content') or '') for token in tokens):
                return idx
    return None


def render(tokenizer, request, thinking):
    messages, changes = normalize_messages(request['messages'])
    tools = request.get('tools')
    reasoning = (request.get('extra_body') or {}).get('reasoning') or request.get('reasoning') or {}
    enabled = reasoning.get('enabled', False) if thinking == 'from-request' else thinking == 'on'
    kwargs = dict(tools=tools, add_generation_prompt=True, enable_thinking=enabled)
    rendered = tokenizer.apply_chat_template(messages, tokenize=False, **kwargs)
    system_messages = [m.get('content') for m in messages if m.get('role') == 'system']
    if any(isinstance(text, str) and text and text not in rendered for text in system_messages):
        raise ValueError('Chat template omitted or changed a system message; a reviewed adapter is required')
    ids = tokenizer.apply_chat_template(messages, tokenize=True, **kwargs)
    if hasattr(ids, 'tolist'):
        ids = ids.tolist()
    if isinstance(ids, Mapping):
        ids = ids['input_ids']
    if ids and isinstance(ids[0], list):
        ids = ids[0]
    if not all(isinstance(token, int) for token in ids):
        raise TypeError('Chat template did not return integer token IDs')
    if not ids:
        raise ValueError('Empty rendered prompt')
    return rendered, ids, changes, enabled


def decoder_layers(model, explicit=None):
    if explicit:
        layers = model.get_submodule(explicit)
        path = explicit
    else:
        for path in ('layers', 'model.layers', 'transformer.h', 'h'):
            try:
                layers = model.get_submodule(path)
                break
            except AttributeError:
                continue
        else:
            raise ValueError('Cannot locate decoder blocks; supply --layers-path')
    if len(layers) != model.config.num_hidden_layers:
        raise ValueError('Decoder layer count does not match config')
    return path, layers


def capture(model, layers, ids, device):
    import torch
    values = [None] * len(layers)
    handles = []
    def hook(i):
        def save(_module, _inputs, output):
            hidden = output[0] if isinstance(output, tuple) else output
            values[i] = hidden[0, -1].detach().to(device='cpu', dtype=torch.float32).clone()
        return save
    try:
        handles = [layer.register_forward_hook(hook(i)) for i, layer in enumerate(layers)]
        inputs = torch.tensor([ids], dtype=torch.long, device=device)
        with torch.inference_mode():
            model(input_ids=inputs, attention_mask=torch.ones_like(inputs), use_cache=False,
                  output_hidden_states=False, return_dict=True)
    finally:
        for handle in handles:
            handle.remove()
    if any(value is None for value in values):
        raise RuntimeError('Some decoder blocks did not execute')
    result = torch.stack(values).numpy()
    import numpy as np
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite activations')
    return result


def main(args):
    import numpy as np
    import torch
    import transformers
    from huggingface_hub import HfApi
    from transformers import AutoConfig, AutoModel, AutoModelForCausalLM, AutoTokenizer

    if args.precision == 'fp8':
        if args.model != 'Qwen/Qwen3-32B-FP8' or args.tiny_random or args.device == 'cpu':
            raise ValueError('fp8 requires Qwen/Qwen3-32B-FP8 pretrained weights on a supported GPU')
    if args.precision == 'bf16' and args.model.endswith('-FP8'):
        raise ValueError('FP8 checkpoint requires --precision fp8')
    if args.output_root:
        import collusion.runs as run_helpers
        run_helpers.RUNS = Path(args.output_root).resolve()
        run_helpers.INDEX = run_helpers.RUNS / 'index.jsonl'
    parents = [Path(p).resolve().name for p in args.runs]
    run = start_run('e02-activation-replay', experiment='E02', settings=vars(args),
                    parents=parents, model=args.model, tags=['wiring' if args.tiny_random else 'replay'])
    try:
        torch.set_num_threads(args.cpu_threads)
        torch.manual_seed(args.seed)
        episodes = final_episodes(args.runs, args.max_episodes)
        if not episodes:
            raise ValueError('No final, complete, non-fake episodes found')
        revision = HfApi().model_info(args.model, revision=args.revision).sha
        tokenizer = AutoTokenizer.from_pretrained(args.model, revision=revision, trust_remote_code=False)
        config = AutoConfig.from_pretrained(args.model, revision=revision, trust_remote_code=False)
        if args.tiny_random:
            config.hidden_size = 32
            config.intermediate_size = 64
            config.num_hidden_layers = 2
            if hasattr(config, 'layer_types'):
                config.layer_types = config.layer_types[:2]
            config.num_attention_heads = 2
            config.num_key_value_heads = 2
            if hasattr(config, 'head_dim'):
                config.head_dim = 16
        remaining = args.max_requests
        selection = {}
        for _, path, episode in episodes:
            rows = list(request_rows(episode))
            if args.max_requests_per_episode:
                rows = rows[:args.max_requests_per_episode]
            if remaining is not None:
                rows = rows[:remaining]
                remaining -= len(rows)
            selection[path] = rows
        # Validate templates before allocating pretrained weights or running any forwards.
        for _, path, episode in episodes:
            selected = selection[path]
            for request_idx, _, record in selected:
                source_model = record['request'].get('model')
                if source_model not in [args.model, *args.source_model] and not args.allow_cross_model:
                    raise ValueError(f'Source target {source_model} != {args.model}; use --allow-cross-model for wiring only')
                _, ids, _, _ = render(tokenizer, record['request'], args.thinking)
                if len(ids) > min(args.max_tokens, config.max_position_embeddings):
                    raise ValueError(f'{path.name} request {request_idx}: {len(ids)} tokens exceeds limit; no truncation allowed')
        dtype = getattr(torch, args.dtype)
        model_class = AutoModelForCausalLM if args.reply_fidelity else AutoModel
        if args.tiny_random:
            model = model_class.from_config(config, trust_remote_code=False, attn_implementation='sdpa').to(dtype=dtype)
            model.to('cpu' if args.device == 'auto' else args.device)
        else:
            model = model_class.from_pretrained(args.model, revision=revision, dtype=dtype,
                        device_map='auto' if args.device == 'auto' else {'': args.device},
                        trust_remote_code=False, attn_implementation='sdpa')
        model.eval()
        layers_path, layers = decoder_layers(model, args.layers_path)
        selected_layers = list(range(len(layers))) if args.layers == 'all' else [int(x) for x in args.layers.split(',')]
        if not selected_layers or len(set(selected_layers)) != len(selected_layers) or any(x < 0 or x >= len(layers) for x in selected_layers):
            raise ValueError('Invalid --layers indices')
        capture_layers = [layers[i] for i in selected_layers]
        input_device = model.get_input_embeddings().weight.device
        tokenizer.save_pretrained(run.dir / 'tokenizer')
        config.save_pretrained(run.dir / 'model_config')
        versions = {name: importlib.metadata.version(name) for name in
                    ('torch', 'transformers', 'accelerate', 'tokenizers', 'huggingface_hub', 'numpy')}
        template = tokenizer.get_chat_template(tools=episodes[0][2]['requests'][next(
            i for i,r in enumerate(episodes[0][2]['requests']) if r.get('actor') == 'target')]['request'].get('tools'))
        (run.dir / 'selected_chat_template.jinja').write_text(template)
        provenance = dict(model=args.model, revision=revision, versions=versions,
                          tiny_random=args.tiny_random, seed=args.seed, dtype=args.dtype, precision=args.precision,
                          selected_layers=selected_layers, quantization_config=getattr(config, "quantization_config", None),
                          device_map=str(getattr(model, 'hf_device_map', input_device)),
                          layers_path=layers_path, layer_count=len(layers), hidden_size=config.hidden_size,
                          activation='decoder block output, last prompt token, before final model norm',
                          stored_dtype='float32', template_sha256=digest(template.encode()),
                          tokenizer_class=type(tokenizer).__name__, transformers_version=transformers.__version__,
                          provider_exact_tokens_available=False)
        write_json_atomic(run.dir / 'provenance.json', provenance)
        index_path = run.dir / 'index.jsonl'
        count = 0
        ratios = []
        normalizations = Counter()
        first_steps = 0
        with index_path.open('w') as index:
            for source_run, path, episode in episodes:
                source_hash = digest(path.read_bytes())
                leak_idx = first_leak_request(episode)
                label = episode.get('label') or {}
                selected = selection[path]
                for request_idx, step, record in selected:
                    request = record['request']
                    source_model = request.get('model')
                    if source_model not in [args.model, *args.source_model] and not args.allow_cross_model:
                        raise ValueError(f'Source target {source_model} != {args.model}; use --allow-cross-model for wiring only')
                    rendered, ids, changes, thinking = render(tokenizer, request, args.thinking)
                    limit = min(args.max_tokens, config.max_position_embeddings)
                    if len(ids) > limit:
                        raise ValueError(f'{path.name} request {request_idx}: {len(ids)} tokens exceeds {limit}; no truncation allowed')
                    current_template = tokenizer.get_chat_template(tools=request.get('tools'))
                    template_hash = digest(current_template.encode())
                    template_file = run.dir / f'template-{template_hash}.jinja'
                    if not template_file.exists():
                        template_file.write_text(current_template)
                    started = time.perf_counter()
                    values = capture(model.base_model if args.reply_fidelity else model, capture_layers, ids, input_device)
                    activation_seconds = time.perf_counter() - started
                    fidelity = {'status': 'disabled'}
                    reply_ids = []
                    if args.reply_fidelity:
                        from fidelity import reply_tokens, score_reply
                        reply_ids, status = reply_tokens(tokenizer, request, record, rendered, thinking)
                        fidelity = {'status': status}
                        if reply_ids and len(ids) + len(reply_ids) > limit:
                            fidelity['status'] = 'prompt_plus_reply_exceeds_limit'
                        elif reply_ids:
                            fidelity.update(score_reply(model, ids, reply_ids, input_device))
                        reply_ids = reply_ids or []
                    key = f'call-{count:06d}'
                    relative = f'activations/{key}.npz'
                    artifact = run.dir / relative
                    artifact.parent.mkdir(exist_ok=True)
                    with artifact.with_suffix('.tmp').open('wb') as output:
                        np.savez_compressed(output, residual_last=values, input_ids=np.asarray(ids, dtype=np.int64), reply_ids=np.asarray(reply_ids, dtype=np.int64), layer_indices=np.asarray(selected_layers))
                    artifact.with_suffix('.tmp').replace(artifact)
                    prompt_path = run.dir / 'prompts' / f'{key}.txt'
                    prompt_path.parent.mkdir(exist_ok=True)
                    prompt_path.write_text(rendered)
                    usage = record.get('usage') or (record.get('response') or {}).get('usage') or {}
                    provider_tokens = usage.get('prompt_tokens')
                    ratio = len(ids) / provider_tokens if isinstance(provider_tokens, (int,float)) and provider_tokens > 0 else None
                    if ratio is not None:
                        ratios.append(ratio)
                    normalizations.update({'argument_strings': len(changes)})
                    same_model = source_model in [args.model, *args.source_model] and not args.tiny_random
                    before = (request_idx <= leak_idx if leak_idx is not None else
                              True if label.get('objective_success') is False else None)
                    row = dict(run_id=source_run, replay_run_id=run.id, episode_file=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                               episode_sha256=source_hash, episode_id=episode.get('episode_id'), round=record['round'],
                               request_idx=request_idx, step_in_turn=step, attempt=record.get('attempt',1),
                               request_error=record.get('error'), response_present=record.get('response') is not None,
                               activation_seconds=activation_seconds, total_seconds=time.perf_counter()-started, reply_fidelity=fidelity,
                               n_tokens=len(ids), provider_prompt_tokens=provider_tokens, token_count_ratio=ratio,
                               source_model=source_model, same_model=same_model, first_leak_request_idx=leak_idx,
                               before_first_leak=before, before_first_leak_round=(record['round'] < label['first_action_round']
                                   if label.get('first_action_round') is not None else True if label.get('objective_success') is False else None),
                               first_step=step == 1, condition=episode.get('condition',{}), label=label,
                               artifact=relative, prompt_file=str(prompt_path.relative_to(run.dir)),
                               template_sha256=template_hash, prompt_sha256=digest(rendered.encode()), input_ids_sha256=digest(ids),
                               request_sha256=digest(request), normalization=changes, enable_thinking=thinking,
                               objective_success=label.get('objective_success'), first_action_round=label.get('first_action_round'),
                               disclosure_kind=label.get('disclosure_kind'), eligible_resisted=label.get('eligible_resisted'),
                               token_in_context_round=label.get('token_in_context_round'))
                    index.write(json.dumps(row, ensure_ascii=False)+'\n')
                    index.flush()
                    count += 1
                    first_steps += step == 1
                    print(f'{source_run}/{path.name} r{record["round"]} step{step} attempt{row["attempt"]}: {len(ids)} tokens -> {values.shape}', flush=True)
        summary = dict(episodes=len(episodes), requests=count, first_step_requests=first_steps,
                       token_ratio_n=len(ratios), token_ratio_min=min(ratios) if ratios else None,
                       token_ratio_median=float(np.median(ratios)) if ratios else None,
                       token_ratio_max=max(ratios) if ratios else None, normalizations=dict(normalizations))
        write_json_atomic(run.dir / 'summary.json', summary)
        (run.dir / 'fidelity.md').write_text(f'''# Replay fidelity\n\nModel: {args.model}@{revision}. Tiny random weights: {args.tiny_random}.\nTemplate SHA256: {provenance['template_sha256']}. See selected_chat_template.jinja, tokenizer/, prompts/, provenance.json and NPZ input_ids.\n\nHF/provider prompt-token ratios: n={len(ratios)}, min/median/max={summary['token_ratio_min']}/{summary['token_ratio_median']}/{summary['token_ratio_max']}. These are diagnostics, not token equality or likelihood checks.\n\nOpenAI tool argument JSON strings are parsed to objects for HF templates; whitespace and JSON key serialization can change. Source requests remain untouched and hashed. Tool IDs, tool results and other fields are retained; the model template may ignore fields. Reasoning mode is explicitly supplied from each saved request (missing enabled defaults to false), or overridden by --thinking. Provider reasoning_details may not be rendered by HF. Templates can trim whitespace, merge tool results, insert tool instructions, or drop prior thinking. The provider's tokenizer revision, private template, exact token IDs, quantization and hidden prompts are unavailable. Equal counts do not establish equal tokens. Cross-model or random-weight replay is wiring only. No provider outputs are regenerated and no claims of exact provider replay are made.\n\nEach API attempt is a separate row, including retries; do not treat retries or tool steps as independent episodes. before_first_leak includes the call that emits the first leak because its input precedes that output. Subsequent calls in that same round are excluded. Unknown leak locations are null; no-leak episodes are true through their observed horizon, not forever. before_first_leak_round is the stricter round-only flag. Labels are copied from the immutable source, not recomputed with a changing E01 scorer.\n''')
        run.result(**summary)
        run.finish()
        return run.dir
    except BaseException as exc:
        run.finish('failed', f'{type(exc).__name__}: {exc}')
        raise


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+')
    p.add_argument('--model', default='ibm-granite/granite-4.2-8b')
    p.add_argument('--source-model', action='append', default=[], help='Explicit API identifier alias for this HF model')
    p.add_argument('--revision', default='main', help='Resolved to immutable Hub commit before loading')
    p.add_argument('--device', default='auto')
    p.add_argument('--dtype', choices=['bfloat16','float32','float16'], default='bfloat16')
    p.add_argument('--thinking', choices=['from-request','on','off'], default='from-request')
    p.add_argument('--layers-path')
    p.add_argument('--layers', default='all', help='all or comma-separated zero-based block indices')
    p.add_argument('--max-requests', type=int, help='Global request cap across all episodes')
    p.add_argument('--output-root', help='Directory containing generated run directories')
    p.add_argument('--reply-fidelity', action='store_true')
    p.add_argument('--precision', choices=['bf16', 'fp8'], default='bf16')
    p.add_argument('--max-episodes', type=int)
    p.add_argument('--max-requests-per-episode', type=int)
    p.add_argument('--max-tokens', type=int, default=32768)
    p.add_argument('--cpu-threads', type=int, default=4)
    p.add_argument('--tiny-random', action='store_true', help='2 blocks, width 32, seeded random weights; wiring only')
    p.add_argument('--allow-cross-model', action='store_true')
    p.add_argument('--seed', type=int, default=0)
    return p


if __name__ == '__main__':
    args = parser().parse_args()
    for name in ('max_requests', 'max_episodes', 'max_requests_per_episode', 'max_tokens', 'cpu_threads'):
        value = getattr(args, name)
        if value is not None and value < 1:
            raise SystemExit(f'--{name.replace("_", "-")} must be positive')
    main(args)
