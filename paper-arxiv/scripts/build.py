#!/usr/bin/env python3
"""Build the paper and reject unresolved references, citations, and missing glyphs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

PAPER = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tex_environment(root=PAPER):
    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    local = sorted((root / '.tools/TinyTeX/bin').glob('*'))
    if local:
        env['PATH'] = str(local[0]) + os.pathsep + env.get('PATH', '')
    if not shutil.which('latexmk', path=env.get('PATH')):
        raise RuntimeError('Install TeX Live with latexmk and pdflatex, or add them to PATH.')
    return env


def local_inputs(root):
    inputs = set()
    for line in (root / 'main.fls').read_text().splitlines():
        if not line.startswith('INPUT '):
            continue
        path = Path(line[6:])
        path = (root / path).resolve() if not path.is_absolute() else path.resolve()
        if path.is_relative_to(root) and path.is_file():
            relative = path.relative_to(root)
            if relative.parts[0] not in {'.tools', '.build', 'dist'}:
                inputs.add(relative)
    return sorted(inputs)


def build(root=PAPER, env=None):
    root = root.resolve()
    env = env or tex_environment()
    snapshot = {str(p.relative_to(root)): sha(p) for p in root.rglob('*')
                if p.is_file() and p.suffix in {'.tex', '.bib', '.sty', '.bst', '.pdf', '.png'}
                and p.name != 'main.pdf'
                and not any(part.startswith('.') or part == 'dist' for part in p.relative_to(root).parts)}
    hashes = json.loads((root / 'template_hashes.json').read_text())
    for name, expected in hashes.items():
        if name.endswith(('.sty', '.bst')) and sha(root / name) != expected:
            raise RuntimeError(f'Template changed: {name}')
    subprocess.run(['latexmk', '-pdf', 'main.tex'], cwd=root, env=env, check=True)
    log = (root / 'main.log').read_text(errors='replace')
    fatal = [line for line in log.splitlines() if re.search(
        r'undefined|Missing character:|There were undefined|Citation .* undefined', line, re.I)]
    if fatal:
        raise RuntimeError('\n'.join(fatal))
    for name, before in snapshot.items():
        if sha(root / name) != before:
            raise RuntimeError(f'Source changed during build: {name}')
    if not (root / 'main.bbl').is_file():
        raise RuntimeError('Missing main.bbl; arXiv requires the generated bibliography.')
    inputs = {str(p): sha(root / p) for p in local_inputs(root)
              if p.suffix in {'.tex', '.bib', '.sty', '.bst', '.bbl', '.pdf', '.png', '.jpg'}}
    report = {
        'command': 'latexmk -pdf main.tex',
        'pdf_sha256': sha(root / 'main.pdf'), 'inputs': inputs,
        'source_changed_during_build': False,
        'undefined_references_or_citations': [],
        'overfull_boxes': [line for line in log.splitlines() if 'Overfull' in line],
        'latexmk_version': subprocess.check_output(['latexmk', '-v'], env=env, text=True).strip(),
    }
    (root / 'build_manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'inputs'}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=PAPER)
    args = parser.parse_args()
    build(args.root)
