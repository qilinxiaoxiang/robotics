import json
from pathlib import Path
import short_path_worker as c
c.guard()
import trimesh,manifold3d as mf
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'guide-clips';jaw=g.conv(trimesh.load(D/'flat-ribbon-sweep/jaw_support-split-channel-world.stl',force='mesh'));cap=g.conv(trimesh.load(H/'usb-access/usb-repair/cap-usb-positive-x225-world.stl',force='mesh'));rows=[]
for y,z in [(-16,131.2),(-16,133.2),(-18,133.2),(-16,135.2)]:
 s=mf.Manifold.cube([24,2.4,2]).translate([33,y-1.2,z]);rs=[]
 for a in range(-25,26,5):
  hits={}
  for k,b in [('jaw',jaw),('cap',cap)]:
   ob=b.translate([-8.1,0,-115.6146]).rotate([-a,0,0]).translate([8.1,0,115.6146]);v=(s^ob).volume()
   if v>1e-8:hits[k]={'v':v,'bounds':list((s^ob).bounding_box())}
  rs.append({'angle':a,'hits':hits})
 rows.append({'y':y,'z':z,'rows':rs})
c.save(O/'upper-corridor-probe.json',{'rows':rows});print(json.dumps(rows))
