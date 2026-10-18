from pathlib import Path
import hashlib,json
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parents[3];F=R/'fastener-review-20261008';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 assert m.is_volume;s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
manifest=json.loads((D/'eight-leg-manifest.json').read_text());rev=json.loads((F/'fastener-patch-proposal.json').read_text());inv=json.loads((D/'complete-interface-inventory.json').read_text());parts=manifest['parts']+inv['existingAdjustableTieReceivingBodies'];rows=[];sources={str(D/'eight-leg-manifest.json'):sha(D/'eight-leg-manifest.json'),str(F/'fastener-patch-proposal.json'):sha(F/'fastener-patch-proposal.json')}
for key in ['lower','right_lower']:
 r=rev['geometryCandidates'][key];f=F/r['worldMesh'];assert sha(f)==r['worldMeshSha256'];sources[str(f)]=sha(f);m=trimesh.load_mesh(f);b=solid(m)
 for p in parts:
  assert sha(p['file'])==p['sha256'];sources[p['file']]=p['sha256'];a=trimesh.load_mesh(p['file']);a.apply_translation(p.get('importTranslationMm',[0,0,0]));bb=a.bounds
  if np.any(bb[1]<m.bounds[0])or np.any(m.bounds[1]<bb[0]):rows.append({'part':p['key'],'obstacle':key,'separatedByAabb':True,'volumeMm3':0});continue
  c=solid(a)^b;assert c.status()==mf.Error.NoError;v=c.volume();rows.append({'part':p['key'],'obstacle':key,'volumeMm3':v,'boundsMm':list(c.bounding_box())if v>1e-7 else None});print(p['key'],key,v,flush=True)
report={'passed':all(r['volumeMm3']<1e-7 for r in rows),'scope':'All 24 conductors, 16 receiving housings and 2 existing adjustable case anchors versus the two effective guide integral-seat lower links. Native source lower references are unchanged until the integration owner chooses the displayed variant. No physical adoption inferred.','sourceHashes':sources,'rows':rows,'scriptSha256':sha(__file__)};(D/'current-lower-revision-delta.json').write_text(json.dumps(report,indent=2));print('passed',report['passed'])
