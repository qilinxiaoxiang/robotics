from pathlib import Path
import cadquery as cq,json,hashlib
D=Path(__file__).resolve().parent;W=D.parents[2];p=W/'leg-ports/header-13-motor-local.step'
s=cq.importers.importStep(str(p)).val();cq.exporters.export(s,str(D/'socket13-local.stl'))
r=[]
for f in s.Faces():
 if f.geomType()=='PLANE' and f.Area()>5:
  b=f.BoundingBox();r.append({'area':f.Area(),'center':f.Center().toTuple(),'normal':f.normalAt().toTuple(),'bounds':[b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax]})
(D/'socket13-keyed-faces.json').write_text(json.dumps({'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'faces':r},indent=2));print(r)
