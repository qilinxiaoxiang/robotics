"""One final exported body and bounded number of actual11-wire poses."""
import argparse,json
from pathlib import Path
import short_path_worker as c
c.guard()
import flat_yaw_geometry as g
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;O=D/'flat-ribbon-sweep';a=argparse.ArgumentParser();a.add_argument('--part',required=True);a.add_argument('--start',type=int,required=True);a.add_argument('--count',type=int,default=10);o=a.parse_args();ep=O/f'{o.part}-export.json';e=json.loads(ep.read_text());p=Path(e['worldMesh']);assert c.sha(p)==e['worldSha256'];body=g.conv(trimesh.load(p,force='mesh'));meta=json.loads((O/f'{o.part}.json').read_text());poses=meta['expectedUniqueHeadRelativePoses'];rows=[]
for i in poses[o.start:o.start+o.count]:
 details=[]
 for s in g.specs_for_pose(i):
  wire=g.tube(s['points'],s['receivingODMm']/2+.02);hit=wire^body;assert hit.status()==mf.Error.NoError;vol=hit.volume();gap=wire.min_gap(body,.6) if vol<1e-8 else 0;details.append({'wire':s['key'],'overlapMm3':vol,'gapLowerBoundMm':gap,'distanceCappedAtMm':.6})
 row={'pose':i,'passed':all(x['overlapMm3']<1e-8 for x in details),'minimumGapLowerBoundMm':min(x['gapLowerBoundMm'] for x in details),'wires':details};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='wires'}),flush=True)
r={'passed':all(x['passed'] for x in rows),'part':o.part,'start':o.start,'expectedPoses':poses[o.start:o.start+o.count],'completedPoses':[x['pose'] for x in rows],'receivingInflationMm':.02,'geometryNote':'Each physical OD unchanged; additional.02mm radial plus existing.005/cos(pi/16) circumscribed mesh allowance; sampled polylines step<=.35 with minimum R4.75. Exported actual channel body read back watertight/positive before Boolean.','rows':rows,'sourceHashes':{str(f):c.sha(f) for f in [Path(__file__),ep,p,D/'flat_yaw_geometry.py',D/'rolling_loop_math.py']}};c.save(O/f'{o.part}-clearance-{o.start}.json',r)
