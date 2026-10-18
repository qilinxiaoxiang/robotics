"""Low-memory OCP-only BREP envelopes; no full robot or CadQuery import."""
from pathlib import Path
import json,hashlib
from OCP.gp import gp_Pnt,gp_Dir,gp_Ax2
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.STEPControl import STEPControl_Writer,STEPControl_Reader,STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
from OCP.TCollection import TCollection_HAsciiString
D=Path(__file__).resolve().parent;R=D.parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((D/'layout-report.json').read_text());parts={p['key']:p for p in json.loads((R/'leg-guide-20261006/full-build-data.json').read_text())['parts']}
def box(b):return BRepPrimAPI_MakeBox(gp_Pnt(*b[0]),gp_Pnt(*b[1])).Shape()
rows=[]
for l in r['layouts']:
 pieces=[('PB1033MI_ENVELOPE',box(l['bankBoundsMm'])),('RECEIVING_1MM_NOT_STRUCTURE',box(l['bankReceivingBoundsMm']))]
 for i,p in enumerate(l['ports']):pieces.append((f'PORT_{i}_25MM_ASSUMPTION',box(p['boundsMm'])))
 for key in ['motor5','motor10','motor4','motor9','hip','right_hip','thigh','right_thigh','lower','right_lower','foot','right_foot','torso_base','power_support','regulator','regulator_insert','shell_left','shell_right']:
  b=[q.copy() for q in parts[key]['bounds']];side=-1 if key in ['motor5','motor4','right_hip','right_thigh','right_lower','right_foot'] else 1 if key in ['motor10','motor9','hip','thigh','lower','foot'] else 0
  for v in b:v[1]+=side*l['legShiftPerSideMm']
  pieces.append(('BBOX_'+key+('_SHIFTED' if side else '_OLD_CENTRAL'),box(b)))
 for sign in [-1,1]:pieces.append(('YAW_AXIS_LEFT' if sign>0 else 'YAW_AXIS_RIGHT',BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(6,sign*l['newYawAxisSpacingMm']/2,-13),gp_Dir(0,0,1)),.8,38).Shape()))
 w=STEPControl_Writer()
 for name,s in pieces:
  assert BRepCheck_Analyzer(s).IsValid();assert w.Transfer(s,STEPControl_AsIs)==IFSelect_RetDone
 model=w.Model();products=[]
 for i in range(1,model.NbEntities()+1):
  e=model.Value(i)
  if e.DynamicType().Name()=='StepBasic_Product':products.append(e)
 if len(products)==len(pieces):
  for e,(name,s) in zip(products,pieces):e.SetName(TCollection_HAsciiString(name));e.SetId(TCollection_HAsciiString(name))
 path=D/f'central-battery-{l["id"]}-concept.step';assert w.Write(str(path))==IFSelect_RetDone
 reader=STEPControl_Reader();assert reader.ReadFile(str(path))==IFSelect_RetDone;reader.TransferRoots();assert reader.NbShapes()==len(pieces)
 assert all(BRepCheck_Analyzer(reader.Shape(i)).IsValid() for i in range(1,reader.NbShapes()+1))
 rows.append({'layout':l['id'],'path':str(path),'sha256':sha(path),'readbackValidShapes':reader.NbShapes(),'namesInTransferOrder':[x[0] for x in pieces],'namedProducts':len(products),'notPrintable':True,'sourceReportSha256':sha(D/'layout-report.json')})
 del w,reader,model,products,pieces
(D/'step-export-receipt.json').write_text(json.dumps({'outputs':rows,'generatorSha256':sha(Path(__file__)),'scope':'Valid BREP envelope boxes and axis cylinders only, not original detailed part geometry or robot collision acceptance.'},indent=2)+'\n');print('EXPORTED',[(x['layout'],x['readbackValidShapes'])for x in rows])
