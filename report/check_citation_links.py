"""Verify DOCX internal-link targets survive PDF export at the right locations."""
import argparse
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from pypdf import PdfReader

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--stem', type=Path, default=ROOT/'report/build/paper')
args = parser.parse_args()
stem = args.stem


def text(node):
    return ''.join(x.text or '' for x in node.iter(W+'t'))


def normalise(value):
    return ''.join(c.lower() for c in unicodedata.normalize('NFKD', value) if c.isalnum())


with ZipFile(stem.with_suffix('.docx')) as archive:
    doc = E.fromstring(archive.read('word/document.xml'))
marks = {n.get(W+'name'): n for n in doc.iter(W+'bookmarkStart')}
expected = []
for link in doc.iter(W+'hyperlink'):
    anchor = link.get(W+'anchor')
    if anchor:
        assert anchor in marks, f'Missing DOCX bookmark: {anchor}'
        paragraph = marks[anchor]
        while paragraph.tag != W+'p':
            paragraph = paragraph.getparent()
        expected.append({'link': text(link), 'target': text(paragraph), 'anchor': anchor})

pdf = PdfReader(stem.with_suffix('.pdf'))
page_ids = {p.indirect_reference.idnum: i+1 for i, p in enumerate(pdf.pages)}
actual = []
for index, page in enumerate(pdf.pages, 1):
    for annotation in page.get('/Annots', []):
        annotation = annotation.get_object()
        dest = annotation.get('/Dest')
        if dest:
            actual.append({'source_page': index, 'target_page': page_ids[dest[0].idnum],
                           'top': float(dest[3])})

bbox = E.fromstring(subprocess.check_output([
    'pdftotext', '-bbox-layout', str(stem.with_suffix('.pdf')), '-']))
ns = {'x': 'http://www.w3.org/1999/xhtml'}
pages = []
for page in bbox.findall('.//x:page', ns):
    stream, locations = '', []
    for word in page.findall('.//x:word', ns):
        token = normalise(word.text or '')
        stream += token
        locations.extend([float(word.get('yMin'))] * len(token))
    pages.append((stream, locations, float(page.get('height'))))

# Compare destinations directly: wrapped links create multiple PDF annotations,
# while repeated citations can share a destination on the same page.
for item in expected:
    prefix = normalise(' '.join(item['target'].split()[:12]))
    candidates = []
    for annotation in actual:
        stream, locations, height = pages[annotation['target_page']-1]
        for match in re.finditer(re.escape(prefix), stream):
            delta = abs(height - annotation['top'] - locations[match.start()])
            if delta < 20:
                candidates.append((delta, annotation))
    assert candidates, f'No PDF link reaches expected target: {item}'
    delta, annotation = min(candidates, key=lambda candidate: candidate[0])
    item.update(annotation)
    item['target_y_delta_pt'] = round(delta, 2)

out = stem.parent/'template-check/citation-links.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(expected, indent=2)+'\n')
print(f'{len(expected)} DOCX internal links have PDF destinations within 20 pt of their target; '
      f'{len(set(x["anchor"] for x in expected))} distinct targets; '
      f'max error {max(x["target_y_delta_pt"] for x in expected):.2f} pt.')
