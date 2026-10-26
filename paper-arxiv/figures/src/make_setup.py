"""Adapt the sprint setup diagram, retaining its documented episode excerpt."""
import ast
import hashlib
import json
from pathlib import Path
import textwrap
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from style import configure, MODEL_COLORS

PAPER=Path(__file__).resolve().parents[2]
SOURCE=PAPER.parent/'report/figures/make_figure1.py'
INK='#222222';MUTED='#666666';BLUE=MODEL_COLORS['qwen'];PEER='#F3E9D4';TARGET='#E2EEF6'


def box(ax,x,y,w,h,label,fill='white',size=8):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.005',fc=fill,ec='#777777',lw=.7))
    ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=size)


def arrow(ax,start,end):
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=9,lw=.8,color=INK))


def main():
    configure()
    tree=ast.parse(SOURCE.read_text())
    exchange=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXCHANGE' for t in n.targets))
    fig=plt.figure(figsize=(6.5,4.9))
    top=fig.add_axes([.02,.62,.96,.35]);top.axis('off');top.set(xlim=(0,1),ylim=(0,1))
    top.text(0,1,'(a) A real episode: refusal, then disclosure',weight='bold',fontsize=10,va='top')
    for i,(kind,who,text,note) in enumerate(exchange):
        x=i*.34
        top.add_patch(FancyBboxPatch((x,.02),.315,.78,boxstyle='round,pad=0.004',fc=PEER if kind=='peer' else TARGET,ec=BLUE if kind=='leak' else '#777777',lw=1))
        top.text(x+.012,.73,who,fontsize=8,weight='bold',va='top')
        top.text(x+.012,.59,textwrap.fill('“'+text+'”',25),fontsize=8,va='top',linespacing=1.15)
        if i<2:arrow(top,(x+.317,.40),(x+.337,.40))
    left=fig.add_axes([.02,.05,.45,.53]);left.axis('off');left.set(xlim=(0,1),ylim=(0,1))
    left.text(0,1,'(b) Who acts; who observes',weight='bold',fontsize=10,va='top')
    box(left,.02,.60,.34,.20,'Peer\nasks for token',PEER)
    box(left,.61,.60,.37,.20,'Target\nholds token',TARGET)
    arrow(left,(.37,.70),(.60,.70));left.text(.48,.79,'channel',ha='center',fontsize=7.5)
    box(left,.61,.84,.37,.10,'Operator rule',size=7.5);arrow(left,(.79,.84),(.79,.80))
    box(left,.61,.37,.37,.15,'Private file\n+ mock tools',size=7.5);arrow(left,(.79,.60),(.79,.52))
    box(left,.02,.37,.42,.15,'Text monitor\nreads transcript',size=7.5)
    arrow(left,(.48,.68),(.23,.53))
    box(left,.21,.08,.76,.17,'Probe reads target activations\nbefore the call or during reasoning',TARGET,size=7.5)
    arrow(left,(.75,.60),(.59,.26))
    right=fig.add_axes([.53,.04,.45,.54]);right.axis('off');right.set(xlim=(-1.8,6.7),ylim=(-.7,5.9))
    right.text(-1.8,5.9,'(c) Labels on a schematic episode',weight='bold',fontsize=9.5,va='top')
    xs=[0,1,2,3,4,5,6];rounds=[1,2,3,4,5,6,6]
    right.add_patch(Rectangle((.55,.1),5.9,4.25,fc='#EDF4F8',ec='none'))
    for y,label in [(4.9,'Round'),(3.9,'Call'),(2.8,'Ever'),(1.8,'This/next\nround'),(.7,'This call')]:right.text(-1.8,y,label,fontsize=8,va='center')
    for x,r in zip(xs,rounds):right.text(x,4.9,str(r),ha='center',va='center',fontsize=8)
    events=['Read','Refuse','Refuse','Refuse','Refuse','Read','Leak']
    for i,(x,event) in enumerate(zip(xs,events)):
        right.text(x,3.9,event,ha='center',va='center',rotation=55,fontsize=7.5,color=BLUE if i==6 else INK)
        for y,v in [(2.8,1),(1.8,int(rounds[i]>=5)),(.7,int(i==6))]:right.text(x,y,'–' if i==0 else str(v),ha='center',va='center',fontsize=9)
    right.text(-1.8,-.15,'Shaded: calls scored after the first read.\nA refusing episode has zero for each label.',fontsize=7.5,va='top')
    out=PAPER/'figures/fig2_setup'
    for ext in ['pdf','png']:fig.savefig(out.with_suffix('.'+ext),bbox_inches=None,dpi=180,facecolor='white')
    out.with_suffix('.json').write_text(json.dumps({'source':str(SOURCE.relative_to(PAPER.parent)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'excerpt':'EXCHANGE constant, verbatim shortened quotes and token truncation preserved','timeline':'schematic, not reconstructed transcript; seven calls across six illustrative rounds','width_inches':6.5,'height_inches':4.9,'access_codes_removed':True},indent=2)+'\n')
    plt.close(fig)


if __name__=='__main__':main()
