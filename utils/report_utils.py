import csv
import io
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from xml.sax.saxutils import escape

def csv_bytes(result):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(['inspection_id','status','defect_id','type','description','area_px','area_mm2','box'])
    for d in result['defects']:
        writer.writerow([result['id'],result['status'],d['id'],d['type'],d['description'],d['area_px'],d['area_mm2'],json.dumps(d['box'])])
    if not result['defects']:
        writer.writerow([result['id'],result['status'],'','','','','',''])
    return out.getvalue().encode('utf-8-sig')

def pdf_bytes(result):
    out = io.BytesIO()
    doc = SimpleDocTemplate(out,pagesize=A4,leftMargin=36,rightMargin=36,topMargin=40,bottomMargin=40)
    styles = getSampleStyleSheet()
    story = [Paragraph('VisionAI Industrial Inspection Report',styles['Title']),Spacer(1,16)]
    for key in ['id','status','summary','alignment','elapsed']:
        story.append(Paragraph(f'<b>{key.title()}:</b> {escape(str(result[key]))}',styles['Normal']))
        story.append(Spacer(1,5))
    story.append(Spacer(1,12))
    story.append(Paragraph('Annotated inspection image',styles['Heading2']))
    reader = ImageReader(io.BytesIO(result['result_jpg']))
    w,h = reader.getSize()
    scale = min(510/w,300/h)
    story.append(RLImage(io.BytesIO(result['result_jpg']),width=w*scale,height=h*scale))
    story.append(Spacer(1,14))
    story.append(Paragraph('Detected regions (SAM mask area is not necessarily true defect area)',styles['Heading2']))
    rows = [['#','Type','Area (px)','Area (mm2)']]
    rows += [[str(d['id']),d['type'][:32],str(d['area_px']),str(d['area_mm2'] or 'Not calibrated')] for d in result['defects']]
    if len(rows)==1: rows.append(['-','No detected defects','-','-'])
    t=Table(rows,colWidths=[32,205,95,130],repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#14243d')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('GRID',(0,0),(-1,-1),0.3,colors.lightgrey)]))
    story.append(t)
    doc.build(story)
    return out.getvalue()
