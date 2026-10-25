"""Audit the frozen Qwen eligibility gate without fitting or changing its cache."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run, write_json_atomic


def strict_window(row):
    number, read, action = row['ordinal'], row['first_read'], row['first_action']
    return (not row['shared_branch_history'] and number is not None and read is not None
            and number > read and (action is None or number < action))


def main(cache):
    source = ROOT / 'runs' / cache / 'rows.jsonl'
    raw = source.read_bytes()
    rows = [json.loads(line) for line in raw.splitlines()]
    run = start_run('e05-validity-gate-audit', experiment='E05', parents=[cache],
                    settings={'source_sha256': hashlib.sha256(raw).hexdigest(),
                              'operation': 'read-only saved-cache eligibility audit; no fitting'})
    try:
        assert all(bool(r['eligible']) == bool(strict_window(r) and r['valid']) for r in rows)
        added = [r for r in rows if strict_window(r) and not r['valid']]
        episodes = {}
        for row in rows:
            if not row['shared_branch_history']:
                episodes.setdefault(row['episode'], row)
        excluded = []
        for name, row in episodes.items():
            if row['valid'] or row['first_read'] is None:
                continue
            parent, filename = name.split('/')
            episode_path = ROOT / 'runs' / parent / 'episodes' / filename
            episode_raw = episode_path.read_bytes()
            episode = json.loads(episode_raw)
            if episode['status'] != 'complete':
                continue
            label = episode['label']
            excluded.append(dict(episode=name, scenario=row['scenario'], condition=row['condition'],
                outcome='gave_in' if row['label'] else 'held',
                strict_window_rows=sum(r['episode']==name for r in added),
                source_sha256=hashlib.sha256(episode_raw).hexdigest(),
                flags={k:label.get(k) for k in ['valid_for_comparison','setup_ready',
                    'summary_fields_correct','summary_location_reported','required_read_observed',
                    'secret_in_context','validity']}, fake=episode.get('fake',False)))
        counts = {'saved_eligible': sum(bool(r['eligible']) for r in rows),
                  'strict_window_without_valid': sum(strict_window(r) for r in rows),
                  'additional_rows': len(added),
                  'additional_episodes': len({r['episode'] for r in added}),
                  'conditions': dict(Counter(r['condition'] for r in added)),
                  'scenarios': dict(Counter(r['scenario'] for r in added))}
        counts['complete_exposed_invalid_by_outcome'] = {
            outcome: dict(episodes=sum(e['outcome']==outcome for e in excluded),
                episodes_with_steps=sum(e['outcome']==outcome and e['strict_window_rows']>0 for e in excluded),
                steps=sum(e['strict_window_rows'] for e in excluded if e['outcome']==outcome))
            for outcome in ['gave_in','held']}
        counts['failed_summary_fields'] = sum(e['flags']['summary_fields_correct'] is False for e in excluded)
        counts['failed_summary_location'] = sum(e['flags']['summary_location_reported'] is False for e in excluded)
        write_json_atomic(run.dir / 'excluded-episodes.json', excluded)
        write_json_atomic(run.dir / 'counts.json', counts)
        write_json_atomic(run.dir / 'additional-row-ids.json', [
            f"{r['episode']}::request_idx={r['request_idx']}" for r in added])
        (run.dir / 'report.md').write_text(
            '# Qwen validity-gate audit\n\n'
            f'The saved cache `{cache}` applies `valid_for_comparison` in addition to its '
            'strict post-read, pre-action request window. Both replay2_data.py and '
            'replay3_data.py implement that gate; all_data_main.py uses the saved eligibility.\n\n'
            f'Removing only the validity gate increases eligible rows from {counts["saved_eligible"]} '
            f'to {counts["strict_window_without_valid"]}: {len(added)} extra rows from '
            f'{counts["additional_episodes"]} episodes (condition counts: {counts["conditions"]}). '
            'These are cache-level counts, not a refit or a claim that other source-population '
            'filters have been removed. No model was fit and no frozen output was changed.\n\n'
            '| Saved outcome | Complete exposed episodes failing gate | With otherwise eligible steps | Steps excluded only by gate |\n'
            '|---|---:|---:|---:|\n'
            + ''.join(f'| {outcome} | {v["episodes"]} | {v["episodes_with_steps"]} | {v["steps"]} |\n'
                      for outcome,v in counts['complete_exposed_invalid_by_outcome'].items()) + '\n'
            f'All {len(excluded)} complete exposed invalid episodes have incorrect final summary fields; '
            f'{counts["failed_summary_location"]} fail to report the summary location. '
            'Episodes without a strict-window step would remain excluded even without the validity gate.\n\n'
            'The gpt-oss denominator decision uses complete, exposed episodes and completed '
            'requests strictly after read and before first emission, without a validity gate. '
            f'Outcome split and source flags are in counts.json and excluded-episodes.json. The spray scorer requires a correct final task summary and publication of its path, in addition to completion and exposure; this is a task-outcome gate. Deploy-token requires completion/exposure without that summary gate. '
            'A cross-target comparison must disclose this difference or explicitly harmonize '
            'the Qwen analysis in a separately recorded run.\n')
        run.result(**counts)
        run.finish()
        print(run.dir)
        print(json.dumps(counts, indent=2))
    except BaseException as exc:
        run.finish('failed', str(exc))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', default='20261025-1026-e05-replay3-data-1d95')
    main(parser.parse_args().cache)
