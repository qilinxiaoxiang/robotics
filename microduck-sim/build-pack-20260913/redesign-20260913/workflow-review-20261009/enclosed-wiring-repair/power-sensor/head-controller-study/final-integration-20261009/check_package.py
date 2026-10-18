from pathlib import Path
import sys,json,hashlib,gc,numpy as np,trimesh,manifold3d as mf
F=Path(__file__).resolve().parent;src=F/'joint-package.json';r=json.loads(src.read_text());group=sys.argv[1];conservative=[]
def load(q):
 p=Path(q['file']);assert hashlib.sha256(p.read_bytes()).hexdigest()==q['sha256'];m=trimesh.load_mesh(p);m.apply_transform(q['worldTransform'])
 if not m.is_volume:m=m.convex_hull;conservative.append(q['key'])
 assert m.is_volume;s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
moving={q['key']:load(q)for q in r['parts']if q['group']==group};checks=[];bounds={k:list(a.bounding_box())for k,a in moving.items()};obstacles=[q for q in r['parts']if q['group']!=group and not(group in ['pi','pi_interface_conditional']and q['group']in['pi','pi_interface_conditional'])]
for q in obstacles:
 b=load(q);B=np.array(b.bounding_box()).reshape(2,3)
 for k,a in moving.items():
  A=np.array(a.bounding_box()).reshape(2,3);sep=np.any(A[1]<B[0])or np.any(B[1]<A[0]);c=None if sep else a^b
  if c is not None:assert c.status()==mf.Error.NoError
  v=0 if sep else max(0,c.volume());checks.append({'moving':k,'obstacle':q['key'],'obstacleGroup':q['group'],'volumeMm3':v,'method':'bounds-separated'if sep else'valid-solid-intersection','intersectionBoundsMm':list(c.bounding_box())if v>1e-6 else None})
 del b;gc.collect()
hits=[c for c in checks if c['volumeMm3']>1e-6];expected=len(moving)*len(obstacles);out={'sourceManifest':str(src),'sourceSha256':hashlib.sha256(src.read_bytes()).hexdigest(),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'group':group,'expectedPairs':expected,'completedPairs':len(checks),'coverageComplete':expected==len(checks),'staticClear':not hits,'wholeHeadAccepted':False,'checks':checks,'hits':hits,'bounds':bounds,'conservativeRepairs':conservative};(F/('joint-check-'+group+'.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'group':group,'pairs':len(checks),'hits':len(hits),'byGroup':{g:sum(q['volumeMm3']for q in hits if q['obstacleGroup']==g)for g in set(q['obstacleGroup']for q in hits)}},indent=2))
