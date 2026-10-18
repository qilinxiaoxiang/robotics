import json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;O=D/'flat-ribbon-sweep';a=g.conv(trimesh.load(O/'arch3-bridge-world.stl',force='mesh'));hits=[]
for pose in range(137,148):
 for w in g.specs_for_pose(pose):
  hit=a^g.tube(w['points'],w['receivingODMm']/2+.02)
  if hit.volume()>1e-8:hits.append({'pose':pose,'wire':w['key'],'volumeMm3':hit.volume(),'bounds':list(hit.bounding_box())})
print(json.dumps(hits))
r=json.loads((O/'head_bottom.json').read_text());ranges=[]
for i in r['expectedUniqueHeadRelativePoses']:
 for s in g.specs_for_pose(i):
  rr=s['receivingODMm']/2+.5;pts=[p[2]+rr for p in s['points'] if 48-rr<=p[0]<=55+rr and 12-rr<=p[1]<=18+rr]
  if pts:ranges.append({'pose':i,'wire':s['key'],'maxZReceiving':max(pts)})
out={'hits':hits,'bridgeCrossingHighestReceivingZ':sorted(ranges,key=lambda x:-x['maxZReceiving'])[:6]};c.save(O/'arch3-collision-diagnosis.json',out);print(json.dumps(out['bridgeCrossingHighestReceivingZ']))
