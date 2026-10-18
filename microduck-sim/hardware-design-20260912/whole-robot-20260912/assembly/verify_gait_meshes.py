from assembly_fk import *
import json,sys,time,itertools,mujoco
from pathlib import Path
OUT=Path(__file__).parent/'compact-battery';path=Path(sys.argv[1]) if len(sys.argv)>1 else OUT.parents[1]/'dynamics/baseline-5v-walking-video.json'
DATA=json.loads(path.read_text());model=mujoco.MjModel.from_xml_path(str(XML));data=mujoco.MjData(model)
names=[model.joint(i).name for i in range(model.njnt)];print('JOINTS',names,flush=True)
objs={k:trimesh.load(OUT/f,force='mesh') for k,f in {'structure':'power-support-integrated-body.stl','battery':'battery-max-envelope-body.stl','small_cover':'small-regulator-cover-body.stl','ties':'two-retention-ties-envelope.stl','large_regulator':'large_regulator-envelope-body.stl','small_regulator':'small_regulator-envelope-body.stl'}.items()}
old=trimesh.load(OUT/'original-power-support-body.stl');objs['structure']=trimesh.boolean.difference([objs['structure'],old],engine='manifold')
_,geoms=fk();geoms=[(g,raw(g['mesh']),model.body(g['body']).id) for g in geoms if g['body']!='trunk_base']
ri=model.body('trunk_base').id
collisions=[];nchecks=0;start=time.time();safety=[]
def inter(a,b):
 if np.any(a.bounds[1]<b.bounds[0]) or np.any(b.bounds[1]<a.bounds[0]):return 0.
 return max(0.,float(trimesh.boolean.intersection([a,b],engine='manifold').volume))
for fi,row in enumerate(DATA['rows'][::3]):
 data.qpos[:]=row['qpos'];mujoco.mj_forward(model,data);R=data.xmat[ri].reshape(3,3);p=data.xpos[ri]*1000
 for g,rawmesh,bi in geoms:
  B=np.eye(4);B[:3,:3]=R.T@data.xmat[bi].reshape(3,3);B[:3,3]=R.T@(data.xpos[bi]*1000-p);m=rawmesh.copy().apply_transform(B@g['local'])
  for name,ob in objs.items():
   nchecks+=1;v=inter(ob,m)
   if v>.005:collisions.append(dict(frame=fi*3,time=row['time'],part=name,obstacle=g['body']+'/'+g['mesh'],intersection_mm3=v))
 if fi%50==0:print('frames',fi,'collisions',len(collisions),flush=True)
report={'trajectory':str(path),'source_frames':len(DATA['rows']),'sampled_frames':len(DATA['rows'][::3]),'stride':3,'sample_interval_s':.06,'mujoco_version':mujoco.__version__,'source_xml':str(XML),'pair_tests':nchecks,'collisions':collisions,'elapsed_seconds':time.time()-start,'scope':'Exact transformed raw reference meshes versus current added structure, new battery/regulators/retention. Uses actual simulated qpos and MuJoCo body kinematics. Checks all moving parts. Internal fixed-body checks are separate verification.json. Cables, impact strength and heat not modeled.'}
output=OUT/f'gait-mesh-check-{path.stem}.json';output.write_text(json.dumps(report,indent=2));print('DONE',len(collisions),output,flush=True)
