import json,math
from pathlib import Path
import short_path_worker as c
c.guard()
import flat_yaw_geometry as g
import numpy as np
from scipy.spatial import cKDTree
from check_local_pair_stdlib import dist
D=Path(__file__).resolve().parent;out=[]
for pose in [-1,68,136]:
 specs=g.specs_for_pose(pose);segments=[];mids=[];radii=[];ids=[]
 for i,s in enumerate(specs):
  p=np.array(s['points'])
  for j,(a,b) in enumerate(zip(p,p[1:])):segments.append((a.tolist(),b.tolist()));mids.append((a+b)/2);radii.append(s['receivingODMm']/2);ids.append((i,j))
 tree=cKDTree(mids);pairs=tree.query_pairs(2.4);minimum=999;fail=[];checked=0
 for a,b in pairs:
  if ids[a][0]==ids[b][0]:continue
  d=dist(*segments[a],*segments[b]);gap=d-radii[a]-radii[b]-.0065;checked+=1
  if gap<minimum:minimum=gap
  if gap<0:fail.append({'a':ids[a],'b':ids[b],'gapLowerBoundMm':gap})
 row={'pose':pose,'crossWirePairsChecked':checked,'minimumGapLowerBoundMm':minimum,'failed':fail[:20],'failureCount':len(fail),'passed':not fail};out.append(row);print(json.dumps(row),flush=True)
r={'accepted':False,'crossWireTestPassed':all(x['passed'] for x in out),'poses':out,'scope':'Three poses only; centerline chord errors bounded .00325 per wire. KD midpoint radius2.4 covers OD1.8 plus .35 segment lengths. Same-wire regularity follows separate analytic arc/U geometry, not counted here. No full-route acceptance.','sourceHashes':{str(p):c.sha(p) for p in [Path(__file__),D/'flat_yaw_geometry.py',D/'rolling_loop_math.py',D/'check_local_pair_stdlib.py']}};c.save(D/'flat-yaw-channel/self-three-poses.json',r)
