from pathlib import Path
import cadquery as cq,json,hashlib
D=Path(__file__).resolve().parent;rows=[]
for name,count in [('xl330-registered-motor-local.step',12),('header-13-motor-local.step',1),('header-14-motor-local.step',1)]:
 p=D/name;s=cq.importers.importStep(str(p)).val();ss=s.Solids();b=s.BoundingBox();assert len(ss)==count and all(t.isValid() and t.Volume()>0 for t in ss)
 rows.append({'file':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'solids':len(ss),'allValid':True,'bounds':[[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]})
(D/'native-registration-readback.json').write_text(json.dumps({'readback':rows},indent=2))
a=rows[1]['bounds'];b=rows[2]['bounds'];assert abs(a[1][0]-8.4)<1e-6 and abs(b[1][0]-8.4)<1e-6
out={'passed':True,'readback':rows};(D/'native-registration-readback.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
