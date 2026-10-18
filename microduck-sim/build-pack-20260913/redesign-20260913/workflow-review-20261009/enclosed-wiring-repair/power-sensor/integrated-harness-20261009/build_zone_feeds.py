from pathlib import Path
import ast,json,hashlib,math
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parents[1]/'motor-wires'
from wire_geometry import primitives,sample,tube,solid,self_check
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=[]
for side,sy,out in [('left',-9.5,-1),('right',25.5,1)]:
 for net,x in [('5V',-3.),('GND',-.5)]:
  targetY=-7 if net=='5V' else 7
  front=13.
  lane=(-14 if net=='5V' else -11.5) if side=='left' else (12 if net=='5V' else 14.5)
  top=32.5 if net=='5V' else 38.1
  tx=-10 if side=='left' else 1
  if net=='GND':tx=-3 if side=='left' else -10
  pts=[[x,sy,22],[x,sy,24.5],[x,lane,24.5],[front,lane,24.5],[front,lane,top],[tx,lane,top]]
  approachY=(targetY-5 if side=='left' else targetY+5)
  endx=-3 if side=='right' and net=='5V' else tx
  pts += ([[endx,targetY,35.5]] if side=='left' and net=='5V' else [[tx,approachY,top],[endx,targetY,35.5]])
  if side=='left' and net=='GND':pts=[[x,sy,22],[x,sy,24.5],[15,sy,24.5],[15,sy,top],[tx,sy,top],[tx,2,top],[tx,targetY,35.5]]
  pr=primitives(pts);q,t=sample(pr);selftest=self_check(pr,q);mesh=tube(q,t);assert mesh.is_volume
  f=D/f'zone-{side}-{net.lower()}-world.stl';mesh.export(f)
  rows.append({'key':f'zone_{side}_{net.lower()}','net':net,'from':'paired distribution splice','to':f'motor {5 if side=="left" else 10} incoming socket13 pin{2 if net=="5V" else 1}','file':str(f),'sha256':sha(f),'gaugeAWG':22,'receivingDiameterMm':1.5,'routeDirection':'motor to splice','primitives':pr,'controlPoints':pts,'lengthMm':sum(x['lengthMm']for x in pr),'boundsMm':mesh.bounds.tolist(),'selfClearance':selftest})
(D/'zone-feeds.json').write_text(json.dumps({'parts':rows,'sourceHashes':{str(Path(__file__)):sha(__file__),str(D/'wire_geometry.py'):sha(D/'wire_geometry.py'),str(M/'local_route.py'):sha(M/'local_route.py')},'status':'CANDIDATE_NOT_YET_CHECKED'},indent=2)+'\n')
print([(r['key'],r['lengthMm'])for r in rows])
