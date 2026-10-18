from pathlib import Path
import json,hashlib,sys,gc,ast,math
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;O=M.parents[1]/'roof-wiring-stage/motor-wires/obstacles';side=sys.argv[1]if len(sys.argv)>1 else'right';datafile=D/f'joint-{side}.json';data=json.loads(datafile.read_text());top=json.loads((M/'active-topology.json').read_text());NM=M.parent/'ankle-wires/native-motors/manifest.json';nm=json.loads(NM.read_text());native=[r for r in nm['parts']if r['motor']==2];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 assert m.is_volume,(m.is_watertight,m.is_winding_consistent,m.volume)
 s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError and s.volume()>0;return s
checks=[];sources={str(datafile):sha(datafile),str(NM):sha(NM)};inventory=[]
for w in data['strands']:
 assert sha(w['file'])==w['sha256'];a=trimesh.load_mesh(w['file']);sa=solid(a)
 for f in O.glob('*.json'):
  ob=json.loads(f.read_text());key=ob['key'];bb=np.array(ob['expectedFinalBoundsMm']);sources[str(f)]=sha(f)
  if np.any(a.bounds[1]<bb[0])or np.any(bb[1]<a.bounds[0]):inventory.append({'wire':w['key'],'obstacle':key,'status':'AABB-separated'});continue
  p=Path(ob['file']);assert sha(p)==ob['sha256'];sources[str(p)]=sha(p)
  if key.startswith('motor')and key[5:].isdigit():
   T=np.array(top['ports'][f'motor-{int(key[5:])}-socket-13']['transform'])
   def motors():
    for r in native:
     assert sha(r['file'])==r['sha256'];m=trimesh.load_mesh(r['file']);m.apply_transform(T@np.linalg.inv(r['worldTransform']));yield key+'-solid'+str(r['solid']),m
   meshes=motors()
  else:
   m=trimesh.load_mesh(p);m.apply_translation(ob.get('importTranslationMm',[0,0,0]));meshes=[(key,m)]
  for label,b in meshes:
   if np.any(a.bounds[1]<b.bounds[0])or np.any(b.bounds[1]<a.bounds[0]):inventory.append({'wire':w['key'],'obstacle':label,'status':'AABB-separated'});continue
   sb=solid(b);c=sa^sb;assert c.status()==mf.Error.NoError;v=c.volume();r={'wire':w['key'],'obstacle':label,'volumeMm3':v,'bounds':list(c.bounding_box())if v>1e-7 else None};checks.append(r)
   if v>1e-7:print(r,flush=True)
  gc.collect()
 print(w['key'],'done',flush=True)
out={'passed':all(x['volumeMm3']<1e-7 for x in checks),'sourceHashes':sources,'checks':checks,'separated':inventory,'scope':'Every current original-body obstacle; manufacturer 12 closed solids replace each aggregate motor. Receiving diameter 1.5 mm, not measured cable specification.'};(D/f'valid-{side}.json').write_text(json.dumps(out,indent=2));print('passed',out['passed'],len(checks),len(inventory))
