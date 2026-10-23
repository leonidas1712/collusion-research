"""Prepare only complete episode JSON, with no repository credentials or unrelated runs."""
import hashlib
import json
from pathlib import Path


def pack_runs(root, run_ids):
    result = {}
    for run_id in run_ids:
        if Path(run_id).name != run_id or run_id in ('.', '..'):
            raise ValueError('Use bare run IDs, not paths')
        files = {}
        for path in sorted((Path(root) / 'runs' / run_id / 'episodes').glob('*.json')):
            if '.partial.' in path.name or '.attempt-' in path.name:
                continue
            raw = path.read_text()
            episode = json.loads(raw)
            if episode.get('status') == 'complete' and not episode.get('fake'):
                files[path.name] = raw
        if not files:
            raise ValueError(f'No complete real episodes in {run_id}')
        result[run_id] = files
    return result


def manifest(payload):
    return {run_id: {name: hashlib.sha256(raw.encode()).hexdigest() for name, raw in files.items()}
            for run_id, files in payload.items()}
