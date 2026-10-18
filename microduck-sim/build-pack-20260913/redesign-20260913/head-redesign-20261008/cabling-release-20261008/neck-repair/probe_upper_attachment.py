import json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh,manifold3d as mf
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;O=D/'guide-clips';jaw=g.conv(trimesh.load(D/'flat-ribbon-sweep/jaw_support-split-channel-world.stl',force='mesh'));rows=[]
for h in [2,1]:
 for x in [18,34]:
  ear=mf.Manifold.cylinder(h,2.4,2.4,48).translate([x,-22.5,129.1145997])-mf.Manifold.cylinder(h+.2,1.1,1.1,32).translate([x,-22.5,129.0145997]);r=[]
  for a in range(-25,26,5):
   j=jaw.translate([-8.1,0,-115.6146]).rotate([-a,0,0]).translate([8.1,0,115.6146]);v=ear^j;r.append({'angle':a,'volume':v.volume(),'bounds':list(v.bounding_box()) if v.volume()>1e-8 else None})
  rows.append({'x':x,'h':h,'rows':r})
c.save(O/'upper-attachment-probe.json',{'rows':rows});print(json.dumps(rows))
