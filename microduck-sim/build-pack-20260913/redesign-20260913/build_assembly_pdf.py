"""Printable field manual from current assembly sources and exact native fastener ledger.
Run with the Codex bundled Python (reportlab, pypdf, Pillow).
"""
from pathlib import Path
import json,re,html,hashlib,collections
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing,Rect,Circle,String
from PIL import Image as PILImage
from pypdf import PdfReader
P=Path(__file__).resolve().parent;OUT=P/'output/pdf';OUT.mkdir(parents=True,exist_ok=True)
for n,f in [('Body','Arial.ttf'),('Bold','Arial Bold.ttf')]:pdfmetrics.registerFont(TTFont(n,'/System/Library/Fonts/Supplemental/'+f))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Body',boldItalic='Bold')
styles=getSampleStyleSheet()
for k in styles.byName:styles[k].fontName='Body'
styles.add(ParagraphStyle(name='Text',fontName='Body',fontSize=10,leading=14,spaceAfter=8))
styles.add(ParagraphStyle(name='SmallText',fontName='Body',fontSize=8.3,leading=11,spaceAfter=5))
styles['Title'].fontName='Bold';styles['Title'].fontSize=25;styles['Title'].leading=30
styles['Heading1'].fontName='Bold';styles['Heading1'].fontSize=18;styles['Heading1'].leading=23
styles['Heading2'].fontName='Bold';styles['Heading2'].fontSize=12;styles['Heading2'].leading=16
story=[]
def fmt(s):
 s=html.escape(str(s)).replace('—','-').replace('–','-').replace('−','-').replace('→',' to ')
 s=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
 s=re.sub(r'`([^`]+)`',r'\1',s)
 s=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',s)
 return s

def para(t,sty='Text'):story.append(Paragraph(fmt(t),styles[sty]))
def heading(t):story.append(Paragraph(fmt(t),styles['Heading1']))
def page(t):
 if story:story.append(PageBreak())
 heading(t)
def image(path,maxheight=310):
 with PILImage.open(path) as im:w,h=im.size
 scale=min(480/w,maxheight/h);story.append(Image(str(path),width=w*scale,height=h*scale));story.append(Spacer(1,9))
def md(text,break_sections=False):
 for block in text.split('\n\n'):
  block=block.strip()
  if not block:continue
  if block.startswith('!['):
   path=re.search(r'\]\(([^)]+)\)',block)[1];image(P/path,350)
  elif block.startswith('# '):heading(block[2:])
  elif block.startswith('## '):
   if break_sections:page(block[3:])
   else:story.append(Paragraph(fmt(block[3:]),styles['Heading2']))
  else:
   if re.match(r'^\d+\. ',block):
    for line in re.split(r'\n(?=\d+\. )',block):para(line.replace('\n',' '))
   else:para(block.replace('\n',' '))
ledger=json.loads((P/'assembly-fasteners.json').read_text());rows=ledger['connections'];contract=json.loads((P/'design-contract.json').read_text())
page('MicroDuck assembly manual')
para('Mechanical assembly, fasteners and first-power worksheet','Heading2')
para('Revision 30 September 2026 | English | Print at 100% on US Letter')
para('Work through the numbered assembly steps, then use the electronics and motor cards at each connection. Screw quantities are installed quantities, not packet sizes or all printed spare copies.')
para('Current architecture: MacBook Pro control and policy computation; Pi sensor capture and forwarding. The software migration, motor-bus owner and transport have not yet been validated. The mechanical design retains Pi Zero geometry. Identify the exact borrowed board before mounting or powering it.')
para('Print jobs: use PRINTING/README.md in the build folder for the active machine-specific jobs and replacements. Do not combine an old job and its replacement. This manual does not direct an unattended print or certify first-article fit.')
para('Reading order','Heading2')
for v in ['1. Inventory and hardware checklist','2. Numbered mechanical assembly steps','3. Electronics connection cards and head fastener diagram','4. Fifteen motor cards with every installed screw position','5. Pin map, fuse groups, wire endpoints and first-power worksheet']:para(v)
para('Prepare: calipers; matching small drivers; tweezers; pliers; deburring tools; multimeter; soldering tools, heat shrink and insulation; labels; controlled-load and temperature/voltage measurement equipment for commissioning.')
para('No tightening torque is specified by the source design. Start plastic screws squarely by hand; stop if the part distorts, a pilot splits or the joint binds. The native geometry checks do not establish printed thread strength.')
page('1. Installed hardware checklist')
for spec,count in ledger['screw_totals_by_spec'].items():para(f'[ ] {count} x {spec}','SmallText')
para('[ ] 14 M2 nuts (nominal thickness 1.6 mm); [ ] 3 M3 nuts (nominal thickness 2.4 mm).')
para('[ ] 4 M3 washers: ID3.2, OD7.0, thickness0.5 mm. [ ] 4 M2.5 DIN433/ISO7092 metal washers: ID2.7, OD5.0, thickness0.5 mm; required at motor IDs1/4/6/9.')
para('TAP means tapping screw for its specified plastic interface. Machine-thread screws used with nuts are a different type. M2 joint heads: maximum diameter4.0 x height1.72 mm. M2.6 rear-center screws must match the ROBOTIS BHS head profile: diameter5.5 x height1.6 mm. The curved manufacturer head was checked; a different head shape is not accepted merely because its bounding dimensions are smaller.')
page('Printed-parts checklist')
para('Check names against the print job. Quantities describe the 89-instance retained stock, including spares and legacy covers. Only two separate idler-horn/cap pairs are installed at IDs11/12; twelve pairs remain spare. The obsolete empty regulator cover and old alarm/regulator arrangements are not installed.')
manifest=json.loads((P/'print-manifest.json').read_text())
stock={}
for item in manifest['instances']:
 key=Path(item['file']).name
 if key not in stock:stock[key]=[item['name'],0]
 stock[key][1]+=item['quantity']
for file,(name,count) in stock.items():para(f'[ ] {count} x {name} ({file})','SmallText')
page('Electronics and retention checklist')
for t in ['[ ] 15 XL330-M288-T motors; 1 OpenRB-150 controller.', '[ ] Pi Zero-form-factor board with confirmed model, installed 40-pin header, bootable card and matching camera connector; actual borrowed board requires identification.', '[ ] Camera Module 3 Wide SC1224; SC1892 200 mm 15-to-22-contact ribbon; BNO085 board and 4397 lead extended to250 mm.', '[ ] MAX98357A amplifier; CMS-30204-18SP 8 ohm1 W speaker; 100 kOhm GAIN-to-VIN resistor.', '[ ] DFR1202 converter, insulated thermal spreading and open insert; external Adafruit5991 receiver; original charger/cable; XT30 pair.', '[ ] 12 fuses total: nine3 A, one10 A, one0.5 A onboard; one5 A external input fuse.', '[ ] Header housing and rated compatible contacts; specified power wires, servo tails and signal extension; insulation, heat shrink, labels and strain relief.', '[ ] Audio: two tie loops per component, four loops total/eight short ties; narrow ties must pass2.4 x1.2 mm slots. Support the speaker rim without touching its diaphragm.', '[ ] Converter: existing support bands, insulated edge liner and removable narrow ties clear of pads/components. Fuse carrier: four tie paths2.5 x1.1 mm. These are retention methods, not additional screw connections.']:para(t)
page('Numbered mechanical assembly')
md((P/'ASSEMBLY-STEPS.md').read_text().split('\n',1)[1],False)
page('Electronics fastener locations')
d=Drawing(480,315)
d.add(Rect(98,16,230,280,fillColor=colors.HexColor('#F2F3F4'),strokeColor=colors.gray))
d.add(String(100,303,'HEAD HOLE LOCATIONS - looking along X',fontName='Bold',fontSize=11))
for prefix,points in [('C',[(39,-67.5),(-39,-67.5),(0,31.5)]),('S',[(19,1.5),(9.35,-41),(-30,-34),(-30,5)])]:
 for i,(y,z) in enumerate(points,1):
  xx=213+2.5*y;zz=202+2.5*z;d.add(Circle(xx,zz,4,fillColor=colors.black));d.add(String(xx+7,zz+5,f'{prefix}{i}',fontName='Bold',fontSize=13));d.add(String(xx+7,zz-8,f'Y{y:g}, Z{z:g}',fontName='Body',fontSize=8))
d.add(String(342,265,'C1-C3: cap closure',fontName='Bold',fontSize=9));d.add(String(342,248,'M2.5 x8 TAP',fontName='Body',fontSize=9));d.add(String(342,222,'S1-S4: support',fontName='Bold',fontSize=9));d.add(String(342,205,'M2.5 x6 TAP',fontName='Body',fontSize=9))
story.append(d)
para('Coordinate locator, not a shell outline or scale template. Match Y/Z to the head-shell model; the insertion X direction is listed on each connection card.','SmallText')
para('C1-C3: head-cap closure. S1-S4: revised motor support to lower head shell. View and labels match the numbered mechanical steps. Start all mating screws before final hand tightening.')
for r in [r for r in rows if not r.get('servo_ids')]:
 card_start=len(story)
 story.append(Paragraph(fmt(r['component']),styles['Heading2']))
 para(f"{r['id']}: {r['quantity']} x {r['spec']}")
 extra=[]
 if r.get('nut_quantity'):extra.append(f"{r['nut_quantity']} nuts")
 if r.get('washer_quantity'):extra.append(f"{r['washer_quantity']} washers")
 if extra:para('Also fit: '+', '.join(extra)+'.')
 para('Centers [x,y,z] mm: '+json.dumps([[round(v,3) for v in xyz] for xyz in r['hole_centers_mm']])+'. Frame: '+r.get('coordinate_frame','')+'; screw insertion axis: '+str(r['axis'])+'.','SmallText')
 para('Clamped stack (mm): '+json.dumps(r['stack_mm'])+'. Engagement: '+str(r['engagement_mm'])+' mm.','SmallText')
 para('Check [ ] seated [ ] retained [ ] free motion / cable clearance','SmallText')
 card=story[card_start:];story[card_start:]=[KeepTogether(card)]
titles={1:'Right ankle',2:'Right knee',3:'Right hip pitch',4:'Right hip roll',5:'Right hip yaw',6:'Left ankle',7:'Left knee',8:'Left hip pitch',9:'Left hip roll',10:'Left hip yaw',11:'Head pitch',12:'Neck pitch',13:'Head yaw',14:'Head roll',15:'Jaw'}
for sid in range(1,16):
 page(f'Motor {sid:02d} - {titles[sid]}')
 para('Shaft high, connectors low. Front is the active output; rear is mirrored. H = M2 output, C = M2 case, R = M2.6 rear-center. Numbers are screw lengths in mm. W requires a0.5 mm washer.','SmallText')
 rr=[r for r in rows if r.get('servo_ids')==[sid]];d=Drawing(480,205)
 for side,xo,title in [(-1,130,'FRONT / ACTIVE'),(1,345,'REAR / PASSIVE')]:
  d.add(Rect(xo-60,35,120,155,fillColor=colors.HexColor('#F2F3F4'),strokeColor=colors.gray));d.add(Circle(xo,147,37,fillColor=None,strokeColor=colors.lightgrey));d.add(String(xo-57,194,title,fontName='Bold',fontSize=10))
  for r in [v for v in rr if v['side']==side]:
   _,y,z=r['hole_centers_mm'][0];x=xo+4*y*(-1 if side==1 else 1);zz=147+4*z;cat={'horn':'H','case':'C','rear_center':'R'}[r['category']];d.add(Circle(x,zz,2,fillColor=colors.black));d.add(String(x+4,zz+4,cat+str(r['length_mm'])+(' W' if r['washer_mm'] else ''),fontName='Bold',fontSize=10))
 story.append(d)
 para('Exact positions and mating parts','Heading2')
 for r in rr:
  _,y,z=r['hole_centers_mm'][0];front='front' if r['side']==-1 else 'rear';ids=r.get('source_ids');para(f"[ ] {front} {r['category']}: (Y {y:g}, Z {z:g}) mm - {r['spec']}{'; washer0.5 mm' if r['washer_mm'] else ''}. Mates {r['component']}; source part IDs {ids if ids else 'current replacement'}. [{r['id']}]",'SmallText')
 para('Coordinates above use the motor-local frame, not page coordinates. Rear-view Y is mirrored in the diagram. All listed connections have quantity1. Match model ID and side before inserting.','SmallText')
 para('Record [ ] centered [ ] all scheduled screws [ ] no binding [ ] cable slack | Notes __________________','SmallText')
page('Pi physical-pin and fuse checklist')
for name,pins in contract['pi_physical_pins'].items():para('[ ] '+name.replace('_',' ')+' - physical pin(s) '+', '.join(map(str,pins))+'.')
para('Motor branches','Heading2')
for n,ids in enumerate([[1,2],[3,4],[5,10],[6,7],[8,9],[11,12],[13,14],[15]],1):para(f'[ ] F{n}:3 A - motor IDs '+', '.join(map(str,ids))+'.')
para('[ ] F0:10 A motor main. [ ] F9:3 A Pi. [ ] F10:0.5 A audio. [ ] External input:5 A, next to receiver before tether. Grounds are unfused.')
page('Cable endpoint checklist')
for c in contract['connections']:
 if c['id']=='mac_wifi':continue
 story.append(Paragraph(fmt(c['id'].replace('_',' ').title()),styles['Heading2']))
 para(f"[ ] {c['start']} to {c['end']}. {c['medium']}; length: {c['length']}. Termination: {c['termination']}.")
para('Network/control: Pi sensor observations to Mac control/policy. Existing Wi-Fi is the intended link; motor-bus ownership, transport protocol and stop behavior must be implemented and measured before operation.')
page('Wiring and first-power worksheet')
md((P/'ASSEMBLY-WIRING.md').read_text().split('\n',1)[1],False)
page('Source record and assembly sign-off')
para('This manual is generated from ASSEMBLY-STEPS.md, ASSEMBLY-WIRING.md, assembly-fasteners.json, design-contract.json and print-manifest.json in the current redesign folder. Exact measurement reports remain in fastener-audit/. The source preserves129 connection groups including118 individual joint screw positions.')
para('Digital clearance and screw-depth checks support the specified design. Receiving-board identity, printed tolerance, thread grip, clamp torque, cable routing over motion, electrical loading and physical stopping require the recorded first-article checks above.')
for t in ['Mechanical assembly completed by __________ date __________','All15 IDs read back __________ zero/direction record __________','All fasteners and required washers checked __________','Camera live image / IMU axes __________','Power, temperatures and transients recorded __________','Mac/Pi transport and fault-stop tests __________','Open correction items and photo references ______________________________']:para(t)
def footer(c,doc):
 c.setFont('Body',8);c.setFillColor(colors.HexColor('#555555'));c.drawString(42,25,'MicroDuck | Assembly manual | 2026-09-30');c.drawRightString(570,25,str(doc.page))
path=OUT/'MicroDuck_Assembly_Manual.pdf';doc=SimpleDocTemplate(str(path),pagesize=(612,792),rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=44,title='MicroDuck Assembly Manual',author='MicroDuck build');doc.build(story,onFirstPage=footer,onLaterPages=footer)
reader=PdfReader(path);text='\n'.join(p.extract_text() for p in reader.pages)
missing=[r['id'] for r in rows if r['id'] not in text];assert not missing,missing
inputs=[P.parents[1]/'PROJECT-CONTEXT.json',P.parent/'assembly/images/06-servo-map.png',P.parent/'assembly/images/09-leg-detail.png']+[P/n for n in ['ASSEMBLY-STEPS.md','ASSEMBLY-WIRING.md','assembly-fasteners.json','design-contract.json','print-manifest.json','build_assembly_pdf.py','fastener-audit/screw-head-clearance.json','fastener-audit/electronics-head-fastener-locations.png','fastener-audit/motor-fastener-locations.png']]
report={'passed':not missing,'pages':len(reader.pages),'connection_groups':len(rows),'joint_positions':sum(bool(r.get('servo_ids')) for r in rows),'all_connection_ids_in_pdf':not missing,'pdf_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sources':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs},'physical_tests':0}
(OUT/'manual-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
