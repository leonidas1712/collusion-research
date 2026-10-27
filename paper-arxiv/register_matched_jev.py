"""Register E13: Jev at the same share of refusing calls flagged as the probe.

Replaces the Jev rows at its own saved cutoff in tables.alarms and tables.episode_calibration,
so run it after register_supplemental.py, register_final_records.py and
register_episode_calibration.py.
"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUN = 'runs/20261028-0107-e13-matched-jev-d814'
DATASETS = dict(qwen_test='Qwen test episodes (38 leaking calls, 1,407 refusing-episode calls)',
                gptoss_dev='gpt-oss development episodes (121 leaking calls, 1,665 refusing-episode calls)')
FIELDS = [('Precision', 'precision'), ('LeakCalls', 'leaking_calls'), ('LeakEpisodes', 'leaking_episodes'),
          ('RefusingCalls', 'refusing_calls'), ('RefusingEpisodes', 'refusing_episodes')]


def main():
    reg = json.loads((HERE/'numbers.yaml').read_text())
    data = json.loads((ROOT/RUN/'results.json').read_text())

    def add(macro, path, ci=None, fmt='percent', decimals=0):
        value = data
        for key in path: value = value[key]
        source = dict(file=RUN+'/results.json', value_path=path)
        entry = dict(value=value, macro=macro, dataset=DATASETS[path[0]],
                     evaluation='E13; saved scores; probe at its saved control-call threshold; Jev at the lowest cut flagging no larger share of refusing-episode calls; 1000 episode-bootstrap draws, cut re-matched in each',
                     status='verified', run=RUN, format=fmt, decimals=decimals, source=source)
        if ci:
            bounds = data
            for key in ci: bounds = bounds[key]
            entry['ci'] = bounds
            source['ci_path'] = ci
        reg['numbers'][macro] = entry
        return {'key': macro}

    for split, p in [('qwen_test', 'qwen'), ('gptoss_dev', 'gptoss')]:
        add(p+'MatchedJevCaught', [split, 'jev_caught'], [split, 'jev_caught_ci'])
        add(p+'MatchedProbeCaught', [split, 'probe_caught'])
        add(p+'MatchedProbeRefusing', [split, 'probe_refusing'], decimals=1)
        add(p+'MatchedJevRefusing', [split, 'jev_refusing'], decimals=1)
        add(p+'MatchedJevCut', [split, 'jev_cut'], fmt='decimal', decimals=2)
    for n, key in [('JevCaughtCount', 'jev_caught_n'), ('ProbeCaughtCount', 'probe_caught_n'), ('LeakTotal', 'leaking_calls')]:
        add('qwenMatched'+n, ['qwen_test', key], fmt='integer')

    # Episode-calibration row: Jev at the matched cut, same columns as the other rows.
    row = ['Qwen Jev', 'Same share flagged']
    for name, key in FIELDS:
        m = 'qwenJevCalibrationMatched'+name
        add(m+'Numerator', ['qwen_test', 'table', key, 'numerator'], fmt='integer')
        add(m+'Denominator', ['qwen_test', 'table', key, 'denominator'], fmt='integer')
        row.append('\\'+m+'Numerator{}/\\'+m+'Denominator{}')
    row += ['---', '---']
    add('qwenJevCalibrationMatchedRefusingEpisodesRate', ['qwen_test', 'table', 'refusing_episodes', 'rate'])
    t = reg['tables']['episode_calibration']
    t['rows'] = [row if r[:2] == ['Qwen Jev', 'Original'] or r[:2] == row[:2] else r for r in t['rows']]

    # Alarm table: the Jev rows at its own cutoffs become one row at the probe's share flagged.
    alarm = ['Qwen test', 'Jev input', "Probe's share of refusing calls",
             {'key': 'qwenMatchedJevCaught'}, {'key': 'qwenMatchedJevRefusing'},
             {'key': 'qwenJevCalibrationMatchedRefusingEpisodesRate'}]
    t = reg['tables']['alarms']
    t['rows'] = [r for r in t['rows'] if r[1] != 'Jev input'] + [alarm]
    (HERE/'numbers.yaml').write_text(json.dumps(reg, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__': main()
