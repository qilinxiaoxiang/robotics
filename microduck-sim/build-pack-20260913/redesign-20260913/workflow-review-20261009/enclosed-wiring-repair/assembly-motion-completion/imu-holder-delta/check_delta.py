from pathlib import Path
import argparse,base64,hashlib,json,sys
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;A=D.parent;R=A.parents[2];G=R/'leg-guide-20261006';I=A.parent/'power-sensor'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=json.loads((I/'imu-local-manifest.json').read_text());native={p['key']:p for p in m['parts']}
inputs={k:A/'station-inputs'/f'{k}.json' for k in ['imu-02','imu-04']}

def load(p):
 if 'meshFile' in p:
  mesh=trimesh.load(p['meshFile'],force='mesh');assert sha(p['meshFile'])==p['meshSha256']
 else:
  v=np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3);f=np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3);mesh=trimesh.Trimesh(v,f,process=True)
 s=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,np.float32),np.asarray(mesh.faces,np.uint32)))
 assert s.status()==mf.Error.NoError and s.volume()>0,(p['key'],s.status())
 return s

def bounds(p):return np.array(p.get('expectedFinalBoundsMm',p.get('bounds')),float)
def apart(a,b):return bool(np.any(a[1]<b[0]) or np.any(b[1]<a[0]))
def box(s):return np.array(s.bounding_box()).reshape(2,3)
def volume(a,b):
 if apart(box(a),box(b)):return 0.
 c=a^b;assert c.status()==mf.Error.NoError;return max(0,float(c.volume()))
def cylinder(o,axis,lo,hi,r):
 axis=np.array(axis,float);T=trimesh.geometry.align_vectors([0,0,1],axis);T[:3,3]=np.array(o)+axis*(lo+hi)/2
 mesh=trimesh.creation.cylinder(radius=r/np.cos(np.pi/48),height=hi-lo,sections=48).apply_transform(T)
 return mf.Manifold(mf.Mesh(np.array(mesh.vertices,np.float32),np.array(mesh.faces,np.uint32)))
def run(mode):
 packet=json.loads(inputs['imu-02' if mode=='holder' else 'imu-04'].read_text());parts={p['key']:p for p in packet['parts']}
 parts.update(native);cache={};rows=[];fail=[];sources={str(I/'imu-local-manifest.json'):sha(I/'imu-local-manifest.json'),str(inputs['imu-02' if mode=='holder' else 'imu-04']):sha(inputs['imu-02' if mode=='holder' else 'imu-04'])}
 for p in native.values():sources[p['meshFile']]=p['meshSha256']
 def solid(k):
  if k not in cache:cache[k]=load(parts[k])
  return cache[k]
 if mode=='holder':
  moving=solid('imu_clamp');old=load(next(p for p in packet['parts'] if p['key']=='imu_clamp'))
  delta=moving-old;assert delta.status()==mf.Error.NoError
  subset={'newOutsideOldMm3':max(0,float(delta.volume())),'newBoundsMm':box(moving).tolist(),'oldBoundsMm':box(old).tolist()}
  bb=box(moving);swept=bb.copy();swept[0,0]-=28
  obstacles=[k for k in parts if not k.startswith('imu_') and not k.startswith('fuse_carrier') and not k.startswith('nut_E-fuse')]
  for k in obstacles:
   if apart(swept,bounds(parts[k])):rows.append({'part':k,'samples':113,'aabbSeparated':True});continue
   vals=[volume(moving.translate([-28*(1-j/112),0,0]),solid(k)) for j in range(113)]
   row={'part':k,'samples':113,'maximumMm3':max(vals),'finalMm3':vals[-1]};rows.append(row)
   if max(vals)>1e-5:fail.append(row)
  report={'motion':{'key':'imu_clamp','approachVector':[-28,0,0],'samples':113},'subset':subset}
 else:
  # Fresh complete local geometry plus all already installed external station parts.
  screws={s['id']:s for s in packet['screws']}
  clamp_packet=json.loads(inputs['imu-02'].read_text());screws.update({s['id']:s for s in clamp_packet['screws']});sources[str(inputs['imu-02'])]=sha(inputs['imu-02'])
  selected=[k for k in screws if k.startswith('E-imu_clamp') or k.startswith('E-imu_rear_cover')]
  for sid in selected:
   screw=screws[sid];o=screw['world_center_mm'];axis=screw['world_axis'];w=screw.get('washer_mm',0)
   models={'shaft':cylinder(o,axis,w+2,w+45.5,1.5),'handle':cylinder(o,axis,w+45.5,w+105.5,9)}
   for role,tool in models.items():
    for k,p in parts.items():
     if k.startswith('fuse_carrier') or k.startswith('nut_E-fuse'):continue
     # Holder clamp is tightened with board/cover/cable absent, then board inserted.
     if sid.startswith('E-imu_clamp') and k.startswith('imu_') and k!='imu_clamp':continue
     if apart(box(tool),bounds(p)):rows.append({'screw':sid,'toolPart':role,'part':k,'aabbSeparated':True});continue
     v=volume(tool,solid(k));row={'screw':sid,'toolPart':role,'part':k,'intersectionMm3':v};rows.append(row)
     if v>1e-5:fail.append(row)
   prior=[x for x in screws.values() if x['id']!=sid and (not x['id'].startswith('E-imu_rear_cover') or sid.startswith('E-imu_rear_cover'))]
   for s in prior:
    h=cylinder(s['world_center_mm'],s['world_axis'],s.get('washer_mm',0),s.get('washer_mm',0)+1.5,2.5)
    v=volume(models['shaft']+models['handle'],h);row={'screw':sid,'priorScrew':s['id'],'intersectionMm3':v};rows.append(row)
    if v>1e-5:fail.append(row)
  report={'screwIds':selected,'tool':{'shaftDiameterMm':3,'shaftLengthMm':45,'handleDiameterMm':18,'handleLengthMm':60}}
 report.update(passed=not fail,scope='Changed IMU holder insertion and local complete driver envelope delta; no physical tolerances or flexible-motion certification.',rows=rows,failures=fail,sourceHashes=sources,scriptSha256=sha(__file__))
 (D/(mode+'-check.json')).write_text(json.dumps(report,indent=2));print(json.dumps({'mode':mode,'passed':not fail,'rows':len(rows),'failures':fail,'subset':report.get('subset')}));return not fail
if __name__=='__main__':sys.exit(0 if run(sys.argv[1]) else 1)
