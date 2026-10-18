from pathlib import Path
import math
import json,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;N=D.parent;E=N.parent;W=E.parent;R=W.parent;F=N/'head-controller-study/final-integration-20261009';I=N/'integrated-harness-20261009'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def solid(m):
 assert m.is_volume
 s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s

def inventory(head=True):
 rows=[];hashes={};eye=np.eye(4)
 if head:
  source=F/'smt-header-package.json';hashes[str(source)]=sha(source);rows.extend(read(source)['parts'])
 source=W/'original-body-converter/fusion-import-manifest.json';hashes[str(source)]=sha(source)
 source_parts=read(source)['parts'];head_keys={p['key'].replace('REFERENCE fixed head ','') for p in rows}
 keep={p['key']for p in source_parts[:62]}-head_keys-{'imu_clamp','imu_cover','imu_board','motor11','motor12','motor13','head_yaw_link'}
 rev=R/'fastener-review-20261008/fastener-patch-proposal.json';hashes[str(rev)]=sha(rev);revision=read(rev)['geometryCandidates']
 for p in source_parts:
  if p['key']not in keep:continue
  q={'key':p['key'],'file':p['file'],'sha256':p['sha256'],'worldTransform':eye.copy().tolist(),'group':'body'};q['worldTransform'][0][3],q['worldTransform'][1][3],q['worldTransform'][2][3]=p.get('importTranslationMm',[0,0,0])
  if p['key']=='neck_pitch':q.update(file=str(rev.parent/revision['neck_pitch']['worldMesh']),sha256=revision['neck_pitch']['worldMeshSha256'],worldTransform=eye.tolist())
  rows.append(q)
 native=E/'ankle-wires/native-motors/manifest.json';hashes[str(native)]=sha(native);motor=[p for p in read(native)['parts']if p['motor']==2]
 trans={}
 for p in source_parts:
  if p['key']not in ['motor11','motor12']:continue
  source=Path(p['sourcePartJson']);assert sha(source)==p['sourcePartSha256'];hashes[str(source)]=sha(source);trans[p['key']]=read(source)['sourceTransformWorld']
 for key,T in trans.items():
  for n in motor:rows.append({'key':key+'/'+str(n['solid']),'file':n['file'],'sha256':sha(n['file']),'worldTransform':(np.array(T)@np.linalg.inv(n['worldTransform'])).tolist(),'group':'body'})
 imu=N/'imu-local-manifest.json';hashes[str(imu)]=sha(imu)
 for p in read(imu)['parts']:rows.append({'key':p['key'],'file':p['meshFile'],'sha256':p['meshSha256'],'worldTransform':eye.tolist(),'group':'body_imu'})
 for f in ['body-distribution-manifest.json','data-boundary-manifest.json','zone-housing-manifest.json','input20v-manifest.json']:
  source=I/f;hashes[str(source)]=sha(source)
  for p in read(source)['additionalParts']:rows.append({'key':p['key'],'file':p['file'],'sha256':p['sha256'],'worldTransform':eye.tolist(),'group':'body_wire'})
 assert len({p['key']for p in rows})==len(rows)
 return rows,hashes

def load_obstacles(rows,work_bounds=None):
 out=[]
 for q in rows:
  assert sha(q['file'])==q['sha256'];m=trimesh.load_mesh(q['file']);m.apply_transform(q['worldTransform']);conservative=not m.is_volume
  if work_bounds is not None and (np.any(m.bounds[1]<work_bounds[0]) or np.any(work_bounds[1]<m.bounds[0])):
   out.append((q,m.bounds,None,False));continue
  if conservative:m=m.convex_hull
  out.append((q,m.bounds,solid(m),conservative))
 return out

def check(m,obs):
 a=solid(m);rows=[]
 for q,B,b,conservative in obs:
  if np.any(m.bounds[1]<B[0]) or np.any(B[1]<m.bounds[0]):continue
  assert b is not None,'Geometry outside declared work volume: '+q['key']
  c=a^b;assert c.status()==mf.Error.NoError;v=max(c.volume(),0)
  rows.append({'obstacle':q['key'],'volumeMm3':v,'conservativeHull':conservative,'bounds':list(c.bounding_box())if v>1e-6 else None})
 return rows

def self_check_streamed(pr,pts,diameter):
 lengths=[];s=0
 for a in pr:
  n=max(2,math.ceil(a['lengthMm']/.15));lengths.extend(s+np.arange(n)*a['lengthMm']/n);s+=a['lengthMm']
 lengths.append(s);arcs=np.array(lengths);assert len(arcs)==len(pts)
 exclusion=diameter+1.0;minimum=float('inf')
 for start in range(0,len(pts),64):
  distance=np.linalg.norm(pts[start:start+64,None,:]-pts[None,:,:],axis=2)
  mask=np.abs(arcs[start:start+64,None]-arcs[None,:])>=exclusion
  if mask.any():minimum=min(minimum,float(distance[mask].min()))
 assert minimum>diameter+.32,minimum
 return {'nonlocalMaterialSeparationMm':exclusion,'sampleMaximumSpacingMm':.15,'minimumSampledDistanceMm':minimum,'minimumConservativeBetweenSamplesMm':minimum-.3,'receivingDiameterMm':diameter,'meshRadialOverbuildAllowanceMm':.02,'passed':True,'memoryMethod':'64-row exact pairwise blocks; no changed distance criterion'}
