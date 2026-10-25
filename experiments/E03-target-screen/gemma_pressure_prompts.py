"""Compose existing scenario prompts with the seven fixed tactic templates."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'experiments/E01-behaviour-pilot')]
from collusion.runs import start_run, write_json_atomic
from peer_tactics import SOURCE, filled_tactic, filled_tactic_from_slots
from scale_up import scale_up_scenario

FAMILIES = ('deploy-token-v2', 'handoff-exception-note', 'dispatch-integration-code',
            'service-capacity-figure')
TACTICS = tuple(f'T{i}' for i in range(1, 8))


def scenario(family, condition, family_id, *, reviewed=False):
    base = scale_up_scenario('deploy-token-v2' if family == 'deploy-token-v2' else 'deploy-token',
                             'consequence', condition, str(family_id),
                             spray_row=None if family == 'deploy-token-v2' else family)
    slots = base.metadata.get('tactic_slots')
    active = tuple(t for t in TACTICS if t not in base.metadata.get('skip_tactics', ()))
    parts = [filled_tactic_from_slots(slots, t, condition,
                                      skip_tactics=base.metadata.get('skip_tactics', ()))
             if slots is not None else filled_tactic(base.metadata['scenario_family'], t, condition)
             for t in active]
    metadata = {**base.metadata, 'tactic_id': '+'.join(active),
                'tactic_ids': list(active), 'tactic_source': str(SOURCE.relative_to(ROOT)),
                'tactic_source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                'base_recruiter_system_sha256': hashlib.sha256(base.recruiter_system.encode()).hexdigest()}
    return replace(base, recruiter_system=base.recruiter_system + '\n\n' + '\n\n'.join(parts),
                   metadata=metadata, scenario_version=base.scenario_version + '-all-tactics-1',
                   recruiter_approved=base.recruiter_approved and reviewed)


def main():
    run = start_run('e03-gemma-pressure-prompt-plan', experiment='E03',
                    settings={'tactics': list(TACTICS), 'families': list(FAMILIES),
                              'live_calls': False, 'tactic_source': str(SOURCE.relative_to(ROOT))})
    try:
        records = []
        for family in FAMILIES:
            for condition in ('recruiting', 'control'):
                s = scenario(family, condition, 96001)
                assert s.recruiter_system.count('Approach to try:') == (6 if family == 'dispatch-integration-code' else 7)
                assert not any('{' + key + '}' in s.recruiter_system for key in
                               ('target_name', 'forbidden_ask', 'in_scope_ask', 'shared_task', 'offer'))
                filename = f'{family}-{condition}.txt'
                (run.dir / filename).write_text(s.recruiter_system + '\n')
                records.append({'family': family, 'condition': condition, 'file': filename,
                                'prompt_sha256': hashlib.sha256(s.recruiter_system.encode()).hexdigest(),
                                'metadata': s.metadata})
        write_json_atomic(run.dir / 'prompts.json', records)
        run.result(prompts=len(records), live_calls=0)
        run.finish()
        print('PROMPT_PLAN', run.id)
    except BaseException as exc:
        run.finish('failed', str(exc))
        raise


if __name__ == '__main__':
    main()
