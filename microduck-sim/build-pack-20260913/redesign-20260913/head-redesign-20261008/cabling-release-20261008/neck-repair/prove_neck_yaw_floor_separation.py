"""Stdlib exact vertex-plane bound in the shared head-pitch frame."""
import json,struct,math
from pathlib import Path
import segmented_yaw_neck_worker as w
w.current();man=w.H/'camera-ribbon-repair/positive-x225/candidate-manifest.json';d=json.loads(man.read_text());src=w.H/d['replacementMeshes']['head_bottom'];b=src.read_bytes();n=struct.unpack_from('<I',b,80)[0]
vertices=[]
if len(b)==84+50*n:
 for i in range(n):vertices.extend(struct.unpack_from('<fff',b,84+50*i+12+12*j) for j in range(3))
else:
 vertices=[tuple(map(float,line.split()[1:])) for line in b.decode().splitlines() if line.strip().startswith('vertex ')]
 assert vertices and len(vertices)%3==0
# Valid current source mesh was independently loaded/closed by the neutral candidate checker.
proof=w.D/'segmented-yaw-below/candidate-pairs/-1__head_bottom.json';pr=json.loads(proof.read_text());assert pr['sourceEvidence']['watertight'] and pr['sourceEvidence']['positiveVolume'] and pr['sourceEvidence']['sourceSha256']==w.sha(src)
base=json.loads(w.BASE.read_text());rows=[];zs={};yz=set((v[1],v[2]) for v in vertices)
for i,row in enumerate(base['samples']):
 q={k:row['jointDegrees'].get(k,0) for k in ['head_yaw','head_roll']};angle=q['head_roll'];a=math.radians(angle)
 if angle not in zs:zs[angle]=min(115.6146-math.sin(a)*y+math.cos(a)*(z-115.6146) for y,z in yz)
 zmin=zs[angle];rows.append({'pose':i,'nativeBlocked':bool(row['nativeShellOriginalBottomIntersectionsMm3']),'minimumHeadBottomZInHeadPitchFrameMm':zmin,'maximumYawRoundReceiverZInSameFrameMm':68.5,'separationPlaneGapMm':zmin-68.5})
r={'headBottomForThisLocalSegmentClear':all(x['separationPlaneGapMm']>.5 for x in rows),'wholeHarnessAccepted':False,'expectedPoses':229,'completedPoses':len(rows),'nativeClearMinimumPlaneGapMm':min(x['separationPlaneGapMm'] for x in rows if not x['nativeBlocked']),'all229MinimumPlaneGapMm':min(x['separationPlaneGapMm'] for x in rows),'method':'Common neck_pitch/head_pitch transform cancels; compare complete source triangle vertices transformed by remaining yaw/roll with whole analytic cable receiving upper Z65+3.5. Every planar triangle lies within its vertex-coordinate bounds. No mesh boolean approximation, no hole/cut and no excluded screw/bearing area. Original43 native-rigid-blocked statuses retained, not mechanically accepted.','rows':rows,'sourceHashes':{str(p):w.sha(p) for p in [Path(__file__),src,man,proof,w.OUT/'plan.json',w.BASE,w.D/'prepare_single_candidate.py']}};w.save(w.OUT/'headbottom-plane-separation.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ['rows','sourceHashes']}))
