import json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh,manifold3d as mf
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'flat-ribbon-sweep';ap=O/'arch2-bridge-world.stl';jp=O/'jaw_support-flat-channel-world.stl';a=g.conv(trimesh.load(ap,force='mesh'));b=g.conv(trimesh.load(jp,force='mesh'));hit=a^b;guide=json.loads((H.parent/'leg-guide-20261006/full-build-data.json').read_text());rows=[]
for x in guide['screws']:
 if x.get('groupId')!='motor_support_frame':continue
 cx,cy,cz=x['world_center_mm'];zone=mf.Manifold.cylinder(8,2.6,2.6,64).translate([cx,cy,cz-6]);rows.append({'id':x['id'],'intersectionMm3':(hit^zone).volume()})
for k in ['head_roll_ring_a','head_roll_ring_b']:
 p=next(p for p in guide['parts'] if p['key']==k);lo,hi=np.array(p['bounds']);lo-=2;hi+=2;zone=mf.Manifold.cube((hi-lo).tolist()).translate(lo.tolist());rows.append({'id':k,'boxPlus2IntersectionMm3':(hit^zone).volume()})
r={'accepted':False,'jawMaterialNeedReliefMm3':hit.volume(),'jawReliefBounds':list(hit.bounding_box()),'zones':rows,'sourceHashes':{str(p):c.sha(p) for p in [ap,jp,Path(__file__)]}};c.save(O/'arch-mechanical-zones.json',r);print(json.dumps(r))
