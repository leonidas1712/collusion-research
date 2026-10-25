"""Frozen gpt-oss episode and step eligibility; independent of the Qwen cache."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'E01-behaviour-pilot'))
from leak_scenarios import _args, _fields as leak_fields
from scenarios import _fields as deploy_fields, STATUS


def episode_eligibility(episode):
    spec=episode['scenario_spec']; metadata=spec['metadata']; label=episode.get('label') or {}
    deploy=metadata.get('scenario_family')=='deploy-token'
    summary_path=STATUS if deploy else metadata['summary_path']
    parse=deploy_fields if deploy else leak_fields
    expected={key:str(value) for key,value in metadata['expected_task_values'].items()}
    final=spec['files'].get(summary_path,''); evidence=[]
    for index,event in enumerate(episode.get('tool_log',[])):
        if event.get('actor')!='target' or event.get('name')!='write_file':continue
        args=_args(event); result=event.get('result')
        if (args.get('path')!=summary_path or not isinstance(result,dict) or 'error' in result
                or result.get('written')!=summary_path or not isinstance(args.get('content'),str)):continue
        final=args['content']; fields=parse(final)
        evidence.append(dict(tool_log_index=index,round=event.get('round'),call_id=event.get('call_id'),
                             correct=all(fields.get(k)==v for k,v in expected.items())))
    complete=episode.get('status')=='complete'
    exposed=bool(label.get('token_in_context') or label.get('secret_in_context') or label.get('required_read_observed'))
    ever=any(e['correct'] for e in evidence)
    final_fields=parse(final)
    return dict(complete=complete,exposed=exposed,ever_correct_summary=ever,
                final_summary_correct=all(final_fields.get(k)==v for k,v in expected.items()),
                original_valid_for_comparison=label.get('valid_for_comparison'),
                episode_eligible=bool(complete and exposed and ever and not episode.get('fake',False)),
                summary_write_evidence=evidence)


def eligible_step(flags, completed_ordinal, first_read_ordinal, first_public_emission_ordinal):
    """Strict post-read/pre-public-emission window; pre-ask rows remain available."""
    return bool(flags['episode_eligible'] and completed_ordinal is not None
                and first_read_ordinal is not None and completed_ordinal>first_read_ordinal
                and (first_public_emission_ordinal is None or completed_ordinal<first_public_emission_ordinal))


def request_boundaries(episode):
    from request_labels import completed_target_requests, request_index_labels, _protected_value, _strings
    indices=request_index_labels(episode,episode.get('label'))
    contains,_=_protected_value(episode)
    first_reasoning=None
    for ordinal,(_,record) in enumerate(completed_target_requests(episode),1):
        choices=record['response'].get('choices') or []
        message=(choices[0].get('message') or {}) if choices else {}
        texts=list(_strings(message.get('reasoning')))+list(_strings(message.get('reasoning_details')))
        if any(contains(text) for text in texts):
            first_reasoning=ordinal
            break
    public=indices['first_action_target_request']
    present=[value for value in [public,first_reasoning] if value is not None]
    return dict(first_read_ordinal=indices['first_token_read_request'],
                first_public_emission_ordinal=public,first_reasoning_mention_ordinal=first_reasoning,
                first_inclusive_emission_ordinal=min(present) if present else None)
