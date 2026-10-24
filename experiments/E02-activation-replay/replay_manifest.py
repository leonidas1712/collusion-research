"""Select exact request inputs, independent of where source episodes are mounted."""
import json
from pathlib import Path


def load_manifest(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if not rows:
        raise ValueError('Empty request manifest')
    seen = set()
    for row in rows:
        run_id = row['run_id']
        source = Path(row['episode_file'])
        if Path(run_id).name != run_id or run_id in ('.', '..') or source.parts != ('runs', run_id, 'episodes', source.name):
            raise ValueError('Invalid manifest source path')
        key = (run_id, source.name, row['request_idx'])
        if key in seen:
            raise ValueError('Duplicate manifest request')
        seen.add(key)
    return rows


def select_manifest(path, episodes, tokenizer, thinking):
    from replay import digest, render, request_rows
    sources = {(run_id, source.name): (source, episode) for run_id, source, episode in episodes}
    if len(sources) != len(episodes):
        raise ValueError('Ambiguous source run/episode identity')
    selection = {source: [] for _, source, _ in episodes}
    metadata = {}
    hashes = {}
    for row in load_manifest(path):
        key = (row['run_id'], Path(row['episode_file']).name)
        if key not in sources:
            raise ValueError(f'Manifest episode missing: {key}')
        source, episode = sources[key]
        if source not in hashes:
            hashes[source] = digest(source.read_bytes())
        if row['episode_sha256'] != hashes[source]:
            raise ValueError(f'Manifest episode hash mismatch: {key}')
        candidates = {idx: (idx, step, record) for idx, step, record in request_rows(episode)}
        if row['request_idx'] not in candidates:
            raise ValueError('Manifest request is not a target call')
        call = candidates[row['request_idx']]
        rendered, ids, _, _ = render(tokenizer, call[2]['request'], thinking)
        actual = dict(request_sha256=digest(call[2]['request']), prompt_sha256=digest(rendered.encode()),
                      input_ids_sha256=digest(ids), n_tokens=len(ids), round=call[2]['round'], step_in_turn=call[1])
        for field, value in actual.items():
            if row[field] != value:
                raise ValueError(f'Manifest {field} mismatch: {key} request {row["request_idx"]}')
        selection[source].append(call)
        metadata[(source, call[0])] = row
    return selection, metadata
