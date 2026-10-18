from assembly_fk import *
import json,itertools,mujoco,time
from pathlib import Path
O=Path(__file__).parent/'trunk-imu';C=O.parent/'compact-battery';H=O.parents[1]/'electrical/head-layout/final'
items={p.stem:trimesh.load(p,force='mesh') for p in O.glob('*_body.stl')}
def inter(a,b):
 if np.any(a.bounds[1]<b.bounds[0]) or np.any(b.bounds[1]<a.bounds[0]):return 0.
 return max(0,float(trimesh.boolean.intersection([a,b],engine='manifold').volume))
obs=[(g['body']+'/'+g['mesh'],m) for g,m in world_meshes() if g['mesh'] not in ['np_f970','power_support','top_head_shell']]
for p in ['power-support-integrated-body.stl','battery-max-envelope-body.stl','large_regulator-envelope-body.stl','small_regulator-envelope-body.stl','small-regulator-cover-body.stl','two-retention-ties-envelope.stl']:obs.append((p,trimesh.load(C/p)))
bodies,geoms=fk()
for p in H.glob('*_assembly.stl'):obs.append((p.name,trimesh.load(p).apply_transform(bodies['jaw_soft'])))
static=[]
for (an,a),(bn,b) in itertools.combinations(items.items(),2):
 if (v:=inter(a,b))>.005:static.append({'a':an,'b':bn,'volume_mm3':v})
for n,m in obs:
 for name,ob in items.items():
  if (v:=inter(ob,m))>.005:static.append({'a':name,'b':n,'volume_mm3':v})
print('STATIC',static,flush=True);result={'static_collisions':static};(O/'validation.json').write_text(json.dumps(result,indent=2))
if static:raise SystemExit('Fix static before trajectory')
M=mujoco.MjModel.from_xml_path(str(XML));D=mujoco.MjData(M);root=M.body('trunk_base').id
moving=[(g['body']+'/'+g['mesh'],g['body'],raw(g['mesh']),g['local']) for g in geoms if g['body']!='trunk_base' and g['mesh']!='top_head_shell']
for p in H.glob('*_assembly.stl'):moving.append((p.name,'jaw_soft',trimesh.load(p),np.eye(4)))
trajectory=O.parents[1]/'dynamics/heading-suite-old60-head30-battery57.json';rows=json.loads(trajectory.read_text())['rows'];collisions=[];count=0;start=time.time()
for i,row in enumerate(rows[::3]):
 D.qpos[:]=row['qpos'];mujoco.mj_forward(M,D);R=D.xmat[root].reshape(3,3);p=D.xpos[root]*1000
 for n,body,m,local in moving:
  bi=M.body(body).id;T=np.eye(4);T[:3,:3]=R.T@D.xmat[bi].reshape(3,3);T[:3,3]=R.T@(D.xpos[bi]*1000-p)
  mesh=m.copy().apply_transform(T@local)
  for name,ob in items.items():
   count+=1
   if (v:=inter(ob,mesh))>.005:collisions.append({'frame':i*3,'time':row['time'],'part':name,'obstacle':n,'volume_mm3':v})
 if i%100==0:print('FRAME',i,'collisions',len(collisions),flush=True)
result.update(trajectory=str(trajectory),frames=len(rows[::3]),sample_period_s=.06,pair_checks=count,moving_collisions=collisions,wall_s=time.time()-start,head_includes='Both final head_cap_assembly.stl and audio_carrier_assembly.stl');(O/'validation.json').write_text(json.dumps(result,indent=2));print('DONE',len(collisions),count,flush=True)
