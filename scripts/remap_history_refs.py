"""Dry-run or apply unambiguous commit-map substitutions to tracked UTF-8 text.

Run only in the filtered release clone. This tool does not rewrite history,
commit, or push. Non-commit hexadecimal hashes are never guessed or changed.
"""
import argparse
import collections
import json
import hashlib
from pathlib import Path
import re
import subprocess

TOKEN = re.compile(r'(?<![A-Za-z0-9])[0-9a-fA-F]{7,40}(?![A-Za-z0-9])')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--commit-map', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    root = args.repo.resolve()
    pairs = [line.split() for line in args.commit_map.read_text().splitlines()[1:] if line.strip()]
    mapping = dict(pairs)
    prefix = collections.defaultdict(set)
    for old in mapping:
        for n in range(7, 41):
            prefix[old[:n]].add(old)
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    # Preserve any tracked file whose exact bytes are SHA-256-referenced elsewhere.
    # This includes source code pinned by a frozen plan, not just JSON records.
    contents = {}
    referenced_hashes = set()
    for rel in filter(None, tracked):
        path = root / rel
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            contents[rel] = data
            referenced_hashes.update(re.findall(rb'(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])', data))
    referenced_hashes = {value.decode().lower() for value in referenced_hashes}
    preserved = []
    for rel, data in contents.items():
        digest = hashlib.sha256(data).hexdigest()
        if (digest in referenced_hashes or Path(rel).name.startswith('frozen_')
                or rel.startswith('docs/history/')):
            preserved.append(dict(path=rel, sha256=digest,
                                  reason='referenced SHA-256, frozen record, or history provenance'))
    preserve_paths = {item['path'] for item in preserved}
    changes = []; issues = []; unresolved = collections.defaultdict(list); validated = set()
    for rel in filter(None, tracked):
        if rel in preserve_paths:
            continue
        path = root / rel
        if path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        if b'\0' in data:
            continue
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            continue
        replacements = []

        def replace(match):
            value = match.group(); token = value.lower(); candidates = prefix.get(token, set())
            if not candidates:
                if len(unresolved[token]) < 3:
                    unresolved[token].append(rel)
                return value
            if len(candidates) != 1:
                issues.append(dict(path=rel, token=value, reason='ambiguous old prefix'))
                return value
            old = next(iter(candidates)); new = mapping[old]
            if new == '0' * 40:
                issues.append(dict(path=rel, token=value, reason='deleted commit has no mapped identity'))
                return value
            # Use full new hashes: no abbreviation ambiguity in the rewritten graph.
            if new not in validated:
                subprocess.run(['git', 'cat-file', '-e', new + '^{commit}'], cwd=root, check=True)
                validated.add(new)
            if value != new:
                replacements.append(dict(old=value, new=new))
            return new

        updated = TOKEN.sub(replace, text)
        if updated != text:
            changes.append(dict(path=rel, count=len(replacements), replacements=replacements))
            if args.apply:
                path.write_bytes(updated.encode('utf-8'))
    # Unmapped strings can be external commits, model revisions, run IDs or content hashes.
    # Report them for review instead of silently treating all hexadecimal strings as commits.
    unresolved_report = []
    tokens = sorted(unresolved)
    checked = subprocess.run(['git', 'cat-file', '--batch-check'], cwd=root,
                             input='\n'.join(tokens)+'\n', text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True).stdout.splitlines()
    for token, result in zip(tokens, checked):
        if result.endswith((' missing', ' ambiguous')):
            unresolved_report.append(dict(token=token, paths=unresolved[token]))
    report = dict(applied=args.apply, commit_map=str(args.commit_map),
                  changed_files=len(changes), replacements=sum(c['count'] for c in changes),
                  validated_mapped_commits=len(validated), issues=issues,
                  changes=changes, preserved=preserved, unmapped_nonresolving_hex=unresolved_report,
                  scope='Only known commit-map keys or unique prefixes are substituted. Unmapped hashes require contextual classification.')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['changes','preserved','unmapped_nonresolving_hex']}, indent=2))
    print('Byte-preserved files:', len(preserved))
    print('Unmapped nonresolving hex strings:',len(unresolved_report))
    if issues:
        raise SystemExit('STOP: ambiguous or deleted commit references need review')


if __name__ == '__main__':
    main()
