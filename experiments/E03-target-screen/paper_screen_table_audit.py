"""Verify screening-table counts, source hashes and the historical manuscript table.

Run from the repository root with Python 3.11 or later:
    python experiments/E03-target-screen/paper_screen_table_audit.py --check

This audits the saved eligibility ledger; it does not rerun semantic judges or
relabel episodes. The manuscript revision is fixed because its table was later
edited for presentation.
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'runs/20261026-0157-e03-paper-screen-table-audit'
FIELDS = ['attempted', 'n', 'gave_in', 'channel_give_ins', 'complete',
          'incomplete', 'never_read', 'invalid_complete', 'held']
KEYS = ('factor', 'level', 'cohort', 'model', 'scenario', 'condition')


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def audit(figures, paper_text, episode_root):
    manifest = json.loads((figures / 'appendix_g_manifest.json').read_text())
    for path, expected in manifest['sources'].items():
        actual = hashlib.sha256((episode_root / path).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Source hash mismatch: {path}')

    records = read_csv(figures / 'appendix_g_episodes.csv')
    groups = defaultdict(list)
    identities = set()
    for record in records:
        assert record['sha256'] == manifest['sources'][record['path']]
        identity = tuple(record[k] for k in ('factor', 'level', 'cohort', 'path'))
        assert identity not in identities, identity
        identities.add(identity)
        groups[tuple(record[k] for k in KEYS)].append(record)
    assert {r['path'] for r in records} == set(manifest['sources'])

    cells = read_csv(figures / 'appendix_g_coverage.csv')
    seen = set()
    for cell in cells:
        key = tuple(cell[k] for k in KEYS)
        assert key not in seen, key
        seen.add(key)
        group = groups.get(key, [])
        valid = [r for r in group if r['valid'] == 'True']
        channel_available = bool(group and group[0]['channel_publication'] != '')
        counts = {
            'attempted': len(group), 'n': len(valid),
            'gave_in': sum(r['action'] == 'True' for r in valid),
            'channel_give_ins': sum(r['channel_publication'] == 'True' for r in valid)
                               if channel_available else None,
            'complete': sum(r['status'] == 'complete' for r in group),
            **{name: sum(r['category'] == name for r in group)
               for name in ('incomplete', 'never_read', 'invalid_complete', 'held')},
        }
        for field in FIELDS:
            expected = int(cell[field]) if cell[field] else None
            assert counts[field] == expected, (key, field, counts[field], expected)
        assert counts['n'] + counts['incomplete'] + counts['never_read'] + counts['invalid_complete'] == counts['attempted']
        assert counts['gave_in'] + counts['held'] == counts['n']
    assert set(groups) <= seen

    table_lines = [line for line in (figures / 'appendix_g_coverage.md').read_text().splitlines()
                   if line.startswith('|')]
    paper_lines = set(paper_text.splitlines())
    for line in table_lines:
        assert line in paper_lines, f'Manuscript table line missing: {line}'
    return {
        'source_episodes_hash_verified': len(manifest['sources']),
        'factor_records': len(records), 'cells_recomputed': len(cells),
        'paper_table_lines_matched': len(table_lines), 'counts_match': True,
        'fields_checked': FIELDS,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures', type=Path, default=ROOT / 'report/figures')
    parser.add_argument('--episode-root', type=Path, default=ROOT)
    paper_source = parser.add_mutually_exclusive_group()
    paper_source.add_argument('--paper', type=Path, default=RUN / 'manuscript_table.md',
                              help='Saved manuscript table or a full manuscript')
    paper_source.add_argument('--paper-revision', help='Read report/paper.md from this Git revision instead')
    parser.add_argument('--check', action='store_true', help='Compare the result with the saved audit summary')
    parser.add_argument('--reference', type=Path, default=RUN / 'summary.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    paper = subprocess.check_output(
        ['git', 'show', f'{args.paper_revision}:report/paper.md'], cwd=ROOT, text=True
    ) if args.paper_revision else args.paper.read_text()
    result = audit(args.figures, paper, args.episode_root)
    if args.check:
        assert result == json.loads(args.reference.read_text()), result
    rendered = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end='')


if __name__ == '__main__':
    main()
