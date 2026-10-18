from pathlib import Path
import json,math,hashlib,ast
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent/'motor-wires';W=D.parents[1];O=W/'roof-wiring-stage/motor-wires/obstacles'
src=(M/'local_route.py').read_text()
for node in ast.parse(src).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['primitives','sample','tube','solid']:
  code=ast.get_source_segment(src,node)
  if node.name=='primitives':code=code.replace('R=(4. if ix in [3,4,5] else 2.)','R=2. if ix<4 or ix>=len(pts)-5 else 4.')
  exec(code)
top=json.loads((M/'active-topology.json').read_text());rows=[];allmeshes=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
obstacles=[json.loads(f.read_text()) for f in O.glob('*.json')]
for rid in ['ttl-02-01','ttl-07-06']:
 route=next(r for r in top['routes']if r['id']==rid);fr=top['ports'][route['fromPort']];to=top['ports'][route['toPort']];sign=-1 if fr['shoulder'][1]<0 else 1
 for k in [-1,0,1]:
  A=np.array(fr['shoulder'])+np.array(fr['width'])*2.5*k;B=np.array(to['shoulder'])+np.array(to['width'])*2.5*k-np.array(to['outward'])*.6;E=-20.6 if k==-1 else -18-1.7*k;Z=-52.5 if k==-1 else -56+1.7*k;inner=61.5 if k==-1 else 63.5;ret=37.4-2*k
  def controls(X):
   yy=38-2*k
   controls=[A,[A[0],sign*68,A[2]],[E,sign*68,A[2]],[E,sign*inner,A[2]],[E,sign*inner,Z],[X,sign*inner,Z],[X,sign*yy,Z],[X,sign*yy,B[2]]]
   if k!=0:controls += [[-51,sign*yy,B[2]],[-47,sign*38,B[2]]]
   return controls+[[B[0],sign*38,B[2]],B]

  X=-65.;p=primitives(controls(X));X-=(180-sum(q['lengthMm']for q in p))/2;p=primitives(controls(X));pts,tans=sample(p);mesh=tube(pts,tans);a=solid(mesh);fn=D/f'{rid}-strand-{k+2}.stl';mesh.export(fn);checks=[]
  for ob in obstacles:
   assert sha(ob['file'])==ob['sha256'],ob['key'];bb=np.array(ob['expectedFinalBoundsMm']);r={'key':ob['key'],'sourceSha256':ob['sha256']}
   if np.any(mesh.bounds[1]<bb[0])or np.any(bb[1]<mesh.bounds[0]):r.update(status='BOUNDS_SEPARATE',volumeMm3=0)
   else:
    b=trimesh.load_mesh(ob['file']);b.apply_translation(ob.get('importTranslationMm',[0,0,0]));c=a^solid(b);assert str(c.status())=='Error.NoError';v=c.volume();r.update(status='CLEAR' if v<1e-7 else 'INTERSECTION',volumeMm3=v,boundsMm=list(c.bounding_box()) if v>1e-7 else None)
   checks.append(r)
  hits=[r for r in checks if r['status']=='INTERSECTION'];row={'key':rid+'-'+str(k+2),'routeId':rid,'wireSlot':k,'file':str(fn),'sha256':sha(fn),'source':fr,'target':to,'centerlineLengthMm':sum(q['lengthMm']for q in p),'primitives':p,'controls':np.array(controls(X)).tolist(),'boundsMm':mesh.bounds.tolist(),'checks':checks,'hits':hits};rows.append(row);allmeshes.append((row['key'],a));print(row['key'],X,hits,flush=True)
selfs=[]
for i,(ka,a) in enumerate(allmeshes):
 for kb,b in allmeshes[i+1:]:
  c=a^b;assert str(c.status())=='Error.NoError';selfs.append({'a':ka,'b':kb,'volumeMm3':c.volume(),'boundsMm':list(c.bounding_box())if c.volume()>1e-7 else None})
report={'expectedObstacleKeys':[p['key']for p in obstacles],'strands':rows,'wireWire':selfs,'complete':all(len(r['checks'])==len(obstacles)for r in rows),'passedStatic':not any(r['hits']for r in rows) and all(s['volumeMm3']<1e-7 for s in selfs),'sourceHashes':{str(M/'active-topology.json'):sha(M/'active-topology.json'),str(Path(__file__)):sha(__file__),str(M/'local_route.py'):sha(M/'local_route.py')},'wireDiameterMm':1.5,'stockNominalMm':180,'bendRadiusMm':[2,4],'physicalFitVerified':False};(D/'ankle-route-check.json').write_text(json.dumps(report,indent=2));print('selfs',[s for s in selfs if s['volumeMm3']>1e-7])
