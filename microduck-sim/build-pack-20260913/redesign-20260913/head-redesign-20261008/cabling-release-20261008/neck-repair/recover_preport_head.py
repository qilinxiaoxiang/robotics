"""Inspect retained pre-port exported head. Do not overwrite any current state."""
import json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh,manifold3d as mf
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;O=D/'flat-ribbon-sweep';p=O/'head_bottom-flat-channel-world.stl';m=trimesh.load(p,force='mesh');assert m.is_watertight and m.is_volume and len(m.split())==1;b=g.conv(m);rows=[]
for pose in [-1,68,136,137,147]:
 details=[]
 for w in g.specs_for_pose(pose):
  wire=g.tube(w['points'],w['receivingODMm']/2+.02);hit=b^wire;gap=wire.min_gap(b,.6) if hit.volume()<1e-8 else 0;details.append({'wire':w['key'],'overlapMm3':hit.volume(),'gapMm':gap})
 row={'pose':pose,'details':details,'minGapMm':min(x['gapMm'] for x in details)};rows.append(row);print(json.dumps(row),flush=True)
r={'accepted':False,'rows':rows,'sourceHashes':{str(p):c.sha(p),str(Path(__file__)):c.sha(Path(__file__))}};c.save(O/'preport-head-clearance.json',r)
