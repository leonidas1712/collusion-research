"""Join saved first-public-emission judgments without changing labels or eligibility."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from collusion.runs import start_run, write_json_atomic


def main(args):
    plan = Path(args.plan).resolve()
    episodes = json.loads((plan/'episodes.json').read_text())
    lookup = {e['source_metadata']['episode_file']: e for e in episodes}
    judge = Path(args.judge).resolve()
    assert json.loads((judge/'meta.json').read_text())['status'] == 'finished'
    run = start_run('e05-gpt-oss-disclosure-kind-join', experiment='E05', parents=[plan.name, judge.name],
        settings={'no_paid_calls': True, 'label_scope': 'first public emission, which can precede channel publication',
                  'primary_labels_and_eligibility_unchanged': True})
    try:
        records = {}
        for path in sorted((judge/'judgments').glob('*.json')):
            value = json.loads(path.read_text())
            source = value['episode']
            episode = lookup[source]
            assert value['episode_sha256'] == episode['source_metadata']['episode_sha256']
            assert hashlib.sha256((ROOT/source).read_bytes()).hexdigest() == value['episode_sha256']
            assert source not in records
            kind = value['labels']['first_publication_kind']
            assert kind in ('deliberate', 'accidental', None)
            records[source] = dict(episode=episode['episode'], episode_sha256=value['episode_sha256'],
                channel_label=episode['label'], first_publication_kind=kind,
                first_public_route=value['first_public_route'], first_public_round=value['first_public_round'],
                first_channel_route=value['first_channel_route'], judgment_file=str(path.relative_to(ROOT)),
                judgment_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        expected = {e['source_metadata']['episode_file'] for e in episodes if e['first_public_emission_ordinal'] is not None}
        assert set(records) == expected
        ordered = sorted(records.values(), key=lambda r: r['episode'])
        summary = dict(episodes=len(episodes), judged_public_emission_episodes=len(ordered),
            kinds=dict(Counter(r['first_publication_kind'] or 'uncertain' for r in ordered)),
            channel_positive_kinds=dict(Counter(r['first_publication_kind'] or 'uncertain' for r in ordered if r['channel_label'])),
            hashes_verified=True, primary_labels_and_eligibility_unchanged=True)
        write_json_atomic(run.dir/'episode_kinds.json', ordered)
        write_json_atomic(run.dir/'summary.json', summary)
        (run.dir/'report.md').write_text('# Saved disclosure-kind metadata join\n\n'
            f"Matched all {len(ordered)} first-public-emission judgments to the 360-episode canonical manifest by path and SHA256. "
            'No API call, primary-label change or eligibility change was made.\n\n'
            'The judge describes the first public emission, usually a file write; it does not necessarily judge the later '
            'channel publication and does not establish internal intent. The activation cache leaves kind null; '
            'analyses needing this sensitivity must join episode_kinds.json on episode and verify episode_sha256. '
            'Episodes without a public emission are absent from the judgment table, not assigned an inferred kind. '
            'Two saved labels are null; the report calls these uncertain, matching the source judge report.\n\n'
            'Counts: '+json.dumps(summary['kinds'])+'. Channel-positive episode kinds: '+
            json.dumps(summary['channel_positive_kinds'])+'.\n')
        run.result(**summary)
        run.finish()
        print('KIND_JOIN', run.dir)
    except BaseException as exc:
        run.finish('failed', str(exc))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', required=True)
    parser.add_argument('--judge', required=True)
    main(parser.parse_args())
