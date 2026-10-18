from pathlib import Path
import json,hashlib
from OCP.gp import gp_Pnt
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.STEPControl import STEPControl_Writer,STEPControl_Reader,STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
from OCP.TCollection import TCollection_HAsciiString
D=Path(__file__).resolve().parent;s=json.loads((D/'central-bridge-primitives.json').read_text());w=STEPControl_Writer();pieces=s['primitiveSolids']+[dict(s['batterySolid'],key='BATTERY_LOWERED8_ENVELOPE')]
for p in pieces:
 shape=BRepPrimAPI_MakeBox(gp_Pnt(*p['originMinMm']),*p['dimensionsMm']).Shape();assert BRepCheck_Analyzer(shape).IsValid();assert w.Transfer(shape,STEPControl_AsIs)==IFSelect_RetDone
model=w.Model();products=[model.Value(i)for i in range(1,model.NbEntities()+1)if model.Value(i).DynamicType().Name()=='StepBasic_Product'];assert len(products)==len(pieces)
for e,p in zip(products,pieces):e.SetName(TCollection_HAsciiString(p['key']));e.SetId(TCollection_HAsciiString(p['key']))
p=D/'C-lowered8-loadpath-skeleton.step';assert w.Write(str(p))==IFSelect_RetDone;r=STEPControl_Reader();assert r.ReadFile(str(p))==IFSelect_RetDone;r.TransferRoots();assert r.NbShapes()==len(pieces);assert all(BRepCheck_Analyzer(r.Shape(i)).IsValid()for i in range(1,r.NbShapes()+1));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();(D/'skeleton-step-receipt.json').write_text(json.dumps({'path':str(p),'sha256':sha(p),'readbackValidShapes':r.NbShapes(),'scope':'Nine analytic load-path box primitives and nominal battery, NOT finished manufacturing geometry. Real current robot remains a separately sourced mesh reference.','inputSha256':sha(D/'central-bridge-primitives.json'),'scriptSha256':sha(Path(__file__))},indent=2)+'\n');print('10 valid BREP primitives read back')
