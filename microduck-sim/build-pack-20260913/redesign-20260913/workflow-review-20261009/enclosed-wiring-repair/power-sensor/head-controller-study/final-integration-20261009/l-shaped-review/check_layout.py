from pathlib import Path
import json,hashlib,sys,gc
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;F=D.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
src=F/'original-inset-pi4-package.json';r=json.loads(src.read_text());T0=np.array(r['boardNativeToWorld']);P0=np.array(r['piCurrentWorldDelta'])
T=np.eye(4);T[:3,:3]=[[0,1,0],[0,0,-1],[-1,0,0]];T[:3,3]=[20,-20,132]
P=np.eye(4);P[:3,:3]=[[0,0,1],[0,1,0],[-1,0,0]];P[:3,3]=np.array([61,6,132])-P[:3,:3]@np.array([59,-1,131.5])
solids={};meshes={};repaired=[];bounds={}
for q in r['parts']:
 if q['group']=='controller':q['worldTransform']=(T@np.linalg.inv(T0)@q['worldTransform']).tolist()
 elif q['group'] in ['pi','pi_interface_conditional']:q['worldTransform']=(P@np.linalg.inv(P0)@q['worldTransform']).tolist()
 elif q['group']=='speaker':
  q['worldTransform'][0][3]+=18;q['worldTransform'][1][3]+=12;q['worldTransform'][2][3]+=6
 elif q['group']=='amp':
  # Existing side amp moved rearward/down into opposite cheek; no mounts frozen.
  q['worldTransform'][0][3]-=7;q['worldTransform'][1][3]-=5;q['worldTransform'][2][3]-=4
 p=Path(q['file']);assert sha(p)==q['sha256'];m=trimesh.load_mesh(p);m.apply_transform(q['worldTransform'])
 if not m.is_volume:
  repaired.append(q['key']);m=m.convex_hull
 assert m.is_volume,q['key'];s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError
 solids[q['key']]=s;meshes[q['key']]=m;bounds[q['key']]=m.bounds.tolist()
# Full ordinary A join is a separate conditional SC0727 option, not confirmed stock.
m=trimesh.creation.box([47.9,20,12]);m.apply_translation([25,17,145]);p=D/'conditional-a-join-receiver.stl';m.export(p)
q={'key':'conditional_A_join','group':'conditional_A_join','file':str(p),'sha256':sha(p),'worldTransform':np.eye(4).tolist(),'geometryKind':'historical_unconfirmed_receiver'};r['parts'].append(q);meshes[q['key']]=m;bounds[q['key']]=m.bounds.tolist();solids[q['key']]=mf.Manifold(mf.Mesh64(m.vertices,m.faces.astype(np.uint64)))
r.update(status='COMPLETE_RIGID_L_CANDIDATE_NOT_ACCEPTED',boardNativeToWorld=T.tolist(),piCurrentWorldDelta=P.tolist(),stage='Single complete L candidate. OpenRB side XZ with C towards +X; Pi frontal YZ with standard female receivers. Original closed shell/mechanisms/camera retained. Audio relocated together; old added mounts withdrawn. No new connector selected.',sourceManifest=str(src),sourceSha256=sha(src),geometryBounds=bounds)
r['oldSideLaneNegative']=str(F.parents[2]/'head-layout/fusion-head-cross-board.json');r['differencesFromOldSideLane']='Perpendicular front Pi / side OpenRB with USB-C toward +X, not the rejected oblique side-lane assembly. All component bodies checked individually.'
(D/'layout.json').write_text(json.dumps(r,indent=2)+'\n')
checks=[]
def group(q):return 'pi' if q['group']=='pi_interface_conditional'else q['group']
for i,a in enumerate(r['parts']):
 for b in r['parts'][i+1:]:
  if group(a)==group(b):continue
  A=np.array(bounds[a['key']]);B=np.array(bounds[b['key']]);sep=bool(np.any(A[1]<B[0])or np.any(B[1]<A[0]));v=0;c=None
  if not sep:
   c=solids[a['key']]^solids[b['key']];assert c.status()==mf.Error.NoError;v=max(0,c.volume())
  checks.append({'a':a['key'],'b':b['key'],'groups':[a['group'],b['group']],'volumeMm3':v,'method':'aabb-separated'if sep else'valid-solid-intersection','boundsMm':list(c.bounding_box())if v>1e-6 else None})
hits=[c for c in checks if c['volumeMm3']>1e-6]
out={'sourceManifest':str(D/'layout.json'),'sourceSha256':sha(D/'layout.json'),'scriptSha256':sha(__file__),'wholeHeadAccepted':False,'expectedPairs':len(checks),'completedPairs':len(checks),'hits':hits,'checks':checks,'conservativeHullKeys':repaired,'scope':'Rigid package only; conditional USB-A and photo MicroB are explicitly approximate, not proof of physical impossibility.'};(D/'check.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'pairs':len(checks),'hits':len(hits),'topHits':sorted(hits,key=lambda c:-c['volumeMm3'])[:18]},indent=2))
