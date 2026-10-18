import json
from pathlib import Path
import short_path_worker as c
c.guard()
import trimesh,numpy as np,manifold3d as mf
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;O=D/'flat-ribbon-sweep';p=O/'jaw_support-flat-channel-world.stl';j=g.conv(trimesh.load(p,force='mesh'));rows=[]
for z in [110.8,111.52,111.8,112.2,112.8,113.3]:
 cs=j.slice(z); poly=cs.to_polygons();rows.append({'z':z,'polygons':[[[round(float(x),4),round(float(y),4)] for x,y in a] for a in poly if any(44<x<55 and 4<y<15 for x,y in a)]})
c.save(O/'carrier-key-sections.json',{'source':str(p),'hash':c.sha(p),'rows':rows});print(json.dumps(rows))
