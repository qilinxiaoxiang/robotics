from pathlib import Path
import cadquery as cq,json,hashlib
from OCP.gp import gp_Trsf
D=Path(__file__).resolve().parent;O=D/'bno-native-solids';O.mkdir(exist_ok=True)
source=D/'sources/bno085.step';shape=cq.importers.importStep(str(source)).val();b=shape.BoundingBox();print('Source bounds',[b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax],flush=True)
assert abs(b.xmin)<.01 and abs(b.ymin)<.01 and abs(b.zmin)<.01 and abs(b.xmax-25.4)<.01
T=cq.Matrix([[0,0,-1,-53],[1,0,0,-12.7],[0,-1,0,26.43],[0,0,0,1]])
nativeT=gp_Trsf();nativeT.SetValues(0,0,-1,-53,1,0,0,-12.7,0,-1,0,26.43)
loc=cq.Location(nativeT)
rows=[]
for i,s in enumerate(shape.Solids()):
 assert s.isValid();q=s.moved(loc);p=O/f'{i:02d}.stl';cq.exporters.export(q,str(p),tolerance=.01,angularTolerance=.1);b=q.BoundingBox()
 print('solid',i,flush=True)
 rows.append({'index':i,'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sourceVolumeMm3':s.Volume(),'boundsMm':[[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]})
r={'source':str(source),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'generatorSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'solidCount':len(rows),'solids':rows,'sourceToWorld':[[0,0,-1,-53],[1,0,0,-12.7],[0,-1,0,26.43],[0,0,0,1]]}
(O/'manifest.json').write_text(json.dumps(r,indent=2)+'\n');print('Exported',len(rows),flush=True)
