"""Register saved-data episode recounts and current-cohort table fragments."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUN = 'runs/20261027-0034-e05-arxiv-development-episode-checks'


def main():
    registry = json.loads((HERE / 'numbers.yaml').read_text())
    summary = json.loads((ROOT / RUN / 'summary.json').read_text())

    def add(macro, path, fmt='integer', decimals=0):
        value = summary
        for part in path:
            value = value[part]
        assert value is not None
        registry['numbers'][macro] = dict(
            value=value, macro=macro, dataset='Current development episodes' if path[0] == 'development' else 'Qwen fresh refusing episodes',
            evaluation='Saved-log and saved-judge recount; no model calls or refits',
            status='verified', run=RUN, format=fmt, decimals=decimals,
            source=dict(file=RUN + '/summary.json', value_path=path))
        return {'key': macro}

    routes, kinds, authority = [], [], []
    for model, prefix, display in [('Qwen', 'qwen', 'Qwen'), ('GPT', 'gptoss', 'gpt-oss')]:
        base = ['development', model]
        data = summary['development'][model]
        n = add(prefix + 'CurrentEpisodes', base + ['episodes'])
        leaks = add(prefix + 'CurrentEmittingEpisodes', base + ['leaking_episodes'])
        routes.append([display, 'All episodes', n])
        routes.append([display, 'Any public emission', leaks])
        for route, title in [('final_reply', 'Final reply'), ('send_message', 'send\\_message arguments'), ('write_file', 'write\\_file-type arguments')]:
            if route in data['routes']:
                routes.append([display, title, add(prefix + 'CurrentRoute' + ''.join(x.title() for x in route.split('_')), base + ['routes', route])])
        for kind in ['deliberate', 'accidental', 'uncertain', 'unavailable']:
            if kind in data['kind_counts']:
                kinds.append([display, kind.title(), add(prefix + 'CurrentIntent' + kind.title(), base + ['kind_counts', kind]), leaks])
        for q, title, short in [('q1_operator_authority', 'Operator', 'Operator'), ('q2_receiver_authority', 'Recipient', 'Recipient')]:
            for arm, lab in [('with', 'Present'), ('without', 'Absent')]:
                stem = prefix + 'CurrentAuthority' + short + arm.title()
                path = base + ['authority', q]
                count = add(stem + 'Episodes', path + [arm + '_claim'])
                positive = add(stem + 'Leaks', path + ['leaks_' + arm + '_claim'])
                rate = add(stem + 'Rate', path + ['rate_' + arm + '_claim'], 'percent', 1) if data['authority'][q]['rate_' + arm + '_claim'] is not None else '---'
                authority.append([display, title, lab, positive, count, rate])
    registry['tables']['episode_routes'] = dict(columns='llr', header=['Target', 'First public-emission route', 'Episodes'], rows=routes)
    registry['tables']['episode_intent'] = dict(columns='llrr', header=['Target', 'Saved intent label', 'Episodes', 'Emitting episodes'], rows=kinds)
    registry['tables']['episode_authority'] = dict(columns='lllrrr', header=['Target', 'Claim', 'Claim present?', 'Emitting', 'Episodes', 'Rate'], rows=authority)
    add('qwenFreshMedianRefusingCalls', ['qwen_fresh_refusing', 'median_calls'])
    add('qwenEpisodeAlarmIndependent', ['qwen_fresh_refusing', 'independent_illustration_nominal_5pct'], 'percent')
    registry['numbers']['qwen_leak_rate_dev']['decimals'] = 0
    registry['numbers']['qwen_fresh_input_refusing_rate']['decimals'] = 1
    # The consuming table supplies the positive sign outside these macros.
    for prefix in ['qwen', 'gptoss']:
        for view in ['Full', 'Latest']:
            registry['numbers'][prefix + 'ProbeMinusText' + view]['format'] = 'decimal'
    (HERE / 'numbers.yaml').write_text(json.dumps(registry, indent=2) + '\n')


if __name__ == '__main__':
    main()
