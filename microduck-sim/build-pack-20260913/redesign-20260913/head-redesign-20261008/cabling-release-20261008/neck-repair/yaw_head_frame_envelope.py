"""Pure stdlib: actual sampled yaw-loop sweep in head-fixed coordinates."""
import json,math
from pathlib import Path
import segmented_yaw_forward_worker as w
from prepare_single_candidate import JOINTS,rot,add,sub
w.current();rows=[];allp=[]
def head_inverse(p,q):
 for name,origin,axis in JOINTS:p=add(origin,rot(sub(p,origin),axis,-math.radians(q.get(name,0))))
 return p
for i in range(229):
 row,g=w.route(i);pts=[head_inverse(p,row['jointDegrees']) for p in g['points']];radii=[math.hypot(p[0]-26,p[1]) for p in pts];rows.append({'pose':i,'nativeBlocked':bool(row['nativeShellOriginalBottomIntersectionsMm3']),'headFrameCenterlineBounds':[list(map(min,zip(*pts))),list(map(max,zip(*pts)))],'radialToYawAxisRangeMm':[min(radii),max(radii)]})
 if not rows[-1]['nativeBlocked']:allp+=pts
r={'accepted':False,'sourceCut':False,'nativeClearSweepReceivingAABB':[[v-3.5 for v in map(min,zip(*allp))],[v+3.5 for v in map(max,zip(*allp))]],'radialToNeutralYawAxisRangeReceivingMm':[min(math.hypot(p[0]-26,p[1]) for p in allp)-3.5,max(math.hypot(p[0]-26,p[1]) for p in allp)+3.5],'warning':'This AABB/annular envelope is only a conservative extent diagnostic, not a subtraction tool or proposal to remove all material inside it. Full yaw moves the lower arc around most of the neck opening, and roll changes height. A neutral-only slot is insufficient. Must preserve floor continuity, bearing seats, jaw supports and every required fastener tool corridor.','rows':rows,'sourceHashes':{str(p):w.sha(p) for p in [Path(__file__),w.OUT/'plan.json',w.BASE,w.D/'segmented_yaw_forward_worker.py',w.D/'prepare_single_candidate.py']}};w.save(w.OUT/'head-frame-envelope.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ['rows','sourceHashes']}))
