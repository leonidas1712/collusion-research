"""Restore run archives from a local directory or a published release URL.

Example (local archive verification):
  scripts/fetch_run_data.sh --source private/release_archives --destination /tmp/run-data-check
For a release, supply --source https://.../releases/download/TAG and the published
--manifest-sha256. Existing differing files are never overwritten.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import urllib.request


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Local asset folder or HTTPS release asset base URL')
    parser.add_argument('--destination', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest-sha256', help='Required for remote downloads; hash of manifest.json')
    args = parser.parse_args()
    remote = args.source.startswith('https://')
    if '://' in args.source and not remote:
        parser.error('Only HTTPS downloads or local paths are supported')
    if remote and not args.manifest_sha256:
        parser.error('Remote downloads require --manifest-sha256 from trusted release metadata')
    root = args.destination.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='run-data-') as temporary:
        cache = Path(temporary)

        def fetch(name):
            if Path(name).name != name:
                raise ValueError('Asset names must be plain filenames')
            if not remote:
                return Path(args.source) / name
            dest = cache / name
            with urllib.request.urlopen(args.source.rstrip('/') + '/' + name) as src, dest.open('wb') as out:
                shutil.copyfileobj(src, out)
            return dest

        manifest_path = fetch('manifest.json')
        if args.manifest_sha256 and sha256(manifest_path) != args.manifest_sha256:
            raise ValueError('Manifest checksum mismatch')
        manifest = json.loads(manifest_path.read_text())
        if manifest['schema_version'] != 1:
            raise ValueError('Unsupported manifest version')
        count = 0
        seen = set()
        for asset in manifest['assets']:
            archive = fetch(asset['name'])
            if archive.stat().st_size != asset['size'] or sha256(archive) != asset['sha256']:
                raise ValueError('Archive checksum mismatch: ' + asset['name'])
            expected = {r['path']: r for r in asset['files']}
            if len(expected) != len(asset['files']):
                raise ValueError('Duplicate manifest paths')
            received = set()
            with tarfile.open(archive, 'r:gz') as tf:
                for member in tf:
                    rel = PurePosixPath(member.name)
                    if (not member.isfile() or rel.is_absolute() or '..' in rel.parts
                            or not rel.parts or rel.parts[0] != 'runs' or member.name not in expected
                            or member.name in seen):
                        raise ValueError('Unexpected or unsafe archive member: ' + member.name)
                    record = expected[member.name]
                    if member.size != record['size']:
                        raise ValueError('Member size mismatch')
                    target = root.joinpath(*rel.parts)
                    for parent in [target, *target.parents]:
                        if parent == root:
                            break
                        if parent.is_symlink():
                            raise ValueError('Refusing symlink destination')
                    if not target.resolve().is_relative_to(root):
                        raise ValueError('Destination escapes root')
                    if target.exists():
                        if sha256(target) != record['sha256']:
                            raise ValueError('Existing file differs: ' + member.name)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        fd, tmpname = tempfile.mkstemp(dir=target.parent, prefix='.restore-')
                        try:
                            with os.fdopen(fd, 'wb') as out, tf.extractfile(member) as src:
                                shutil.copyfileobj(src, out)
                            if sha256(tmpname) != record['sha256']:
                                raise ValueError('Member checksum mismatch: ' + member.name)
                            os.replace(tmpname, target)
                        finally:
                            Path(tmpname).unlink(missing_ok=True)
                    received.add(member.name)
                    seen.add(member.name)
                    count += 1
            if received != set(expected):
                raise ValueError('Archive is missing manifest members')
            if remote:
                archive.unlink()
            print(f"Verified {asset['name']}: {len(received)} files", flush=True)
        print(f'Restored and verified {count} files in {root}', flush=True)


if __name__ == '__main__':
    main()
