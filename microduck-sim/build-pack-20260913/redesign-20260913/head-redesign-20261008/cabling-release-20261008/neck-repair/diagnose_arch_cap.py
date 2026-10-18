import json
from pathlib import Path
import short_path_worker as c
c.guard()
import trimesh
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'flat-ribbon-sweep';ap=O/'arch4-bridge-world.stl';a=g.conv(trimesh.load(ap,force='mesh'));rows=[]
for name,p in [('current',H/'usb-access/usb-repair/cap-usb-positive-x225-world.stl'),('native',H/'curved-head/community-curved-head-world.stl')]:
 m=trimesh.load(p,force='mesh');b=g.conv(m);hit=a^b;rows.append({'source':name,'path':str(p),'sha256':c.sha(p),'overlapMm3':hit.volume(),'bounds':list(hit.bounding_box()) if hit.volume()>1e-8 else None})
r={'accepted':False,'rows':rows,'bridgeHash':c.sha(ap)};c.save(O/'arch4-cap-contact.json',r);print(json.dumps(r))
