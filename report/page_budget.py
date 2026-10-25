"""Measure the saved paper render; section spans include figures and tables."""
import hashlib,json,re,subprocess,sys,unicodedata
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'report'))
from build_paper import prepare_ast,walk
out=ROOT/'report/build/paper'
source=out.with_suffix('.source.md');raw=source.read_bytes()
ast,_=prepare_ast(ROOT/'report/paper.md',raw)
xml=subprocess.check_output(['pdftotext','-bbox-layout',str(out.with_suffix('.pdf')),'-'])
r=ET.fromstring(xml);ns={'x':'http://www.w3.org/1999/xhtml'}
words=[]
for pi,page in enumerate(r.findall('.//x:page',ns),1):
 for word in page.findall('.//x:word',ns):words.append((word.text or '',pi,float(word.get('yMin')),float(word.get('yMax'))))
def norm(s):return ''.join(c.lower() for c in unicodedata.normalize('NFKD',s) if c.isalnum())
stream='';loc=[]
for i,w in enumerate(words):
 s=norm(w[0]);stream+=s;loc += [i]*len(s)
def plain(b):
 return subprocess.check_output(['pandoc','-f','json','-t','plain','--wrap=none'],input=json.dumps({'pandoc-api-version':ast['pandoc-api-version'],'meta':{},'blocks':[b]}),text=True).strip()
def position(text,after=0):
 s=norm(text);at=stream.find(s,after)
 if at<0:raise ValueError(text)
 a=words[loc[at]];b=words[loc[at+len(s)-1]]
 return {'page':a[1],'y':a[2],'end_page':b[1],'end_y':b[3],'end_char':at+len(s)}
sections=[];current=None;objects=[];notes=[];heading_after=0
for b in ast['blocks']:
 t=b['t'];text=plain(b)
 if t=='Header':
  if text=='Code and Data':break
  if b['c'][0]==1:continue
  current={'section':text,'words':0,'start':position(text,heading_after)};sections.append(current);heading_after=current['start']['end_char']
 elif current:
  count=len(text.split());current['words']+=count
  if t=='Table':objects.append({'object':'Table','words':count,'section':current['section']})
  if t=='Para' and any(n.get('t')=='Image' for n in walk(b)):objects.append({'object':'Figure','section':current['section'],'source':next(n['c'][2][0] for n in walk(b) if n.get('t')=='Image')})
  if t=='BlockQuote' or text.startswith(('Related-work author note','[TODO','[Placeholder')):
   notes.append({'section':current['section'],'words':count,'text':text,'position':position(text[:100])})
end=position('Code and Data')
for i,s in enumerate(sections):
 stop=sections[i+1]['start'] if i+1<len(sections) else end
 s['end']=stop
 s['page_equivalent']=(stop['page']-s['start']['page'])+(stop['y']-s['start']['y'])/648
 # A section crossing a page includes the unused bottom/top space in its span.
rows=['# Main-body page budget','', 'Measured from the saved paper.source.md and paper.pdf snapshot. Page-equivalents use the 9-inch text height; spans include headings, graphics, captions and page-break whitespace. These are layout spans, not guaranteed savings. Section word counts include tables and captions.','', '| Section | Words | Starts on page | Page-equivalent span |','|---|---:|---:|---:|']
for s in sections:rows.append(f"| {s['section']} | {s['words']} | {s['start']['page']} | {s['page_equivalent']:.2f} |")
rows+=['','## Editorial blocks','',f"Blocks labelled editorial/TODO/placeholder (including substantive draft Methods, not automatically removable): {sum(n['words'] for n in notes)} words. This excludes isolated inline TODO fragments inside substantive paragraphs.",'','| Section | Words | Beginning |','|---|---:|---|']
for n in notes:rows.append(f"| {n['section']} | {n['words']} | {n['text'][:100].replace('|','/')}… |")
(out.parent/'page_budget.md').write_text('\n'.join(rows)+'\n')
(out.parent/'page_budget.json').write_text(json.dumps({'source_sha256':hashlib.sha256(raw).hexdigest(),'pdf_sha256':hashlib.sha256(out.with_suffix('.pdf').read_bytes()).hexdigest(),'sections':sections,'editorial_blocks':notes,'objects':objects},indent=2)+'\n')
print('\n'.join(rows))
