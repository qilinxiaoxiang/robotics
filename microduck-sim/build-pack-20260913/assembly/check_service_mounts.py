"""Static and sampled trajectory check for newly added detachable service mounts."""
from pathlib import Path
import sys,json,itertools,time
import numpy as np,trimesh,manifold3d as md,mujoco
HERE=Path(__file__).resolve().parent;O=HERE/'service-mounts';SIM=HERE.parents[1]
OLD=SIM/'hardware-design-20260912/whole-robot-20260912';sys.path.insert(0,str(OLD/'assembly'))
from assembly_fk import fk,raw,XML
def solid(m):
 m=m.copy();m.fix_normals();s=md.Manifold(md.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)));assert s.status()==md.Error.NoError;return s
def corners(m):return np.array(list(itertools.product(*zip(m.bounds[0],m.bounds[1]))))
def overlap(a,b):return np.all(a[1]>=b[0]) and np.all(b[1]>=a[0])
def add(name,body,path,m=None):
 m=trimesh.load(path,force='mesh') if m is None else m
 return {'name':name,'body':body,'source':str(path),'mesh':m,'solid':solid(m),'corners':corners(m)}
new=[add(p.stem,'trunk_base',p) for p in sorted(O.glob('*-body.stl'))+sorted(O.glob('*-envelope.stl'))]
report=OLD/'assembly/full-assembly/full-assembly-final-trajectory.json';inventory=json.loads(report.read_text())['inventory'];base=[]
for x in inventory:
 p=Path(x['source'])
 if x['name'].startswith('retained/'):
  _,body,mesh,index=x['name'].split('/');g=next(g for g in fk()[1] if g['body']==body and g['mesh']==mesh and g['index']==int(index))
  m=raw(mesh).apply_transform(g['local'])
 else:m=trimesh.load(p,force='mesh')
 base.append(add(x['name'],x['body'],p,m))
static=[]
for a,b in itertools.combinations(new,2):
 if overlap(a['mesh'].bounds,b['mesh'].bounds):
  v=float((a['solid']^b['solid']).volume())
  if v>.005:static.append({'a':a['name'],'b':b['name'],'mm3':v})
for a in new:
 for b in base:
  if b['body']!='trunk_base':continue
  if overlap(a['mesh'].bounds,b['mesh'].bounds):
   v=float((a['solid']^b['solid']).volume())
   if v>.005:static.append({'a':a['name'],'b':b['name'],'mm3':v})
traj=OLD/'delay-repair-20260912/repair-final-batteryremove60-headremove15.json'
if not traj.exists():traj=OLD/'dynamics/final-batteryremove60-headremove15.json'
rows=json.loads(traj.read_text())['rows'];M=mujoco.MjModel.from_xml_path(str(XML));D=mujoco.MjData(M);rid=M.body('trunk_base').id
moving=[x for x in base if x['body']!='trunk_base'];collisions=[];checks=0;booleans=0;frames=np.linspace(0,len(rows)-1,250,dtype=int)
for i,fi in enumerate(frames):
 row=rows[int(fi)];D.qpos[:]=row['qpos'];mujoco.mj_forward(M,D);R=D.xmat[rid].reshape(3,3);p=D.xpos[rid]*1000
 for b in moving:
  bi=M.body(b['body']).id;T=np.eye(4);T[:3,:3]=R.T@D.xmat[bi].reshape(3,3);T[:3,3]=R.T@(D.xpos[bi]*1000-p)
  pts=b['corners']@T[:3,:3].T+T[:3,3];bb=np.array([pts.min(0),pts.max(0)]);bs=None
  for a in new:
   checks+=1
   if not overlap(a['mesh'].bounds,bb):continue
   if bs is None:bs=b['solid'].transform(T[:3])
   booleans+=1;v=float((a['solid']^bs).volume())
   if v>.005:collisions.append({'t':row['time'],'a':a['name'],'b':b['name'],'mm3':v})
 if i%50==0:print('frames',i,'hits',len(collisions),flush=True)
result={'static_collisions':static,'trajectory':str(traj),'sample_frames':len(frames),'pair_checks':checks,'exact_booleans':booleans,'motion_collisions':collisions,'passed':not static and not collisions,'scope':'New service-mount solids and installed component envelopes vs frozen whole robot, at 250 sampled recorded poses; no flexible-wire/strength/dynamics acceptance.'}
(O/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['static_collisions','motion_collisions']},indent=2));print('STATIC',static);print('DYNAMIC',collisions[:8]);sys.exit(0 if result['passed'] else 1)
