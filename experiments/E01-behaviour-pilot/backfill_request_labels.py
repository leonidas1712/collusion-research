"""Add request indices without replacing existing outcome or semantic labels."""
import json
from collections import Counter
from pathlib import Path
from action_scenarios import FAMILIES, score_action
from hybrid_code_review import score_reciprocal_code_review
from request_labels import request_index_labels
from collusion.runs import start_run, write_json_atomic

ROOT = Path(__file__).resolve().parents[2]


def main():
    run = start_run('e01-request-index-backfill', experiment='E01',
                    settings={'method':'target_completed_requests_v1','api_calls':0})
    rows = []
    families = Counter()
    for path in sorted((ROOT/'runs').glob('*/episodes/episode-*.json')):
        if '.partial.' in path.name or '.attempt-' in path.name:
            continue
        meta_path = path.parent.parent/'meta.json'
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        if meta.get('experiment') != 'E01' and '-e01-' not in path.parent.parent.name:
            continue
        episode = json.loads(path.read_text())
        if episode.get('status') != 'complete':
            continue
        family = episode.get('scenario_spec', {}).get('metadata', {}).get('scenario_family', 'legacy')
        original = episode.get('label')
        label = dict(original) if isinstance(original, dict) else {'legacy_label':original}
        evidence = (score_action(episode) if family in FAMILIES else
                    score_reciprocal_code_review(episode) if family == 'reciprocal-code-review' else label)
        additions = request_index_labels(episode, evidence)
        label.update(additions)
        episode['label'] = label
        write_json_atomic(path, episode)
        saved = json.loads(path.read_text())['label']
        if isinstance(original, dict):
            assert all(saved[k] == v for k, v in original.items() if k not in additions)
        else:
            assert saved['legacy_label'] == original
        rows.append({'episode':str(path.relative_to(ROOT)), 'family':family, **additions})
        families[family] += 1
    write_json_atomic(run.dir/'labels.json', rows)
    summary = {'episodes':len(rows), 'families':dict(families),
               'with_action_request':sum(r['first_action_target_request'] is not None for r in rows),
               'with_read_request':sum(r['first_token_read_request'] is not None for r in rows),
               'existing_labels_preserved':True, 'api_calls':0}
    write_json_atomic(run.dir/'summary.json', summary)
    run.result(**summary)
    run.finish()
    print(json.dumps(summary,indent=2))

if __name__ == '__main__':
    main()
