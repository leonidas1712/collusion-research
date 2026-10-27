"""Register the bag-of-words classifier's per-call AUROC on the Qwen test calls and its paired difference from the probe."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
RUN = 'runs/20261028-0228-e12-bow-test-auroc'
DATASET = 'Qwen fresh test episodes'
EVALUATION = ('bag-of-words (latest message) fit on all 2976 development calls as in E12, scored once on the '
              '1825 test calls/38 positives; within scenario and round; 1000 family-bootstrap draws')


def main():
    reg = json.loads((HERE/'numbers.yaml').read_text())
    def add(key, macro, value_path, ci_path, fmt=None):
        source = dict(file=RUN+'/metrics.json', value_path=value_path, ci_path=ci_path)
        data = json.loads((HERE.parent/RUN/'metrics.json').read_text())
        def get(path):
            v = data
            for k in path: v = v[k]
            return v
        entry = dict(value=get(value_path), ci=get(ci_path), macro=macro, dataset=DATASET, evaluation=EVALUATION,
                     status='out_of_sample', run=RUN, source=source)
        if fmt: entry.update(fmt)
        reg['numbers'][key] = entry
    add('qwen_fresh_percall_bow_auroc', 'qwenFreshCallBow', ['bow', 'within_round_auc'], ['bow', 'within_round_ci95'])
    add('qwen_fresh_percall_probe_minus_bow', 'qwenFreshCallProbeMinusBow', ['paired_difference', 'value'],
        ['paired_difference', 'ci95'], dict(format='signed', decimals=2))
    (HERE/'numbers.yaml').write_text(json.dumps(reg, indent=2)+'\n')


if __name__ == '__main__': main()
