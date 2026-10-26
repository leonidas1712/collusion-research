#!/usr/bin/env python3
"""Package the recorded TeX inputs and compile them in a clean directory."""
import argparse
import json
import re
from pathlib import Path
import shutil
import subprocess
import tarfile
from build import PAPER, build, local_inputs, sha, tex_environment


def package(output, root=PAPER):
    root = root.resolve()
    env = tex_environment()
    build(root, env)
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f'Use a new output directory: {output}')
    source = output / 'source'
    clean = output / 'clean-build'
    source.mkdir(parents=True)
    inputs = [p for p in local_inputs(root)
              if p.suffix in {'.tex', '.bib', '.sty', '.bst', '.bbl', '.pdf', '.png', '.jpg'}
              and p.name != 'main.pdf']
    aux = (root / 'main.aux').read_text()
    for command, suffix in [('bibdata', '.bib'), ('bibstyle', '.bst')]:
        for group in re.findall(r'\\' + command + r'\{([^}]+)\}', aux):
            inputs.extend(Path(name.strip() + suffix) for name in group.split(','))
    inputs.extend(map(Path, ['latexmkrc', 'template_hashes.json']))
    for relative in sorted(set(inputs)):
        if not (root / relative).resolve().is_relative_to(root):
            raise RuntimeError(f'External package dependency: {relative}')
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)
    if not (source / 'main.bbl').is_file():
        raise RuntimeError('Package lacks main.bbl.')
    shutil.copytree(source, clean)
    result = build(clean, env)
    # PDF metadata can differ; compare extracted text rather than binary PDF hashes.
    def text(path):
        return subprocess.check_output(['pdftotext', '-layout', str(path), '-'])
    if text(root / 'main.pdf') != text(clean / 'main.pdf'):
        raise RuntimeError('Clean package build text differs from the local build.')
    archive = output / 'arxiv-source.tar.gz'
    with tarfile.open(archive, 'w:gz') as bundle:
        for path in sorted(source.rglob('*')):
            if path.is_file():
                bundle.add(path, arcname=str(path.relative_to(source)))
    manifest = {
        'archive_sha256': sha(archive),
        'files': {str(p.relative_to(source)): sha(p) for p in sorted(source.rglob('*')) if p.is_file()},
        'local_pdf_sha256': sha(root / 'main.pdf'),
        'packaged_pdf_sha256': result['pdf_sha256'],
        'clean_build_text_matches': True,
        'viewer_check': 'pending: both PDFs require a real-viewer check',
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='New directory for source archive, manifest, and clean build.')
    parser.add_argument('--root', type=Path, default=PAPER)
    args = parser.parse_args()
    package(args.output, args.root)
