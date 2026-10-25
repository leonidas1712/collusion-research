"""Verify internal PDF citations against their DOCX reference targets."""
from pathlib import Path
from zipfile import ZipFile
import json,re,unicodedata
from lxml import etree as E
from pypdf import PdfReader
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
ROOT=Path(__file__).resolve().parents[1]
with ZipFile(ROOT/'report/build/paper.docx') as z:r=E.fromstring(z.read('word/document.xml'))
def txt(n):return ''.join(x.text or '' for x in n.iter(W+'t'))
def norm(s):return ''.join(c.lower() for c in unicodedata.normalize('NFKD',s) if c.isalnum())
marks={n.get(W+'name'):n for n in r.iter(W+'bookmarkStart')}
expected=[]
for h in r.iter(W+'hyperlink'):
 a=h.get(W+'anchor')
 if a:
  p=marks[a].getparent()
  expected.append({'citation':txt(h),'reference':txt(p),'anchor':a})
pdf=PdfReader(ROOT/'report/build/paper.pdf');ids={p.indirect_reference.idnum:i+1 for i,p in enumerate(pdf.pages)};actual=[]
for i,p in enumerate(pdf.pages,1):
 for a in p.get('/Annots',[]):
  a=a.get_object();d=a.get('/Dest')
  if d and ids.get(d[0].idnum,0)>=json.loads((ROOT/'report/build/paper.pagination.json').read_text())['references_starts_page']:actual.append({'source_page':i,'target_page':ids[d[0].idnum],'top':float(d[3]),'rect':[float(v) for v in a['/Rect']]})
actual.sort(key=lambda x:(x['source_page'],-x['rect'][3],x['rect'][0]))
for x in actual:x.pop('rect')
grouped=[]
for x in actual:
 if not grouped or x!=grouped[-1]:grouped.append(x)
actual=grouped
assert len(actual)==len(expected),(len(actual),len(expected))
for x,y in zip(expected,actual):
 x.update(y);x['target_contains_expected_reference']=norm(' '.join(x['reference'].split()[:12])) in norm(pdf.pages[x['target_page']-1].extract_text())
 assert x['target_contains_expected_reference'], x
out=ROOT/'report/build/template-check/citation-links.json';out.write_text(json.dumps(expected,indent=2)+'\n')
print(len(expected),'citation links all resolve to pages containing expected reference')

import subprocess
bbox=E.fromstring(subprocess.check_output(['pdftotext','-bbox-layout',str(ROOT/'report/build/paper.pdf'),'-']))
ns={'x':'http://www.w3.org/1999/xhtml'}
for x in expected:
 page=bbox.findall('.//x:page',ns)[x['target_page']-1];words=page.findall('.//x:word',ns);stream='';locations=[]
 for w in words:
  z=norm(w.text or '');stream+=z;locations += [float(w.get('yMin'))]*len(z)
 prefix=norm(' '.join(x['reference'].split()[:12]));at=stream.index(prefix)
 x['target_y_delta_pt']=round(abs((float(page.get('height'))-x['top'])-locations[at]),2)
 assert x['target_y_delta_pt']<20,x
out.write_text(json.dumps(expected,indent=2)+'\n')
print('All destinations within 20 pt of expected entry start; max',max(x['target_y_delta_pt'] for x in expected))
