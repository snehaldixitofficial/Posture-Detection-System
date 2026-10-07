"""IEEE-style PDF fallback from the single-file LaTeX manuscript.

The built-in compiler was unavailable (platform-directory initialization error).
This exporter does not claim to execute IEEEtran. It renders matching content
with Times type, two 3.5-inch columns, vector figures and artifact-derived tables.
"""
from functools import partial
from reportlab.pdfgen.canvas import Canvas
import html
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image, FrameBreak, NextPageTemplate, KeepTogether, PageBreak, BalancedColumns
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'docs/paper'
SOURCE = PAPER / 'STAY_UPRIGHT_IEEE.tex'
OUTPUT = PAPER / 'STAY_UPRIGHT_IEEE.pdf'
ASSETS = PAPER / 'export_assets'
ASSETS.mkdir(exist_ok=True)
CW = 252
for name, filename in [('Times-Roman','times.ttf'),('Times-Bold','timesbd.ttf'),('Times-Italic','timesi.ttf'),('Times-BoldItalic','timesbi.ttf'),('Courier','cour.ttf'),('Helvetica','arial.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts') / filename)))
pdfmetrics.registerFontFamily('Times-Roman',normal='Times-Roman',bold='Times-Bold',italic='Times-Italic',boldItalic='Times-BoldItalic')
styles = {
    'body': ParagraphStyle('body',fontName='Times-Roman',fontSize=10,leading=12.1,alignment=TA_JUSTIFY,firstLineIndent=10,spaceAfter=4.5),
    'abstract': ParagraphStyle('abstract',fontName='Times-Bold',fontSize=9.2,leading=11,alignment=TA_JUSTIFY,spaceAfter=7),
    'section': ParagraphStyle('section',fontName='Times-Roman',fontSize=10,leading=12,alignment=TA_CENTER,spaceBefore=10,spaceAfter=6,keepWithNext=True),
    'subsection': ParagraphStyle('subsection',fontName='Times-Italic',fontSize=10,leading=12,spaceBefore=6,spaceAfter=4,keepWithNext=True),
    'caption': ParagraphStyle('caption',fontName='Times-Roman',fontSize=8,leading=9.7,alignment=TA_CENTER,spaceAfter=5),
    'cell': ParagraphStyle('cell',fontName='Times-Roman',fontSize=8,leading=9.4),
    'reference': ParagraphStyle('reference',fontName='Times-Roman',fontSize=8.2,leading=9.6,leftIndent=13,firstLineIndent=-13,spaceAfter=3),
}
tex = SOURCE.read_text(encoding='utf-8')
keys = re.findall(r'\\bibitem\{([^}]+)\}',tex)
CITES = {k:i+1 for i,k in enumerate(keys)}
REFS = {'tab:position':'I','tab:features':'II','tab:counts':'III','tab:performance':'IV','tab:baseline':'V','tab:ablation':'VI','fig:pipeline':'1','fig:confusion':'2'}

def unmath(value):
    value=value.replace(r'\mathrm{None}','None').replace(r'\mathrm{Lean}','Lean')
    value=value.replace(r'\{','{').replace(r'\}','}').replace(r'\times',' × ').replace(r'\in',' ∈ ').replace(r'\gamma','γ').replace(r'\theta','θ').replace(r'\%','%')
    value=re.sub(r'\\(?:mathrm|text|operatorname)\{([^{}]*)\}',r'\1',value)
    value=value.replace(r'\quad',' ').replace(r'\,',' ')
    value=re.sub(r'([A-Za-z])_([A-Za-z0-9])',r'\1<sub>\2</sub>',value)
    value=re.sub(r'\^\{(-?[0-9]+)\}',r'<super>\1</super>',value)
    return value

def prose(value):
    value=re.sub(r'\\url\{([^}]+)\}',lambda m:'<link href="'+html.escape(m.group(1))+'">'+html.escape(m.group(1))+'</link>',value)
    value=re.sub(r'\\cite\{([^}]+)\}',lambda m:'['+', '.join(str(CITES[k]) for k in m.group(1).split(','))+']',value)
    value=re.sub(r'\\ref\{([^}]+)\}',lambda m:REFS[m.group(1)],value)
    value=value.replace('₁','<sub>1</sub>').replace('₂','<sub>2</sub>')
    value=value.replace('~',' ').replace(r'\emph{','<i>{').replace(r'\textbf{','<b>{').replace(r'\texttt{','<font name="Courier" size="8">{')
    for tag,end in [('<i>','</i>'),('<b>','</b>'),('<font name="Courier" size="8">','</font>')]:
        value=re.sub(re.escape(tag)+r'\{([^{}]*)\}',lambda m:tag+m.group(1)+end,value)
    value=re.sub(r'\$([^$]+)\$',lambda m:unmath(m.group(1)),value)
    value=value.replace(r'\%','%').replace(r'\_','_').replace(r'\&','&amp;').replace(r'\emph','')
    value=value.replace('---','—').replace('--','–').replace('``','“').replace("''",'”')
    value=value.replace(r'\url{','{')
    value=re.sub(r'\s+',' ',value).strip()
    value=value.replace(' & ',' &amp; ')
    return value

def p(value,kind='body'):
    return Paragraph(prose(value),styles[kind])

def table(caption,headers,rows,widths):
    data=[[p(str(c),'cell') for c in row] for row in [headers]+rows]
    t=Table(data,colWidths=widths,hAlign='CENTER',repeatRows=1)
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEABOVE',(0,0),(-1,0),.65,colors.black),('LINEBELOW',(0,0),(-1,0),.45,colors.black),('LINEBELOW',(0,-1),(-1,-1),.65,colors.black),('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    return KeepTogether([Spacer(1,5),p(caption,'caption'),t,Spacer(1,8)])

def pipeline():
    labels=[('Protocol-labeled videos','Correct / Slouch / Lean Left / Lean Right'),('MediaPipe Pose Lite + quality gate','33 outputs; seven required head/shoulder joints'),('Shared versioned features','21 normalized geometric descriptors'),('Frozen split','Take 02: train/validation + gap; take 03: test'),('Common RF / RBF SVM / XGBoost','Exact rules and named directional extension'),('Frozen evaluation + separate live refit','Reports, predictions, timings and checksums'),('Browser features → model switch → feedback','Frozen models; optional loopback RF refit')]
    height=7*34+6*10; d=Drawing(CW,height)
    for i,(a,b) in enumerate(labels):
        y=height-34-i*44
        d.add(Rect(5,y,CW-10,34,rx=2,ry=2,fillColor=colors.white,strokeColor=colors.black,strokeWidth=.6))
        d.add(String(CW/2,y+21,a,fontName='Times-Bold',fontSize=8.1,textAnchor='middle'))
        d.add(String(CW/2,y+9,b,fontName='Times-Roman',fontSize=7.5,textAnchor='middle'))
        if i<6:
            d.add(Line(CW/2,y,CW/2,y-8,strokeWidth=.7));d.add(Polygon([CW/2-2,y-6,CW/2,y-10,CW/2+2,y-6],fillColor=colors.black,strokeColor=colors.black))
    return KeepTogether([Spacer(1,5),d,Spacer(1,4),p('Fig. 1. Implemented pipeline. All scored classifiers use the same test rows; the live refit is separate from frozen evaluation.','caption'),Spacer(1,5)])

def equation(value,index):
    if r'\begin{cases}' in value:
        rows=[['ŷr =','Slouch','if f₂ − 1.352 &lt; −0.12'],['','Lean','else if |f₁ − 0.031| &gt; 0.55'],['','Correct','otherwise']]
        t=Table([[p(x,'cell') for x in r] for r in rows],colWidths=[30,42,160]);t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),1),('RIGHTPADDING',(0,0),(-1,-1),1)]))
        return KeepTogether([Spacer(1,4),t,p(f'({index})','caption')])
    expr=re.sub(r'\s+',' ',value.strip())
    fig=plt.figure(figsize=(6.5,.7));fig.patch.set_alpha(0)
    plt.rcParams['mathtext.fontset']='stix'
    fig.text(.5,.5,'$'+expr+'$',ha='center',va='center',fontsize=15)
    path=ASSETS/f'equation_{index}.png'
    fig.savefig(path,dpi=300,bbox_inches='tight',pad_inches=.04,transparent=True);plt.close(fig)
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w,h=im.size
    display_width=min(CW-15,w*72/300);display_height=h/w*display_width
    return KeepTogether([Spacer(1,5),Image(str(path),width=display_width,height=display_height),p(f'({index})','caption')])

def make_table(label):
    if label=='tab:position':
        return table('TABLE I<br/>RESEARCH POSITION RELATIVE TO PRIOR WORK',['Work','Input/approach','Relationship to this study'],[
            ['Lee et al. [3]','Frontal face/shoulder features; weighted RF','Prior use of this observable body region'],['ML-2SN [4]','Skeletal spatial/temporal streams','Models temporal behavior; present study uses static geometry'],['SitPose [5]','Kinect depth; ensemble learning','Different sensor and broader participant evaluation'],['MultiPosture [6]','Upper/lower-body joint coordinates','Different labels and feature contract'],['Stay Upright','Seven landmarks; common RF/SVM/XGB pipeline','Audited quality gate, reconciled rules, personal video holdout']],[59,82,111])
    if label=='tab:features':
        return table('TABLE II<br/>FEATURE GROUPS AND EXACT DIMENSIONALITY',['Group','N','Descriptors'],[
            ['Legacy geometry',3,'f₁, f₂, signed facial asymmetry'],['Planar ratios',8,'Nose–shoulder-midpoint; each ear–ipsilateral shoulder; nose–each shoulder; eye-midpoint–shoulder-midpoint; ear width; eye width'],['Signed angles',3,'Ear/shoulder inclination, head tilt, shoulder angle'],['Planar offsets',4,'Shoulder height difference; nose vertical/lateral and ear-midpoint vertical offsets'],['Depth proxies',3,'Nose and ear-midpoint depth relative to shoulders; bilateral face/shoulder depth asymmetry'],['Total',21,'Seven required landmarks; no hip/leg coordinates']],[56,17,179])
    if label=='tab:counts':
        return table('TABLE III<br/>RECORDED DATASET AND FROZEN TEST SUPPORT',['Protocol class','Take 02','Take 03','Total'],[['Correct',236,242,478],['Slouch',242,242,484],['Lean Left',242,242,484],['Lean Right',242,242,484],['Total',962,968,'1,930']],[100,50,50,52])
    if label=='tab:baseline':
        return table('TABLE V<br/>FAIR THREE-STATE COMPARISON',['Method','Accuracy (%)','Macro F1'],[['Original fixed-default rules','97.62','0.9756'],['RF, collapsed predictions','98.35','0.9779'],['RBF SVM, collapsed predictions','95.14','0.9346'],['XGBoost, collapsed predictions','98.86','0.9848']],[139,60,53])
    if label=='tab:ablation':
        return table('TABLE VI<br/>EXPLORATORY ABLATION: MACRO F1 ON REUSED TEST VIDEOS',['Representation','N','RF','SVM','XGB'],[['Legacy f₁, f₂',2,'0.6575','0.6428','0.7100'],['Legacy + signed asymmetry',3,'0.8467','0.8729','0.8418'],['All except depth proxies',18,'0.9845','1.0000','0.9886'],['Full representation',21,'0.9835','0.9510','0.9886']],[116,16,40,40,40])
    return None

def wide_results(canvas,doc):
    flow=table('TABLE IV<br/>PRIMARY FOUR-CLASS RESULTS ON THE SAME 968 TAKE-03 FRAMES (SINGLE-PERSON PILOT)',
       ['Model','Acc. (%)','Macro prec.','Macro recall','Macro F1','Val. F1','Fit (s)','Batch ms/frame','Median single ms'],
       [['RF','98.35','0.9845','0.9835','0.9835','0.9807','0.287','0.0107','7.624'],['RBF SVM','95.14','0.9593','0.9514','0.9510','0.9807','0.004','0.0037','0.217'],['XGBoost','98.86','0.9891','0.9886','0.9886','0.9494','0.240','0.0050','0.231']],
       [63,43,57,57,49,49,40,82,82])
    # Draw the individual flowables to preserve vector tables on the broad float.
    y=738
    for f in flow._content:
        w,h=f.wrap(522,666);f.drawOn(canvas,45,y-h);y-=h
    y-=12
    for i,(name,c,e) in enumerate([('RF',226,16),('RBF SVM',195,47),('XGBoost',231,11)]):
        x=45+i*179
        canvas.setFont('Times-Bold',9);canvas.drawCentredString(x+82,y,name)
        labels=['C','S','L','R'];matrix=[[c,e,0,0],[0,242,0,0],[0,0,242,0],[0,0,0,242]]
        for j,v in enumerate(labels):
            canvas.setFont('Times-Roman',8);canvas.drawCentredString(x+43+j*29,y-15,v)
        for row in range(4):
            canvas.drawString(x+13,y-31-row*19,labels[row])
            for col in range(4):
                val=matrix[row][col];shade=val/242
                canvas.setFillColor(colors.Color(1-.68*shade,1-.52*shade,1-.20*shade));canvas.rect(x+29+col*29,y-37-row*19,29,19,fill=1,stroke=0)
                canvas.setFillColor(colors.black);canvas.drawCentredString(x+43+col*29,y-31-row*19,str(val))
    caption=p('Fig. 2. Frozen test confusion matrices. Rows: actual; columns: predicted. C = Correct, S = Slouch, L = Lean Left, R = Lean Right. Each actual class contains 242 frames.','caption')
    caption.wrap(522,50);caption.drawOn(canvas,45,y-135)

def canvas_meta(canvas,doc):
    canvas.setTitle('Stay Upright: Auditable Head-and-Shoulder Posture Classification with Video-Disjoint Evaluation')
    canvas.setAuthor('Snehal Dixit')
    canvas.setSubject('IEEE-style conference draft; one-person posture pilot')

def result_page(canvas,doc):
    canvas_meta(canvas,doc);wide_results(canvas,doc)

frames=lambda top:[Frame(45,72,CW,top-72,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0),Frame(315,72,CW,top-72,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)]
doc=BaseDocTemplate(str(OUTPUT),pagesize=(612,792),leftMargin=45,rightMargin=45,topMargin=54,bottomMargin=72,title='Stay Upright',author='Snehal Dixit')
doc.addPageTemplates([PageTemplate(id='First',frames=[Frame(45,608,522,130,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)]+frames(610),onPage=canvas_meta),PageTemplate(id='Normal',frames=frames(738),onPage=canvas_meta),PageTemplate(id='Results',frames=frames(483),onPage=result_page),PageTemplate(id='Final',frames=frames(738),onPage=canvas_meta)])
title=Paragraph('Stay Upright: Auditable Head-and-Shoulder Posture Classification with Video-Disjoint Evaluation',ParagraphStyle('title',fontName='Times-Roman',fontSize=23,leading=26,alignment=TA_CENTER,spaceAfter=10))
author=Paragraph('Snehal Dixit<br/>School of Computing Science Engineering and Artificial Intelligence (SCAI)<br/>VIT Bhopal University, India<br/>snehal.25mip10072@vitbhopal.ac.in',ParagraphStyle('author',fontName='Times-Roman',fontSize=10,leading=12,alignment=TA_CENTER))
story=[title,author,FrameBreak(),NextPageTemplate(['Normal','Normal','Normal','Results','*','Normal'])]
abstract=re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',tex,re.S).group(1)
story.append(p('<b>Abstract—</b>'+abstract,'abstract'))
kw=re.search(r'\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}',tex,re.S).group(1)
story.append(p('<b><i>Index Terms—</i></b>'+kw,'abstract'))
body=tex[tex.index(r'\section{Introduction}'):tex.index(r'\begin{thebibliography}')]
token=re.compile(r'(\\begin\{table\*?\}.*?\\end\{table\*?\}|\\begin\{figure\*?\}.*?\\end\{figure\*?\}|\\begin\{equation\}.*?\\end\{equation\}|\\section\*?\{[^}]+\}|\\subsection\{[^}]+\})',re.S)
section=0; subsection=0; eq=0; final_tail_index=None
roman=['I','II','III','IV','V','VI','VII']
for piece in token.split(body):
    piece=piece.strip()
    if not piece:continue
    if piece.startswith(r'\begin{table'):
        label=re.search(r'\\label\{([^}]+)\}',piece).group(1);f=make_table(label)
        if f:story.append(f)
    elif piece.startswith(r'\begin{figure'):
        if 'fig:pipeline' in piece:story.append(pipeline())
    elif piece.startswith(r'\begin{equation}'):
        if story and isinstance(story[-1], Paragraph): story[-1].keepWithNext=True
        eq+=1;story.append(equation(piece[len(r'\begin{equation}'): -len(r'\end{equation}')],eq))
    elif piece.startswith(r'\section'):
        heading=re.search(r'\{([^}]+)\}',piece).group(1)
        if '*' in piece:
            final_tail_index=len(story)
            story.append(p(heading.upper(),'section'))
        else:
            section+=1;subsection=0
            if section == 6: final_tail_index=len(story)
            story.append(p(roman[section-1]+'. '+heading.upper(),'section'))
    elif piece.startswith(r'\subsection'):
        subsection+=1;heading=re.search(r'\{([^}]+)\}',piece).group(1);story.append(p(chr(64+subsection)+'. '+heading,'subsection'))
    else:
        for para in re.split(r'\n\s*\n',piece):
            if para.strip():story.append(p(para))
story.append(p('REFERENCES','section'))
bib=tex[tex.index(r'\begin{thebibliography}'):tex.index(r'\end{thebibliography}')]
for key,content in re.findall(r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem|$)',bib,re.S):
    content=content.replace(r'Caba\~nero G\'omez','Cabañero Gómez').replace(r'Herv\'as','Hervás').replace(r'Gonz\'alez D\'iaz','González Díaz')
    content=re.sub(r'\\url\{([^}]+)\}',lambda m:'<link href="'+html.escape(m.group(1))+'">'+html.escape(m.group(1))+'</link>',content)
    story.append(p(f'[{CITES[key]}] '+content,'reference'))
if final_tail_index is not None:
    tail=story[final_tail_index:]
    heights=[f.wrap(CW,666)[1]+f.getSpaceBefore()+f.getSpaceAfter() for f in tail]
    total=sum(heights)
    split=min((i for i in range(1,len(tail)) if not tail[i-1].getKeepWithNext()), key=lambda i: abs(sum(heights[:i])-total/2))
    story=story[:final_tail_index]+[NextPageTemplate('Final'),PageBreak()]+tail[:split]+[FrameBreak()]+tail[split:]
doc.build(story,canvasmaker=partial(Canvas,initialFontName='Times-Roman'))
print(OUTPUT)
