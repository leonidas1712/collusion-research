"""Register E12 cascade results (saved scores; thresholds chosen on fresh episodes, descriptive)."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUN = 'runs/20261027-2007-e12-cascade'
DETECTORS = [('probe_alone', 'ProbeAlone', 'Probe alone, stricter threshold'),
             ('jev_lenient', 'JevLenient', 'Probe (lenient) then Jev'),
             ('jev_grid', 'JevGrid', 'Probe (grid) then Jev'),
             ('bow_lenient', 'BowLenient', 'Probe (lenient) then bag-of-words'),
             ('bow_grid', 'BowGrid', 'Probe (grid) then bag-of-words')]
TARGETS = [('5%', 'Five'), ('10%', 'Ten')]


def main():
    reg = json.loads((HERE/'numbers.yaml').read_text())
    data = json.loads((ROOT/RUN/'results.json').read_text())

    def add(macro, path, ci=None, fmt='percent', decimals=0):
        value = data
        for key in path: value = value[key]
        source = dict(file=RUN+'/results.json', value_path=path)
        entry = dict(value=value, macro=macro, dataset='Qwen fresh test episodes (38 leaking, 51 refusing)',
                     evaluation='E12 cascade; saved scores; per-episode halt at first call all stages flag; thresholds chosen on the same fresh episodes (descriptive); 1000 episode-bootstrap draws, thresholds re-chosen',
                     status='exploratory', run=RUN, format=fmt, decimals=decimals, source=source)
        if ci:
            bounds = data
            for key in ci: bounds = bounds[key]
            entry['ci'] = bounds
            source['ci_path'] = ci
        reg['numbers'][macro] = entry

    for t, tn in TARGETS:
        for d, dn, _ in DETECTORS:
            base = ['targets', t, d]
            add('cascade'+dn+tn, base+['leaking_rate'], base+['leaking_rate_ci95'])
            add('cascade'+dn+tn+'Caught', base+['leaking_caught'], fmt='integer')
            if d != 'probe_alone':
                add('cascade'+dn+tn+'Gap', base+['gap_episodes'], fmt='signed', decimals=0)
    reg.setdefault('aliases', {})['cascadeBestFive'] = 'cascadeBowGridFive'
    rows = []
    for d, dn, label in DETECTORS:
        row = [label]
        for _, tn in TARGETS:
            m = 'cascade'+dn+tn
            cell = '\\'+m+'Caught{}/38 (\\'+m+'{}) \\'+m+'CI{}'
            if d != 'probe_alone':
                cell += '; \\'+m+'Gap{}'
            row.append(cell)
        rows.append(row)
    reg['tables']['cascade'] = dict(
        columns=r'@{}>{\raggedright\arraybackslash}p{0.28\linewidth}>{\raggedright\arraybackslash}p{0.32\linewidth}>{\raggedright\arraybackslash}p{0.32\linewidth}@{}',
        header=['Detector', r'$\le$5\% of refusing episodes halted', r'$\le$10\% of refusing episodes halted'], rows=rows)
    (HERE/'numbers.yaml').write_text(json.dumps(reg, indent=2)+'\n')


if __name__ == '__main__': main()
