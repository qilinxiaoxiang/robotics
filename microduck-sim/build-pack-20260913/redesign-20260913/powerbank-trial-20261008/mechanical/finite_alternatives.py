from pathlib import Path
import sys,json,hashlib,base64,itertools
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parent.parent;SIM=R.parents[1];A=SIM/'hardware-design-20260912/whole-robot-20260912/assembly';sys.path.insert(0,str(A));from assembly_fk import fk,TREE,XML
C=R/'head-redesign-20261008/usb-access/usb-repair/robot-source-cache'
def man(m):return mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
def dec(key):
 d=json.loads((C/(key+'.json')).read_text());m=trimesh.Trimesh(np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3),process=True);return d,m
objects={}
for name,off in [('rear20',[-20,0,0]),('up40',[0,0,40]),('rear10up25',[-10,0,25])]:
 m=trimesh.load(D/'pb1033mi-reference-world.stl',force='mesh');m.apply_translation(off);objects[name]=m
fixed={k:man(m) for k,m in objects.items()};bb={k:m.bounds for k,m in objects.items()};baseline=fk()[0]
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

report={'states':states,'bounds':{k:m.bounds.tolist() for k,m in objects.items()},'failures':fails};(D/'finite-pose-alternatives.json').write_text(json.dumps(report,indent=2));print({k:sum(r['obstacle']==k for r in fails) for k in objects})
