"""Finite yaw/roll wire coverage, endpoint true-circle distance >=0.5mm."""
import argparse,json,math
from pathlib import Path
import short_path_worker as c
c.guard()
import trimesh,manifold3d as mf
import flat_yaw_geometry as g
from segment_capsule_clearance import check
D=Path(__file__).resolve().parent;O=D/'flat-ribbon-sweep';ap=argparse.ArgumentParser();ap.add_argument('--part',required=True);ap.add_argument('--start',type=int,default=0);ap.add_argument('--count',type=int,default=10);a=ap.parse_args();p=O/(a.part+'-split-channel-world.stl');mesh=trimesh.load(p,force='mesh');assert mesh.is_watertight and mesh.is_volume;body=g.conv(mesh);r=json.loads((O/'head_bottom.json').read_text());expected=r['expectedUniqueHeadRelativePoses'][a.start:a.start+a.count];rows=[];evidence={'watertight':True,'positiveVolume':True,'sourceSha256':c.sha(p)}
for pose in expected:
 wires=[]
 for w in g.specs_for_pose(pose):
  hit=body^g.tube(w['points'],w['receivingODMm']/2+.02);assert hit.status()==mf.Error.NoError;ports=[]
  for pts in [w['points'][:2],w['points'][-2:]]:
   z=check(pts,w['receivingODMm']/2+.5,.0035,body,source_evidence=evidence,search_extra=.7);gap=z['minimumGapLowerBoundMm']-w['receivingODMm']/2-.0035-.001;ports.append(gap)
  wires.append({'wire':w['key'],'inflatedSweepIntersectionMm3':hit.volume(),'portSurfaceGapLowerBoundsMm':ports})
 row={'pose':pose,'passed':all(w['inflatedSweepIntersectionMm3']<1e-8 and min(w['portSurfaceGapLowerBoundsMm'])>=.5 for w in wires),'minimumPortGapLowerBoundMm':min(min(w['portSurfaceGapLowerBoundsMm']) for w in wires),'wires':wires};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='wires'}),flush=True)
c.save(O/f'{a.part}-split-clearance-{a.start}.json',{'passed':all(r['passed'] for r in rows),'expectedPoses':expected,'completedPoses':[r['pose'] for r in rows],'rows':rows,'scope':'79 source native-clear unique head-relative sampled yaw/roll poses; this batch only. Ports use exact round-sweep distance lower bounds; interior inflated circumscribed mesh test. No full harness or arbitrary joint continuum claim.','sourceHashes':{str(f):c.sha(f) for f in [Path(__file__),p,D/'flat_yaw_geometry.py',D/'segment_capsule_clearance.py',O/'head_bottom.json']}})
