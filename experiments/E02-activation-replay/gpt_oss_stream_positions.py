"""Map frozen Harmony inputs to new incoming messages and generated token roles."""
import time
from gpt_oss_replay import assistant_messages,harmony_encoding

ROLE={'incoming':0,'reasoning':1,'answer':2,'tool':3,'last_prompt':4}

def annotated_messages(record,date,mode):
    import openai_harmony as h
    req=record['request'];effort=(req.get('reasoning') or req.get('extra_body',{}).get('reasoning') or {}).get('effort','low')
    system=h.SystemContent.new().with_reasoning_effort(h.ReasoningEffort[effort.upper()]).with_conversation_start_date(date)
    developer=h.DeveloperContent.new().with_instructions(req['messages'][0]['content'])
    developer.with_function_tools([h.ToolDescription.new(t['function']['name'],t['function'].get('description',''),t['function'].get('parameters')) for t in req.get('tools',[])])
    messages=[h.Message.from_role_and_content(h.Role.SYSTEM,system),h.Message.from_role_and_content(h.Role.DEVELOPER,developer)];mapping=[None,0];names={}
    last_user=max((i for i,m in enumerate(req['messages']) if m['role']=='user'),default=-1)
    for j,raw in enumerate(req['messages'][1:],1):
        if raw['role']=='user':new=[h.Message.from_role_and_content(h.Role.USER,raw['content'])]
        elif raw['role']=='assistant':
            new=assistant_messages(raw,h,mode=='keep_all' or (mode=='current_turn' and j>last_user))
            for call in raw.get('tool_calls') or []:names[call['id']]='functions.'+call['function']['name']
        elif raw['role']=='tool':new=[h.Message.from_author_and_content(h.Author.new(h.Role.TOOL,names[raw['tool_call_id']]),raw['content']).with_recipient('assistant').with_channel('commentary')]
        else:raise ValueError(raw['role'])
        messages.extend(new);mapping.extend([j]*len(new))
    return messages,mapping

def positions(row,episode):
    import openai_harmony as h
    enc=harmony_encoding();record=episode['requests'][row['request_idx']]
    previous=[r for r in episode['requests'][:row['request_idx']] if r.get('actor')=='target']
    old=previous[-1]['request']['messages'] if previous else []
    current=record['request']['messages']
    assert current[:len(old)]==old,('Non-append raw message history',row['row_id'])
    incoming={i for i in range(len(old),len(current)) if current[i]['role'] in ['user','tool']}
    date=time.strftime('%Y-%m-%d',time.gmtime(record['response']['created'])) if record.get('response',{}).get('created') else episode['started_at'][:10]
    messages,mapping=annotated_messages(record,date,row['history_reasoning_mode'])
    config=h.RenderConversationConfig(auto_drop_analysis=False)
    rendered=enc.render_conversation_for_completion(h.Conversation.from_messages(messages),h.Role.ASSISTANT,config)
    assert rendered==row['prompt_ids'],('Prompt rendering mismatch',row['row_id'])
    chunks=[enc.render(m,h.RenderOptions(conversation_has_function_tools=True)) for m in messages]
    flat=[t for c in chunks for t in c]
    assert rendered[:len(flat)]==flat,('Prompt message decomposition mismatch',row['row_id'])
    tags={};incoming_kinds={};offset=0
    for chunk,raw_idx in zip(chunks,mapping):
        if raw_idx in incoming:
            for p in range(offset,offset+len(chunk)):
                tags[p]=ROLE['incoming'];incoming_kinds[p]=current[raw_idx]['role']
        offset+=len(chunk)
    raw=record['response']['choices'][0]['message'];reply_messages=assistant_messages(raw,h)
    full=row['prompt_ids']+row['reply_ids'];reply_chunks=[enc.render(m,h.RenderOptions(conversation_has_function_tools=True)) for m in reply_messages]
    offset=len(full)-sum(map(len,reply_chunks));boundary=row.get('first_value_token_position')
    end=boundary if boundary is not None else len(full)
    for m,chunk in zip(reply_messages,reply_chunks):
        role=ROLE['reasoning'] if m.channel=='analysis' else ROLE['tool'] if m.recipient else ROLE['answer']
        for p in range(max(offset,len(rendered)),min(offset+len(chunk),end)):tags[p]=role
        offset+=len(chunk)
    assert offset==len(full)
    assert all(p in tags for p in range(len(rendered),end))
    tags[len(rendered)-1]=ROLE['last_prompt']
    indices=sorted(tags)
    public=row.get('first_public_value_token_position')
    return {'capture_positions':indices,'capture_roles':[tags[p] for p in indices],
        'incoming_kind':['peer' if incoming_kinds.get(p)=='user' else 'tool_result' if p in incoming_kinds else '' for p in indices],
        'offset_to_first_secret':[p-boundary if boundary is not None else None for p in indices],
        'offset_to_first_public_secret':[p-public if public is not None else None for p in indices],
        'incoming_raw_message_indices':sorted(incoming),'previous_target_request_count':len(previous)}
