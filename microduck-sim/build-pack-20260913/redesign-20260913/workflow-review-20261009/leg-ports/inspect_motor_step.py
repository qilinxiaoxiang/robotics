from pathlib import Path
import cadquery as cq,json,hashlib
D=Path(__file__).resolve().parent;R=D.parents[1];P=R/'fastener-audit/sources/X330_3d.stp'
s=cq.importers.importStep(str(P)).val()
def bbox(s):
 b=s.BoundingBox();return [[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]
rows=[]
for i,a in enumerate(s.Solids()):
 row={'index':i,'volume':a.Volume(),'valid':a.isValid(),'bounds':bbox(a),'faceCount':len(a.Faces())}
 if i>=12:
  row['faces']=[{'index':j,'type':f.geomType(),'area':f.Area(),'center':f.Center().toTuple(),'bounds':bbox(f),'normal':f.normalAt().toTuple() if f.geomType()=='PLANE' else None} for j,f in enumerate(a.Faces())]
 rows.append(row)
o={'source':str(P),'sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'solids':rows};(D/'motor-step-solids.json').write_text(json.dumps(o,indent=2));print(json.dumps([{k:v for k,v in r.items() if k!='faces'} for r in rows],indent=2))
