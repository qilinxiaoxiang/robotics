import json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'flat-ribbon-sweep';r=json.loads((O/'head_bottom.json').read_text());p=O/'head_bottom.npz';assert c.sha(p)==r['stateSha256'];z=np.load(p);s=mf.Manifold(mf.Mesh64(z['vertices'],z['faces']));parts=sorted(s.decompose(),key=lambda x:x.volume(),reverse=True);guide=json.loads((H.parent/'leg-guide-20261006/full-build-data.json').read_text());rows=[]
for i,s in enumerate(parts):
 if s.volume()<.001:continue
 guarded=[]
 for q in guide['screws']:
  if q.get('groupId')!='motor_support_frame':continue
  x,y,z=q['world_center_mm'];guard=mf.Manifold.cylinder(8,2.6,2.6,48).translate([x,y,z-6]);guarded.append({'id':q['id'],'materialMm3':(s^guard).volume()})
 rows.append({'component':i,'volumeMm3':s.volume(),'bounds':list(s.bounding_box()),'protectedThreadMaterial':guarded})
out={'scope':'Component diagnosis before any scrap removal','rows':rows,'sourceHashes':{str(p):c.sha(p),str(O/'head_bottom.json'):c.sha(O/'head_bottom.json')}};c.save(O/'head-components.json',out);print(json.dumps(out))
