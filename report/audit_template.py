"""Compare effective template formatting and inspect PDF fonts and links."""
import json
import re
import subprocess
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
from docx import Document
from docx.oxml.ns import qn
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'report/build/template-check'
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def text(p):
    return ''.join(p.xpath('.//w:t/text()', namespaces=NS))


class File:
    def __init__(self,path):
        with ZipFile(path) as z:
            self.root=etree.fromstring(z.read('word/document.xml'))
            self.styles=etree.fromstring(z.read('word/styles.xml'))
            self.notes=etree.fromstring(z.read('word/footnotes.xml'))
        self.doc=Document(path)
        self.ps=self.root.findall('.//w:p',NS)
        self.index={s.get(qn('w:styleId')):s for s in self.styles.findall('w:style',NS)}
    def find(self,prefix):
        if prefix == 'Recruited':
            return next(p for p in self.ps if p.find('w:pPr/w:pStyle',NS) is not None and p.find('w:pPr/w:pStyle',NS).get(qn('w:val')) == 'Title')
        return next(p for p in self.ps if text(p).startswith(prefix))
    def style_chain(self,style):
        out=[]
        while style in self.index:
            s=self.index[style];out.append(s)
            b=s.find('w:basedOn',NS);style=b.get(qn('w:val')) if b is not None else None
        return out
    def properties(self,p):
        runs=p.findall('.//w:r',NS)
        r=next((r for r in runs if text(r).strip()),runs[0] if runs else etree.Element(qn('w:r')))
        sid=p.find('w:pPr/w:pStyle',NS)
        chain=self.style_chain(sid.get(qn('w:val')) if sid is not None else 'Normal')
        char=r.find('w:rPr/w:rStyle',NS)
        chars=self.style_chain(char.get(qn('w:val'))) if char is not None else []
        rps=[r.find('w:rPr',NS)]+[s.find('w:rPr',NS) for s in chars+chain]+[self.styles.find('w:docDefaults/w:rPrDefault/w:rPr',NS)]
        pps=[p.find('w:pPr',NS)]+[s.find('w:pPr',NS) for s in chain]+[self.styles.find('w:docDefaults/w:pPrDefault/w:pPr',NS)]
        def val(parts,tag,attr='val',default=None):
            for part in parts:
                node=part.find('w:'+tag,NS) if part is not None else None
                if node is not None:
                    value=node.get(qn('w:'+attr))
                    if value is not None:return value
                    if tag in ['b','i','caps']:return '1'
            return default
        line=val(pps,'spacing','line','240');rule=val(pps,'spacing','lineRule','auto')
        return {'font':val(rps,'rFonts','ascii','unspecified'),
                'size_pt':float(val(rps,'sz',default='22'))/2,
                'bold':val(rps,'b',default='0') not in ['0','false'],
                'italic':val(rps,'i',default='0') not in ['0','false'],
                'all_caps':val(rps,'caps',default='0') not in ['0','false'],
                'alignment':val(pps,'jc',default='left'),
                'line_spacing':str(round(float(line)/240,3))+' ×' if rule=='auto' else str(float(line)/20)+' pt '+rule,
                'before_pt':float(val(pps,'spacing','before','0'))/20,
                'after_pt':float(val(pps,'spacing','after','0'))/20,
                'first_line_pt':float(val(pps,'ind','firstLine','0'))/20-float(val(pps,'ind','hanging','0'))/20,
                'left_pt':float(val(pps,'ind','left','0'))/20,
                'right_pt':float(val(pps,'ind','right','0'))/20}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    a=File(ROOT/'report/template.docx');b=File(ROOT/'report/build/paper.docx')
    roles=[('Body','What problem','In July'),('Title','PROJECT TITLE','Recruited'),
           ('Author','Author name 1','Leonidas Raghav'),('With/Apart','With','With'),
           ('Abstract heading','Abstract','Abstract'),('Abstract body','Summarize your project','Can we tell'),
           ('Heading 1',None,None),('Heading 2','1. Introduction','1. Introduction'),('Heading 3','Limitations','3.1 Setup'),
           ('References','[Reference 1]','Agrawal,'),('Captions',None,'Figure 1.'),
           ('Table header',None,'Evaluation'),('Table body',None,'Held-out scenario'),('Inline code',None,None)]
    rows=[]
    for role,ap,bp in roles:
        aa=a.properties(a.find(ap)) if ap else None
        bb=b.properties(b.find(bp)) if bp else None
        if role=='Inline code':
            run=next((r for r in b.root.findall('.//w:r',NS) if r.find('w:rPr/w:rStyle',NS) is not None and r.find('w:rPr/w:rStyle',NS).get(qn('w:val'))=='VerbatimChar'),None)
            if run is not None:
                clone=etree.Element(qn('w:p'));clone.append(etree.fromstring(etree.tostring(run)));bb=b.properties(clone)
        rows.append({'role':role,'template':aa,'paper':bb})
    rows.append({'role':'Footnote','template':a.properties(a.notes.find('.//w:p',NS)), 'paper':b.properties(next(n for n in b.notes.findall('.//w:p',NS) if 'Research conducted' in text(n)))})
    geometry=[]
    for prop in ['page_width','page_height','top_margin','bottom_margin','left_margin','right_margin','header_distance','footer_distance']:
        geometry.append({'property':prop,'template_pt':getattr(a.doc.sections[0],prop).pt,'paper_pt':getattr(b.doc.sections[0],prop).pt})
    fonts={}
    for key,path in [('template',OUT/'template.pdf'),('paper',ROOT/'report/build/paper.pdf')]:
        result=subprocess.check_output(['pdffonts',str(path)],text=True)
        (OUT/(key+'-pdffonts.txt')).write_text(result);fonts[key]=result
    font_sets = {}
    for key, listing in fonts.items():
        lines = [line.split() for line in listing.splitlines()[2:] if line.strip()]
        assert all(fields[-5] == 'yes' for fields in lines), 'Unembedded PDF font'
        font_sets[key] = sorted({fields[0].split('+')[-1] for fields in lines})
    assert set(font_sets['paper']) <= set(font_sets['template']), font_sets
    assert all(x['template_pt'] == x['paper_pt'] for x in geometry)
    pdf=PdfReader(ROOT/'report/build/paper.pdf');links=[]
    for page_number,page in enumerate(pdf.pages,1):
        for annotation in page.get('/Annots',[]):
            x=annotation.get_object()
            if x.get('/Subtype')!='/Link':continue
            action=x.get('/A',{});links.append({'page':page_number,'uri':str(action.get('/URI','')), 'destination':str(x.get('/Dest',action.get('/D',''))),'action':str(action.get('/S',''))})
    destinations={k:{'page':pdf.get_destination_page_number(v)+1,'top':str(v.top)} for k,v in pdf.named_destinations.items()}
    data={'geometry':geometry,'roles':rows,'pdf_links':links,'named_destinations':destinations,'fonts':fonts,'font_sets':font_sets}
    (OUT/'audit.json').write_text(json.dumps(data,indent=2)+'\n')
    md=['# Template formatting check','','Values are effective XML formatting at representative content, including direct formatting and style inheritance. Dimensions are points. Body paragraphs retain authored emphasis.','', '| Page property | Template | Paper |','|---|---:|---:|']
    md += [f"| {x['property']} | {x['template_pt']} | {x['paper_pt']} |" for x in geometry]
    md += ['', 'Neither document has a PAGE field, header text, or footer text; the template has a starting page-number setting but does not print numbers.','','| Role | Property | Template | Paper | Match |','|---|---|---|---|---|']
    for row in rows:
        aa=row['template'];bb=row['paper']
        if not bb:md.append(f"| {row['role']} | usage | no sample | not used | — |");continue
        for key,value in bb.items():
            av=aa.get(key) if aa else 'no sample'
            md.append(f"| {row['role']} | {key} | {av} | {value} | {'yes' if aa and av==value else 'see notes'} |")
    md += ['', '## Differences and coverage','','- The title string is unchanged; all-capitals display is applied to match the template. One author replaces six placeholders; the author and affiliation occupy two centred lines. Abstract length differs, but its native table width, indentation, italic face and paragraph settings are retained.', '- The template has no Heading 1 content, caption example, data-table text example or code example. Main headings use its direct-format Heading 2; subsections use Heading 3. Captions retain 9-point Old Standard TT and data tables 9-point Old Standard TT so their existing dense content remains readable. These two sizes are adaptations, not claimed template matches.', '- The only glyph absent from the installed Old Standard TT was κ. It is explicitly set in Arial, a font present in the template, instead of allowing platform fallback to Helvetica. No text is substituted.', '- Reference entries use the template’s numbered-list layout while retaining APA citation text from citeproc. Author–year citations link to their entries, bibliography URLs are clickable, and the template footnote hyperlink remains intact. Defining Pandoc paragraph styles absent from the template removes the stray-X rendering artifact.', '', '## PDF checks','', f"Link annotations: {len(links)}. Named destinations: {len(destinations)} (the exporter uses direct destination arrays). See audit.json for destinations and URI targets; see citation-links.json for the reference-entry checks. All PDF fonts are embedded subsets: Old Standard TT regular/bold/italic and Arial, each also present in the template; no Helvetica fallback remains."]
    (OUT/'audit.md').write_text('\n'.join(md)+'\n')
    print(json.dumps({'links':len(links),'named_destinations':len(destinations)}))

if __name__=='__main__':main()
