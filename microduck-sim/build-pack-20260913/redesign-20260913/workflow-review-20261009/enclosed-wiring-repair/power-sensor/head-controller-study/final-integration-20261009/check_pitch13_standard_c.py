from pathlib import Path
import json,hashlib,gc,numpy as np,trimesh,manifold3d as mf
F=Path(__file__).resolve().parent;E=F.parents[2];HD=E/'head-layout'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
src=F/'smt-header-package.json';r=json.loads(src.read_text());old=np.array(r['boardNativeToWorld']);T=old.copy();p=np.radians(13);T[:3,:3]=[[0,-np.cos(p),-np.sin(p)],[1,0,0],[0,-np.sin(p),np.cos(p)]];delta=T@np.linalg.inv(old)
parts=[]
for q in r['parts']:
 q=dict(q)
 if q['key'].startswith('controller-roof-boss-')or q['group']=='c_receiver':continue
 if q['group']=='controller':q['worldTransform']=(delta@q['worldTransform']).tolist()
 if q['key']=='current_amp':
  q['file']=str(HD/'head-flexible-harness/amp-mounts/amplifier_plusY1.stl');q['sha256']=sha(q['file']);q['worldTransform']=np.eye(4).tolist()
 parts.append(q)
# Full source external receiver: source metal back plane -9.25 maps to assumed native shoulder y34.1.
# Includes all STEP shell vertices and .3 insulation clearance on the non-mating body.
source=F/'7semi-all-source.stl';mesh=trimesh.load_mesh(source);b=mesh.bounds.copy();b[0]-=.3;b[1]+=.3
# Do not expand the front mating nose; the native USB socket is not an external collision target.
b[1,1]=-9.25
m=trimesh.creation.box(extents=b[1]-b[0]);m.apply_translation(b.mean(axis=0));S=np.eye(4);S[:3,:3]=np.diag([-1,-1,1]);S[:3,3]=[.015,24.85,3.23];m.apply_transform(T@S);f=F/'pitch13-7semi-external-receiving.stl';m.export(f)
parts.append({'key':'7semi_external_insulated_receiver','file':str(f),'sha256':sha(f),'worldTransform':np.eye(4).tolist(),'group':'controller','geometryKind':'source_bounds_plus_0.3_insulation'})
fragment=HD/'head-flexible-harness/amp-mounts/amp-mount-fragment.json'
for q in json.loads(fragment.read_text())['parts']:parts.append(dict(q,group='amp_mounts'))
mp=F/'pitch13-standard-c-package.json';mp.write_text(json.dumps({'sourceManifest':str(src),'sourceSha256':sha(src),'sourceReceiver':str(source),'receiverSha256':sha(source),'boardNativeToWorld':T.tolist(),'boardDelta':delta.tolist(),'parts':parts,'status':'bounded_pitch_candidate_not_accepted','externalLengthMm':float(-9.25-b[0,1]),'removedMounts':'Four old controller roof posts require regeneration if layout passes; no source shell removed.'},indent=2)+'\n')
conservative=[]
def load(q):
 assert sha(q['file'])==q['sha256'];m=trimesh.load_mesh(q['file']);m.apply_transform(q['worldTransform'])
 if not m.is_volume:m=m.convex_hull;conservative.append(q['key'])
 assert m.is_volume;s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
moving={q['key']:load(q)for q in parts if q['group']=='controller'};obs=[q for q in parts if q['group']!='controller'];checks=[]
for q in obs:
 s=load(q);B=np.array(s.bounding_box()).reshape(2,3)
 for k,a in moving.items():
  A=np.array(a.bounding_box()).reshape(2,3);sep=np.any(A[1]<B[0])or np.any(B[1]<A[0]);c=None if sep else a^s
  if c is not None:assert c.status()==mf.Error.NoError
  v=0 if c is None else max(0,c.volume());checks.append({'moving':k,'obstacle':q['key'],'volumeMm3':v,'boundsMm':list(c.bounding_box())if v>1e-6 else None})
 del s;gc.collect()
hits=[x for x in checks if x['volumeMm3']>1e-6];out={'sourceManifest':str(mp),'sourceSha256':sha(mp),'expectedPairs':len(moving)*len(obs),'completedPairs':len(checks),'coverageComplete':len(checks)==len(moving)*len(obs),'staticClear':not hits,'wholeHeadAccepted':False,'checks':checks,'hits':hits,'conservativeRepairs':conservative};(F/'pitch13-standard-c-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'pairs':len(checks),'hits':hits},indent=2))
