from pathlib import Path
import json,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();a=json.loads((D/'all-interfaces.json').read_text());r=json.loads((M/'retention-fusion-manifest.json').read_text());rows=[]
def solid(m):
 assert m.is_volume;s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
for p in r['parts']:
 assert sha(p['file'])==p['sha256'];m=trimesh.load_mesh(p['file']);b=solid(m)
 for w in a['parts']:
  bb=np.array(w['bounds']);cull=np.any(bb[1]<m.bounds[0])or np.any(m.bounds[1]<bb[0]);v=0.;bounds=None
  if not cull:
   assert sha(w['file'])==w['sha256'];x=solid(trimesh.load_mesh(w['file']))^b;assert x.status()==mf.Error.NoError;v=x.volume();bounds=list(x.bounding_box())if v>1e-7 else None
  rows.append({'part':p['key'],'cableEntity':w['key'],'aabbSeparated':bool(cull),'volumeMm3':v,'bounds':bounds})
  if v>1e-7:print(rows[-1])
o={'passed':all(x['volumeMm3']<1e-7 for x in rows),'checks':rows,'sourceHashes':{str(M/'retention-fusion-manifest.json'):sha(M/'retention-fusion-manifest.json'),str(D/'all-interfaces.json'):sha(D/'all-interfaces.json')}};(D/'retention-delta.json').write_text(json.dumps(o,indent=2));print(o['passed'],len(rows))
