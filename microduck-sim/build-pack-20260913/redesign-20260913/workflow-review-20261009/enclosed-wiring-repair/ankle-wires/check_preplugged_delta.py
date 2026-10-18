from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent/'motor-wires';O=D.parents[1]/'roof-wiring-stage/motor-wires/obstacles'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 assert m.is_volume
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert a.status()==mf.Error.NoError;return a
top=json.loads((M/'active-topology.json').read_text());obs={json.loads(f.read_text())['key']:json.loads(f.read_text())for f in O.glob('*.json')};rows=[]
for port,vec,keys in [('motor-2-socket-14',[0,45,0],['right_thigh','motor3']),('motor-7-socket-13',[0,-45,0],['thigh','motor8']),('motor-1-socket-13',[0,0,30],['right_ankle','right_smallring']),('motor-6-socket-14',[0,0,30],['ankle','smallring'])]:
 m=trimesh.load_mesh(D/(port+'-housing.stl'));a=solid(m);v=np.array(vec);checks=[]
 for key in keys:
  ob=obs[key];assert sha(ob['file'])==ob['sha256'];mm=trimesh.load_mesh(ob['file']);mm.apply_translation(ob.get('importTranslationMm',[0,0,0]));
  if key.startswith('motor'):
   # Conservative full motor outer box only here; disjoint proves body separation.
   mm=trimesh.creation.box(mm.extents,transform=trimesh.transformations.translation_matrix(mm.bounds.mean(axis=0)))
  b=solid(mm);hits=[];n=int(np.linalg.norm(v)/.25)+1
  for t in np.linspace(0,1,n):
   c=a.translate(v*t)^b;assert c.status()==mf.Error.NoError
   if c.volume()>1e-7:hits.append({'offsetFraction':float(t),'volumeMm3':c.volume(),'bounds':list(c.bounding_box())})
  checks.append({'key':key,'sourceSha256':ob['sha256'],'samples':n,'hits':hits})
 row={'port':port,'housingSha256':sha(D/(port+'-housing.stl')),'approachVectorMm':vec,'checks':checks,'passed':not any(c['hits']for c in checks)};rows.append(row);print(port,row['passed'],[(c['key'],len(c['hits']))for c in checks],flush=True)
(D/'preplugged-delta.json').write_text(json.dumps({'scope':'Added rigid plug bodies carried with the motor along existing guide approaches. Only listed bench obstacles exist at this operation. Complete flexible wire shape is arranged loose and not swept as rigid. Does not supersede guide bare-motor source-contact and ankle closure physical-fit boundaries.','topologySha256':sha(M/'active-topology.json'),'sourceScriptSha256':sha(__file__),'rows':rows,'passed':all(r['passed']for r in rows)},indent=2))
