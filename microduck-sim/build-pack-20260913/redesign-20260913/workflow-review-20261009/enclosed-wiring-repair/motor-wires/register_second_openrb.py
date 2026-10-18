"""Register second real EH socket using saved source pin-face vertices, not board bounds."""
from pathlib import Path
import json,hashlib,math
D=Path(__file__).parent;OLD=D.parents[1]/'roof-wiring-stage/motor-wires'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
probe=json.loads((OLD/'openrb-port-probe.json').read_text());first=json.loads((OLD/'openrb-registered-port.json').read_text());a=probe['along'];n=probe['normal'];c=probe['components']['110'];v=[p for p in c['verts']if abs(p[1]+12.010000228881836)<1e-5 and 140.3<p[2]<141.2];v.sort();assert len(v)==12
pins=[]
for i in range(3):
 ps=v[i*4:(i+1)*4];lo=[min(p[k]for p in ps)for k in range(3)];hi=[max(p[k]for p in ps)for k in range(3)];center=[sum(p[k]for p in ps)/4 for k in range(3)]
 assert abs(hi[0]-lo[0]-.6)<3e-5 and abs(hi[2]-lo[2]-.6)<3e-5
 pins.append({'sourceFaceVerticesBoardRotatedBasisMm':ps,'centerBoardRotatedBasisMm':center,'squareSizeMm':[hi[0]-lo[0],hi[2]-lo[2]]})
assert all(abs(pins[i+1]['centerBoardRotatedBasisMm'][0]-pins[i]['centerBoardRotatedBasisMm'][0]-2.5)<3e-5 for i in range(2))
x=pins[1]['centerBoardRotatedBasisMm'][0];z=pins[1]['centerBoardRotatedBasisMm'][2];y=c['bounds'][0][1]
def world(p):return [a[k]*p[0]+(p[1]if k==1 else 0)+n[k]*p[2]for k in range(3)]
mouth=world([x,y,z]);out=[0,-1,0];T=[[a[k],n[k],out[k],mouth[k]]for k in range(3)]+[[0,0,0,1]]
second={**first,'sourceSocket':110,'mouth':mouth,'shoulder':[mouth[k]+2.1*out[k]for k in range(3)],'outward':out,'transform':T,'evidence':'Actual saved source component110 has three independent0.6mm square pin-end face vertex sets at2.5mm pitch; mouth is actual shroud outer-rim Y=-12.7100000381, row centre from middle pin. No board-bbox port surrogate.','pinFaceCentersWorldMm':[world(p['centerBoardRotatedBasisMm'])for p in pins],'pinFaceWitnesses':pins,'expectedUse':'OpenRB second physical TTL branch to motor10; same electrical bus, no increased-current inference'}
def boxmesh(port,key):
 lo,hi=port['housingLocalBounds'];T=port['transform'];vs=[]
 for x,y,z in [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]:
  q=[hi[0]if x else lo[0],hi[1]if y else lo[1],hi[2]if z else lo[2]];vs.append([sum(T[i][j]*q[j]for j in range(3))+T[i][3]for i in range(3)])
 fs=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]]
 text=['solid '+key]
 for f in fs:
  p,q,r=[vs[i]for i in f];u=[q[i]-p[i]for i in range(3)];w=[r[i]-p[i]for i in range(3)];normal=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]];norm=sum(x*x for x in normal)**.5;text.append('facet normal '+' '.join(str(x/norm)for x in normal));text.append('outer loop');text.extend('vertex '+' '.join(f'{x:.17g}'for x in vs[i])for i in f);text+=['endloop','endfacet']
 text.append('endsolid '+key);path=D/(key+'.stl');path.write_text('\n'.join(text));return {'key':key,'file':str(path.resolve()),'sha256':sha(path),'expectedFinalBoundsMm':[[min(v[k]for v in vs)for k in range(3)],[max(v[k]for v in vs)for k in range(3)]],'coordinates':'same old world frame as source OpenRB; apply same board rigid delta for new placement','kind':'full catalogue mated receiving envelope; not detailed latch'}
result={'status':'source-registered two sockets; placement/insertion pending','sourceHashes':{str(OLD/n):sha(OLD/n)for n in ['openrb-port-probe.json','openrb-registered-port.json','openrb-current-source-equivalence.json']},'registrationToleranceMm':3e-5,'toleranceMeaning':'numeric source-face witness consistency, not manufacturing tolerance','ports':[first,second],'parts':[boxmesh(first,'openrb-first-eh-housing'),boxmesh(second,'openrb-second-eh-housing')],'pinOrderVerified':False}
(D/'two-openrb-ports.json').write_text(json.dumps(result,indent=2));print(second['mouth'],second['shoulder'])
