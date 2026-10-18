"""Preserve both structural bodies; inspect retained screw and bearing interfaces."""
import json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh,manifold3d as mf
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'flat-ribbon-sweep';sp=O/'head_bottom.npz';rp=O/'head_bottom.json';r=json.loads(rp.read_text());assert c.sha(sp)==r['stateSha256'];z=np.load(sp);s=mf.Manifold(mf.Mesh64(z['vertices'],z['faces']));cs=sorted(s.decompose(),key=lambda x:x.volume(),reverse=True);data=H.parent/'leg-guide-20261006/full-build-data.json';guide=json.loads(data.read_text());jp=O/'jaw_support-flat-channel-world.stl';jaw=g.conv(trimesh.load(jp,force='mesh'));rows=[]
for i,name in [(0,'head-bottom-main'),(1,'head-roll-bearing-carrier')]:
 b=cs[i];entry={'name':name,'volumeMm3':b.volume(),'bounds':list(b.bounding_box()),'contactWithCurrentJawMm3':(b^jaw).volume(),'mountingInterfaces':[]}
 for sc in guide['screws']:
  if sc.get('groupId')!='motor_support_frame':continue
  x,y,z=sc['world_center_mm'];zone=mf.Manifold.cylinder(12,3.2,3.2,64).translate([x,y,103]);v=b^zone
  if v.volume()>1e-7:entry['mountingInterfaces'].append({'id':sc['id'],'sourceScrewCenter':sc['world_center_mm'],'localMaterialMm3':v.volume(),'bounds':list(v.bounding_box())})
 for key in ['head_roll_ring_a','head_roll_ring_b']:
  p=next(p for p in guide['parts'] if p['key']==key);lo,hi=np.array(p['bounds']);lo-=2;hi+=2;v=b^mf.Manifold.cube((hi-lo).tolist()).translate(lo.tolist());entry[key+'SupportMaterialMm3']=v.volume()
 rows.append(entry)
out={'accepted':False,'separateStructuralPartsNotScrap':True,'parts':rows,'droppedParts':False,'sourceHashes':{str(p):c.sha(p) for p in [Path(__file__),sp,rp,data,jp]}};c.save(O/'split-carrier-interfaces.json',out);print(json.dumps(out))
