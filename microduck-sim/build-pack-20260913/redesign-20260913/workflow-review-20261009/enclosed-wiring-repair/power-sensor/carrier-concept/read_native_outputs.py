from pathlib import Path
import cadquery as cq,json,hashlib,gc
D=Path(__file__).resolve().parent
rows=[]
for p in [D/'carrier-additions-world.step']+sorted(D.glob('*-exit.step')):
 s=cq.importers.importStep(str(p));vals=s.solids().vals();assert vals and all(q.isValid() and q.Volume()>0 for q in vals);b=s.val().BoundingBox();rows.append({'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'nativeSolids':len(vals),'nativeVolumeMm3':sum(q.Volume()for q in vals),'boundsMm':[[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]});del s,vals;gc.collect()
board=cq.Workplane('XY').box(30,26,8).translate((-25,0,-46));cq.exporters.export(board,str(D/'dfr1202-receiving-world.step'))
(D/'native-output-readback.json').write_text(json.dumps({'scope':'Native STEP export/readback only; geometric fit bound separately.','rows':rows,'passed':len(rows)==6},indent=2));print('read',len(rows),'valid native STEP files')
