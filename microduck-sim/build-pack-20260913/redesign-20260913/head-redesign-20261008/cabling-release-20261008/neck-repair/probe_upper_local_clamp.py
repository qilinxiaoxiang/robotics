import json
from pathlib import Path
import short_path_worker as c
c.guard()
import trimesh,manifold3d as mf
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'guide-clips';jaw=g.conv(trimesh.load(D/'flat-ribbon-sweep/jaw_support-split-channel-world.stl',force='mesh'));cap=g.conv(trimesh.load(H/'usb-access/usb-repair/cap-usb-positive-x225-world.stl',force='mesh'));rows=[]
for y,z in [(-22.5,134.5),(-19,134.5)]:
 s=mf.Manifold.cube([5,17,10.4]).translate([23.5,y-8.5,z-5.2]);rs=[]
 for a in range(-25,26,5):
  hits={}
  for k,b in [('jaw',jaw),('cap',cap)]:
   ob=b.translate([-8.1,0,-115.6146]).rotate([-a,0,0]).translate([8.1,0,115.6146]);v=(s^ob).volume()
   if v>1e-8:hits[k]={'v':v,'bounds':list((s^ob).bounding_box())}
  rs.append({'angle':a,'hits':hits})
 rows.append({'y':y,'z':z,'rows':rs})
c.save(O/'upper-local-clamp-probe.json',{'rows':rows});print(json.dumps(rows))
