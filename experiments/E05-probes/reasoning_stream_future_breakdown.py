"""Describe the calls between strict-one-ahead scored replies and public emission."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from reasoning_stream_data import ROOT, harmony_encoding
from reasoning_stream_labels import add_horizon_labels
from reasoning_stream_report import stream_metrics
from collusion.runs import start_run, write_json_atomic

sys.path.insert(0, str(ROOT / 'experiments/E01-behaviour-pilot'))
from request_labels import completed_target_requests


def quantiles(values):
    return {'n': len(values), 'q25_median_q75': np.quantile(values, [.25, .5, .75]).tolist(),
            'min': min(values), 'max': max(values)} if values else {'n': 0}


def main(out):
    rows = add_horizon_labels(json.loads((ROOT / 'runs/20261026-0522-e05-reasoning-stream-data/replies.json').read_text()))
    lookup = {r['row_id']: i for i, r in enumerate(rows)}
    source = out / 'probe_scores.csv'; source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    groups = {}
    with source.open() as f:
        for record in csv.DictReader(f):
            if record['variant'] == 'h1' and record['mask'] == 'all' and record['window'] == 'post_ask':
                i = lookup[record['row_id']]
                if not rows[i]['y_immediate']:
                    groups.setdefault(record['analysis'], {}).setdefault(int(record['seed']), {})[i] = record
    ids = sorted(groups['loso'][42]); positives = [i for i in ids if rows[i]['y_h1']]
    assert len(ids) == 1874 and len(positives) == 116
    enc = harmony_encoding(); details = []
    for i in positives:
        r = rows[i]; episode = json.loads(Path(r['source_path']).read_text())
        current = episode['requests'][r['request_idx']]
        next_index, future = completed_target_requests(episode)[r['first_action'] - 1]
        assert r['eligible_replies_until_public'] == 1 and next_index > r['request_idx']
        before = current['request']['messages']; after = future['request']['messages']
        assert after[:len(before)] == before
        added = after[len(before):]
        incoming = [m for m in added if m['role'] in ['tool', 'user']]
        assert all(isinstance(m.get('content'), str) for m in incoming)
        tool_names = [(t.get('function') or {}).get('name') for t in
                      current['response']['choices'][0]['message'].get('tool_calls') or []]
        values = episode['scenario_spec']['honeypots']
        role_tokens = {role: sum(len(enc.encode(m['content'], allowed_special='all'))
                                for m in incoming if m['role'] == role) for role in ['tool', 'user']}
        a, b = current['response'].get('created'), future['response'].get('created')
        gap = b - a if a is not None and b is not None else None
        assert gap is None or gap >= 0
        details.append({'row_id': r['row_id'], 'episode': r['episode'], 'family': r['family'],
                        'scenario': r['scenario'], 'round': r['round'], 'action_round': future['round'],
                        'round_gap': future['round'] - r['round'], 'current_request_idx': r['request_idx'],
                        'action_request_idx': next_index, 'created_timestamp_delta_seconds': gap,
                        'intervening_message_roles': dict(Counter(m['role'] for m in added)),
                        'current_reply_tool_names': tool_names,
                        'incoming_contains_protected_value': any(v in m['content'] for v in values for m in incoming),
                        'incoming_tool_content_tokens': role_tokens['tool'], 'incoming_peer_content_tokens': role_tokens['user'],
                        'incoming_content_tokens': sum(role_tokens.values()), 'exact_message_prefix': True})
    run = start_run('e05-stream-future-breakdown', experiment='E05', parents=[out.name],
                    settings={'request': 'Aboard1914', 'no_refit': True, 'source_sha256': source_hash})
    try:
        round_counts = dict(Counter(str(d['round_gap']) for d in details))
        summaries = {}
        for label, subset in [('all', details), ('same_round', [d for d in details if d['round_gap'] == 0]),
                              ('next_round', [d for d in details if d['round_gap'] == 1])]:
            summaries[label] = {'positive_replies': len(subset), 'episodes': len({d['episode'] for d in subset}),
                **{key: quantiles([d[key] for d in subset if d[key] is not None]) for key in
                   ['created_timestamp_delta_seconds', 'incoming_tool_content_tokens', 'incoming_peer_content_tokens', 'incoming_content_tokens']}}
        metrics = {}
        same = {lookup[d['row_id']] for d in details if d['round_gap'] == 0}
        chosen = np.array([i for i in ids if not rows[i]['y_h1'] or i in same], dtype=int)
        y = np.array([rows[i]['y_h1'] for i in chosen])
        for mode, seeds in groups.items():
            assert set(seeds) == {42, 43, 44} and all(set(seed) == set(ids) for seed in seeds.values())
            folds = np.array([[int(seeds[s][i]['fold']) for i in chosen] for s in [42, 43, 44]])
            for method, column in [('token_max', 'max_score'), ('token_mean', 'mean_score'), ('frozen_last_prompt_A', 'frozen_last_prompt_score')]:
                scores = np.array([[float(seeds[s][i][column]) for i in chosen] for s in [42, 43, 44]])
                metrics['same_round/' + mode + '/' + method] = stream_metrics(rows, chosen, y, scores, folds, 1000)[0]
        payload = {'source_sha256': source_hash, 'round_gap_counts': round_counts, 'summaries': summaries,
                   'same_round_current_tool_names': dict(Counter(n for d in details if d['round_gap'] == 0 for n in d['current_reply_tool_names'])),
                   'same_round_incoming_contains_value': sum(d['round_gap'] == 0 and d['incoming_contains_protected_value'] for d in details),
                   'same_round_metrics': metrics, 'negative_bank': len(ids) - len(positives),
                   'next_round_auc': 'Not reported: only three positive replies/episodes; too sparse for a reliable separate estimate',
                   'timing_caveat': 'Provider response.created timestamps, integer seconds. Not logged response-end to next-request-start latency; may use provider clocks.',
                   'token_count_definition': 'Harmony-tokenized content of newly appended user/tool messages; excludes current assistant reply and Harmony headers',
                   'details': details}
        lines = ['# What “one reply ahead” means', '',
            f"Of the 116 strict-one-ahead positive replies, {round_counts.get('0', 0)} precede another target call in the same round, "
            f"and {round_counts.get('1', 0)} precede a call in the next round. All 116 next prompts extend the earlier message list exactly. "
            'The intervening incoming item is a tool result in the same-round cases and a new user/peer message in the next-round cases.', '',
            f"Among the 113 same-round cases, the current reply calls `read_file` 109 times and the malformed name "
            f"`read_file<|channel|>commentary` four times. Incoming tool content contains the protected value in "
            f"{payload['same_round_incoming_contains_value']} cases. These episodes were already exposed under the "
            'post-read eligibility rule. This concentration on a read-file step is a potential alternative explanation '
            'for the one-step ranking; the analysis does not isolate a general advance-warning signal.', '',
            '| Positive subset | Replies | Provider timestamp delta, median [IQR], seconds | New incoming content tokens, median [IQR] |',
            '|---|---:|---|---|']
        for label, summary in summaries.items():
            def fmt(key):
                q = summary[key].get('q25_median_q75')
                return f'{q[1]:g} [{q[0]:g}, {q[2]:g}]' if q else 'Missing'
            lines.append(f"| {label} | {summary['positive_replies']} | {fmt('created_timestamp_delta_seconds')} | {fmt('incoming_content_tokens')} |")
        lines += ['', 'The timing column is a difference between provider `response.created` timestamps with one-second resolution. '
                  'The harness does not record response-end and next-request-start times here. It is therefore **not a measured warning duration** '
                  'or the gap available to an intervention. Token counts include only the newly appended incoming message bodies, '
                  'tokenized with the same Harmony encoding; they exclude the current assistant reply and framing tokens.', '',
                  '## Same-round positive subset', '',
                  'These estimates retain all 1,758 original strict-future negative replies and the 113 same-round positives, '
                  'dropping the three next-round positives. This is an outcome-conditioned descriptive subset, not a new deployable endpoint. '
                  'Within-scenario × round AUROC and 1,000-family-bootstrap intervals average seeds 42/43/44.', '',
                  '| Split | MAX | Mean | Frozen last-prompt A |', '|---|---|---|---|']
        for mode in ['pooled', 'loso']:
            cells = []
            for method in ['token_max', 'token_mean', 'frozen_last_prompt_A']:
                value = metrics[f'same_round/{mode}/{method}']; ci = value['within_round_ci95']
                cells.append(f"{value['within_round_auc']:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]")
            lines.append('| ' + mode + ' | ' + ' | '.join(cells) + ' |')
        lines += ['', 'A separate next-round AUROC is not reported: three positive replies are too few for a reliable estimate. '
                  'The result is overwhelmingly a warning one tool step ahead within a round; it does not establish warning before another peer turn. '
                  'The saved models were trained on inclusive horizons, with no refit for this check. The last-prompt model has a different training label.', '',
                  f"Script: `experiments/E05-probes/reasoning_stream_future_breakdown.py`. Source: `{source}` (SHA256 `{source_hash}`). "
                  f"Audit run: `{run.dir}`. No API/GPU spend."]
        for folder in [out, run.dir]:
            write_json_atomic(folder / 'strict_future_breakdown.json', payload)
            (folder / 'strict_future_breakdown.md').write_text('\n'.join(lines) + '\n')
        run.result(round_gap_counts=round_counts); run.finish()
    except BaseException as exc:
        run.finish('failed', str(exc)); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    main(parser.parse_args().out)
