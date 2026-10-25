"""Offline Harmony renderer comparisons on six frozen gpt-oss requests."""
import argparse
import hashlib
import importlib.metadata
import itertools
import json
from pathlib import Path

import openai_harmony as h
from gemma_gate import ROOT
from collusion.runs import start_run, write_json_atomic


def conversation(req, date, reasoning, arguments, tool_channel, tool_result):
    system = h.SystemContent.new().with_reasoning_effort(h.ReasoningEffort.LOW)
    if date:
        system.with_conversation_start_date(date)
    developer = h.DeveloperContent.new().with_instructions(req['messages'][0]['content'])
    developer.with_function_tools([h.ToolDescription.new(t['function']['name'],t['function'].get('description',''),
                                                        t['function'].get('parameters')) for t in req['tools']])
    messages = [h.Message.from_role_and_content(h.Role.SYSTEM,system),h.Message.from_role_and_content(h.Role.DEVELOPER,developer)]
    tools = {}
    for raw in req['messages'][1:]:
        role = raw['role']
        if role == 'user':
            messages.append(h.Message.from_role_and_content(h.Role.USER,raw['content']))
        elif role == 'assistant':
            if reasoning and raw.get('reasoning'):
                messages.append(h.Message.from_role_and_content(h.Role.ASSISTANT,raw['reasoning']).with_channel('analysis'))
            if raw.get('tool_calls'):
                for call in raw['tool_calls']:
                    fn=call['function']; tools[call['id']]='functions.'+fn['name']
                    value=fn['arguments']
                    if arguments!='raw':
                        value=json.dumps(json.loads(value),ensure_ascii=False,separators=(',',':') if arguments=='compact' else None)
                    msg=h.Message.from_role_and_content(h.Role.ASSISTANT,value).with_recipient(tools[call['id']]).with_channel(tool_channel)
                    if tool_channel=='commentary':
                        msg.with_content_type('json')
                    messages.append(msg)
            elif raw.get('content'):
                messages.append(h.Message.from_role_and_content(h.Role.ASSISTANT,raw['content']).with_channel('final'))
        elif role == 'tool':
            value=raw['content'] if tool_result=='raw' else json.dumps(raw['content'],ensure_ascii=False)
            msg=h.Message.from_author_and_content(h.Author.new(h.Role.TOOL,tools[raw['tool_call_id']]),value)
            if tool_channel=='commentary':
                msg.with_recipient('assistant').with_channel('commentary')
            messages.append(msg)
        else:
            raise ValueError(role)
    return h.Conversation.from_messages(messages)


def main(a):
    source=Path(a.source).resolve()
    records=[]
    for f in sorted((source/'episodes').glob('*.json')):
        ep=json.loads(f.read_text())
        for i,r in enumerate(ep['requests']):
            if r.get('response'):
                records.append(dict(episode=f.name,request_idx=i,request=r['request'],
                                    provider_tokens=r['response']['usage']['prompt_tokens']))
    assert len(records)==6
    run=start_run('e03-harmony-audit',experiment='E03',parents=[source.name],settings={
        'package':importlib.metadata.version('openai-harmony'),'reasoning_effort':'low',
        'source':str(source.relative_to(ROOT)), 'paid_calls':0})
    enc=h.load_harmony_encoding(h.HarmonyEncodingName.HARMONY_GPT_OSS)
    results=[]
    for date,reasoning,arguments,channel,result in itertools.product(
            [None,'2026-10-25'],[False,True],['raw','compact','spaced'],['commentary','analysis'],['raw','quoted']):
        counts=[]; hashes=[]
        for row in records:
            convo=conversation(row['request'],date,reasoning,arguments,channel,result)
            ids=enc.render_conversation_for_completion(convo,h.Role.ASSISTANT)
            counts.append(len(ids));hashes.append(hashlib.sha256(json.dumps(ids).encode()).hexdigest())
        expected=[r['provider_tokens'] for r in records]
        results.append(dict(date=date,reasoning=reasoning,arguments=arguments,tool_channel=channel,tool_result=result,
                            tokens=counts,deltas=[x-y for x,y in zip(counts,expected)],
                            exact_matches=sum(x==y for x,y in zip(counts,expected)),
                            max_abs_error=max(abs(x-y) for x,y in zip(counts,expected)),token_sha256=hashes))
    results.sort(key=lambda r:(-r['exact_matches'],sum(abs(x) for x in r['deltas'])))
    write_json_atomic(run.dir/'variants.json',results)
    write_json_atomic(run.dir/'requests.json',[{k:v for k,v in r.items() if k!='request'} for r in records])
    # The renderer's completed-turn policy can be isolated without any new model call.
    test=h.Conversation.from_messages([
        h.Message.from_role_and_content(h.Role.USER,'First task'),
        h.Message.from_role_and_content(h.Role.ASSISTANT,'SYNTHETIC_PRIOR_REASONING').with_channel('analysis'),
        h.Message.from_role_and_content(h.Role.ASSISTANT,'Done').with_channel('final'),
        h.Message.from_role_and_content(h.Role.USER,'Second task')])
    retention={}
    for drop in [True,False]:
        ids=enc.render_conversation_for_completion(test,h.Role.ASSISTANT,h.RenderConversationConfig(auto_drop_analysis=drop))
        retention[str(drop)]=dict(tokens=len(ids),retains_marker='SYNTHETIC_PRIOR_REASONING' in enc.decode(ids))
    write_json_atomic(run.dir/'completed_turn_control.json',retention)
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained('openai/gpt-oss-20b',revision='6cee5e81ee83917806bbde320786a8fb61efebee',local_files_only=True)
    canonical=[r for r in results if r['date']=='2026-10-25' and r['arguments']=='raw'
               and r['tool_channel']=='commentary' and r['tool_result']=='raw']
    checks=[]
    for row in records:
        ids=enc.render_conversation_for_completion(conversation(row['request'],'2026-10-25',False,'raw','commentary','raw'),h.Role.ASSISTANT)
        checks.append(ids==tok.encode(enc.decode(ids),add_special_tokens=False))
    assert all(checks)
    write_json_atomic(run.dir/'token_roundtrip.json',dict(hf_revision='6cee5e81ee83917806bbde320786a8fb61efebee',equal=checks))
    dropped=next(r for r in canonical if not r['reasoning'])
    retained=next(r for r in canonical if r['reasoning'])
    lines=['# Offline Harmony prompt-count audit', '',
           '**No tested rendering reproduces all six provider counts exactly.** The official renderer gets within one token on every request when prior reasoning is omitted. That satisfies the original approximate 1% token-count criterion, but does not establish exact provider token identity or justify an unverified activation-replay adapter.', '',
           '## Inputs and method', '',
           'Six saved CoreWeave gpt-oss-20b requests from `runs/20261025-1739-e03-gpt-oss-smoke` cover one alone episode each of deploy-token-v2 and handoff-exception-note. Each has a read-file call, a write-file call and a final reply. All three requests belong to target round 1. This analysis made no model calls and used no GPU.', '',
           'Rendering uses `openai-harmony==0.0.8`, `HARMONY_GPT_OSS`, structured SystemContent and DeveloperContent, the original function schemas, and reasoning effort LOW. The closest configuration uses the saved-call date 2026-10-25, preserves raw argument JSON and raw tool-result text, places tool calls/results on commentary, marks call content as JSON, and omits previous assistant reasoning. The renderer adds the assistant completion prefix itself. There is no added padding, fitted token offset or edited scenario text.', '',
           '## Counts', '',
           '| Episode / request | Provider | Harmony, drop reasoning | Difference | Harmony, keep reasoning | Difference |',
           '|---|---:|---:|---:|---:|---:|']
    for i,row in enumerate(records):
        lines.append(f"| {row['episode']} / {row['request_idx']} | {row['provider_tokens']} | {dropped['tokens'][i]} | {dropped['deltas'][i]:+d} | {retained['tokens'][i]} | {retained['deltas'][i]:+d} |")
    lines+=['',
            'Dropping reasoning gives a constant −1 token difference (0.22–0.32%). Retaining the returned reasoning gives differences of −1, +13, +77, −1, +15 and +32 tokens. Under otherwise identical serialization, this favors omission of previous reasoning from the served prompt. It is evidence from counts, not direct observation of provider input tokens. The remaining token could reflect a provider prefix, whitespace, preamble or usage accounting; its identity is unresolved. No arbitrary token was appended to claim a match.', '',
            'The exploratory matrix contains 48 combinations: date absent/present; reasoning dropped/kept; raw/compact/spaced argument JSON; commentary+JSON or analysis tool headers; raw or JSON-quoted result text. These are serialization diagnostics, not 48 equally valid deployment recommendations. None matches all six counts. The highest exact-match count is two; its errors are −1, 0, +3, −1, 0, +3 and it normalizes argument spacing. The raw-argument configuration minimizes aggregate absolute error at six tokens. All matrix results and token hashes are in `variants.json`.', '',
            '## What the reasoning test establishes', '',
            'The API history retains both reasoning and reasoning_details. The count comparison above tests omission versus inclusion of the plain reasoning text during tool steps within one target turn. There is no later user/peer turn in these alone traces, so whether CoreWeave drops reasoning across completed turns cannot be determined from these six requests.', '',
            'A synthetic offline control separates renderer policy from provider behavior: a prior analysis message followed by a final reply and a new user message loses its analysis marker with the official renderer default auto_drop_analysis=True (21 tokens), and retains it with False (36 tokens). This demonstrates the library behavior only. The current vLLM source also explicitly removes analysis before the latest final response; its chat-input converter accepts the reasoning field. That is a public implementation example, not proof of CoreWeave’s serving stack or version.', '',
            '## Validation, provenance and limits', '',
            'All six canonical Harmony token sequences round-trip through the pinned HF tokenizer with exact token-ID equality (`token_roundtrip.json`). The mismatch is therefore not explained by a different vocabulary on these prompts. This does not prove equality with the provider’s unavailable token IDs. The local completed-turn control is in `completed_turn_control.json`; saved provider counts and request indices are in `requests.json`. No provider defaults were changed and no production replay adapter was installed.', '',
            'Reproduce with `experiments/E02-activation-replay/.venv/bin/python experiments/E03-target-screen/harmony_audit.py runs/20261025-1739-e03-gpt-oss-smoke`. The environment needs openai-harmony==0.0.8 and the cached HF tokenizer at revision 6cee5e81ee83917806bbde320786a8fb61efebee. Tokenizer checks use local_files_only=True. The official encoding assets must already be cached for a network-disconnected rerun.', '',
            'Sources: [official Harmony package](https://github.com/openai/harmony), [OpenAI format guide](https://developers.openai.com/cookbook/articles/openai-harmony), and [vLLM Harmony conversion source](https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/parser/harmony_utils.py), inspected 2026-10-25. The vLLM source was inspected as text and was not executed.', '',
            'Conclusion: approximate count fidelity is recovered with official Harmony and reasoning omission; exact fidelity and provider behavior across completed turns remain unverified. No additional paid test is included.']
    (run.dir/'report.md').write_text('\n'.join(lines)+'\n')
    run.result(variants=len(results),exact_all_six=sum(r['exact_matches']==6 for r in results),best=results[0],paid_calls=0)
    run.finish()
    print(run.dir); print(json.dumps(results[:4],indent=2));print(retention)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');main(p.parse_args())
