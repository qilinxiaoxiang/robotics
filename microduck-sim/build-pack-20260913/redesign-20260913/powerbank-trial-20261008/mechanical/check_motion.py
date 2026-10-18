from pathlib import Path
import sys,json,hashlib,base64,itertools
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parent.parent;SIM=R.parents[1];A=SIM/'hardware-design-20260912/whole-robot-20260912/assembly';sys.path.insert(0,str(A));from assembly_fk import fk,TREE,XML
C=R/'head-redesign-20261008/usb-access/usb-repair/robot-source-cache'
def man(m):return mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
def dec(key):
 d=json.loads((C/(key+'.json')).read_text());m=trimesh.Trimesh(np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3),process=True);return d,m
objects={n:trimesh.load(D/n,force='mesh') for n in ['pb1033mi-backpack-world.stl','pb1033mi-reference-world.stl','adafruit5991-receiving-world.stl']};fixed={k:man(m) for k,m in objects.items()};bb={k:m.bounds for k,m in objects.items()};baseline=fk()[0]
limits={j.get('name'):list(map(float,j.get('range').split())) for j in TREE.iter('joint') if j.get('range')};states=[{}]
for side in ['left','right']:
 js=[side+'_hip_'+j for j in ['yaw','roll','pitch']]
 for j in js:
  states.extend([{j:float(a)} for a in np.linspace(*limits[j],13)])
 states.extend([dict(zip(js,q)) for q in itertools.product(*[[limits[j][0],0,limits[j][1]] for j in js])])
# Duplicate poses removed; finite domain, explicitly not a continuous/full range proof.
states=list({json.dumps(q,sort_keys=True):q for q in states}.values());transforms=[fk(q)[0] for q in states]
rows=[];fails=[];checks=0
keys=['hip','right_hip','yaw','right_yaw','motor9','motor4','thigh','right_thigh','motor8','motor3','motor7','motor2','lower','right_lower','ankle','right_ankle','foot','right_foot']
for key in keys:
 d,m=dec(key);solid=man(m);assert solid.status()==mf.Error.NoError
 inv=np.linalg.inv(baseline[d['body']]);vertices=m.vertices
 for i,(q,tr) in enumerate(zip(states,transforms)):
  mat=tr[d['body']]@inv;pos=vertices@mat[:3,:3].T+mat[:3,3];bounds=np.array([pos.min(0),pos.max(0)])
  for k,o in fixed.items():
   checks+=1
   if np.any(bounds[1]<bb[k][0]) or np.any(bb[k][1]<bounds[0]):continue
   v=(solid.transform(mat[:3])^o).volume()
   if v>1e-4:fails.append({'state':i,'jointRadians':q,'part':key,'obstacle':k,'intersectionMm3':v})
# Full insertion of empty carrier: approach from rear with support tongues above shelf,
# then lower2mm onto shelf. Static bank loading is separate from robot attachment.
sourcekeys=['power_support','imu_clamp','imu_board','fuse_carrier','regulator','regulator_insert','shell_left','shell_right','motor10','motor5']
pathfails=[]
for key in sourcekeys:
 _,m=dec(key);o=man(m)
 for i in range(81):
  off=[-40*(1-i/80),0,2]
  v=(fixed['pb1033mi-backpack-world.stl'].translate(off)^o).volume()
  if v>1e-4:pathfails.append({'part':key,'phase':'rear approach','sample':i,'intersectionMm3':v})
 for i in range(9):
  v=(fixed['pb1033mi-backpack-world.stl'].translate([0,0,2*(1-i/8)])^o).volume()
  if v>1e-4:pathfails.append({'part':key,'phase':'seat on shelf','sample':i,'intersectionMm3':v})
report={'sampledPoses':len(states),'states':states,'partKeys':keys,'checkedPairs':checks,'failures':fails,'mountInsertionSamplesPerObstacle':90,'mountInsertionObstacles':sourcekeys,'mountInsertionFailures':pathfails,'scope':'Finite single-hip13samples plus27corner combinations per leg; not a whole-robot continuous motion certificate. No joint range changed. Exact native meshes, specified rectangularbank/5991 receiving.','hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),XML,D/'pb1033mi-backpack-world.stl',D/'pb1033mi-reference-world.stl']}}
(D/'motion-and-insertion.json').write_text(json.dumps(report,indent=2)+'\n');print('POSES',len(states),'FAILURES',len(fails),'MOUNTFAIL',len(pathfails));print(fails[:8]);print(pathfails[:8])
