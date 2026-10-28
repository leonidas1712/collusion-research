"""Register the count of Qwen3-32B test calls made before the first read of the protected file."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUN = 'runs/20261028-1044-e05-pre-read-calls'


def main():
    reg = json.loads((HERE/'numbers.yaml').read_text())
    data = json.loads((ROOT/RUN/'results.json').read_text())
    for macro, key, fmt in [('qwenPreReadCalls', 'pre_read_calls', 'integer'),
                            ('qwenPreReadShare', 'pre_read_share', 'percent'),
                            ('qwenPreReadEpisodes', 'episodes', 'integer'),
                            ('qwenPreReadRoundOne', 'first_read_round_one', 'integer')]:
        reg['numbers'][macro] = dict(value=data[key], macro=macro,
            dataset='Qwen3-32B test recruiting episodes (89 episodes, 1,825 scored calls)',
            evaluation='Target calls before the first scored call; saved episodes only',
            status='verified', run=RUN, format=fmt, decimals=0,
            source=dict(file=RUN+'/results.json', value_path=[key]))
    (HERE/'numbers.yaml').write_text(json.dumps(reg, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__': main()
