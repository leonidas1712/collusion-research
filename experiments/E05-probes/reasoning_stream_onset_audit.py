"""Audit reply lengths and alarm onset from frozen scores; no fitting or inference."""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def audit():
    run = ROOT / 'runs/20261026-0526-e05-reasoning-stream'
    rows = json.loads((ROOT / 'runs/20261026-0522-e05-reasoning-stream-data/replies.json').read_text())
    cohort = [r for r in rows if r['condition'] == 'recruiting' and r['stream_window'] == 'post_ask']
    lengths = {}
    for name, selected in [('all', cohort), ('leaking', [r for r in cohort if r['y_immediate']])]:
        for nonempty in [False, True]:
            vals = [r['reasoning_tokens'] for r in selected if not nonempty or r['reasoning_tokens']]
            lengths[f'{name}_{"nonempty" if nonempty else "including_empty"}'] = dict(n=len(vals), median=float(np.median(vals)), quartiles=np.quantile(vals, [.25, .75]).tolist())
    alarms, seeds, seen = [], {}, set()
    files = sorted((run / 'immediate/all/loso').glob('s*-f*/fit.json'))
    assert len(files) == 18
    for path in files:
        fit = json.loads(path.read_text()); seed = fit['plan']['seed']
        count = seeds.setdefault(seed, Counter())
        with np.load(path.parent / 'scores.npz') as z:
            for j, idx in enumerate(z['indices']):
                r = rows[int(idx)]
                if r['stream_window'] != 'post_ask':
                    continue
                assert (seed, int(idx)) not in seen
                seen.add((seed, int(idx)))
                values = z['token_scores'][z['offsets'][j]:z['offsets'][j+1]]
                assert len(values) == r['reasoning_tokens']
                assert np.isclose(values.max(), z['max_scores'][j])
                if not r['y_immediate']:
                    continue
                count['leaking_replies'] += 1
                hit = np.flatnonzero(values > fit['threshold'])
                if len(hit):
                    first = int(hit[0]) + 1
                    count['alarmed'] += 1
                    count['first_token'] += int(first == 1)
                    alarms.append(dict(seed=seed, fold=fit['plan']['fold'], row_id=r['row_id'],
                                       first_token_1based=first, reasoning_tokens=len(values),
                                       fraction=first / len(values)))
    matched = {}
    base = ROOT / 'runs/20261026-0822-e05-expanded-stream'
    expanded = json.loads((ROOT / 'runs/20261026-0813-e05-expanded-stream-data/replies.json').read_text())
    stored = json.loads((base / 'stopped_grid_interim.json').read_text())['metrics']
    for stream in ['reasoning', 'incoming']:
        key = f'{stream}/full/immediate/both/pooled'; count = Counter(); ids = set()
        fits = sorted((base / key).glob('s42-f*/fit.json'))
        assert len(fits) == 5
        for path in fits:
            fit = json.loads(path.read_text())
            with np.load(path.parent / 'scores.npz') as z:
                for idx, score in zip(z['indices'], z['ema_max']):
                    assert int(idx) not in ids
                    ids.add(int(idx)); r = expanded[int(idx)]
                    if not r['ever_public']:
                        count['held_replies'] += 1
                        count['held_replies_alarmed'] += int(score > fit['thresholds']['ema'])
        rate = count['held_replies_alarmed'] / count['held_replies']
        assert np.isclose(rate, stored[key]['held_reply_alarm'])
        matched[stream] = dict(count, rate=rate)
    total = sum(r['first_token_1based'] == 1 for r in alarms)
    return dict(lengths=lengths, by_seed=seeds, first_token_alarms=total, alarmed_reply_seed_observations=len(alarms),
                first_token_fraction=total / len(alarms), crossing_fraction_median=float(np.median([r['fraction'] for r in alarms])),
                matched_four_layer_seed42_pooled=matched, alarms=alarms)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'runs/20261026-0526-e05-reasoning-stream/onset_audit.json')
    args = parser.parse_args()
    result = audit()
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'alarms'}, indent=2))


if __name__ == '__main__':
    main()
