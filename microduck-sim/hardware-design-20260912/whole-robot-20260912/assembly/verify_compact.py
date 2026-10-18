from assembly_fk import *
import json,itertools,time
from pathlib import Path
OUT=Path(__file__).parent/'compact-battery'
def intersection(a,b):
 if np.any(a.bounds[1]<b.bounds[0]) or np.any(b.bounds[1]<a.bounds[0]):return 0.
 return max(0.,float(trimesh.boolean.intersection([a,b],engine='manifold').volume))
objs={k:trimesh.load(OUT/f,force='mesh') for k,f in {'integrated_support':'power-support-integrated-body.stl','battery':'battery-max-envelope-body.stl','small_cover':'small-regulator-cover-body.stl','ties':'two-retention-ties-envelope.stl'}.items()}
objs['large_regulator']=trimesh.creation.box([43.2,31.8,11]).apply_translation([-35.5,0,-48])
objs['small_regulator']=trimesh.creation.box([22.9,9.7,22.9]).apply_translation([-4,0,17.5])
for name in ['large_regulator','small_regulator']:objs[name].export(OUT/f'{name}-envelope-body.stl')
static=[]
for (an,a),(bn,b) in itertools.combinations(objs.items(),2):
 v=intersection(a,b)
 if v>.005:static.append({'a':an,'b':bn,'intersection_mm3':v})
for g,m in world_meshes():
 if g['mesh'] in ['np_f970','power_support']:continue
 for name,ob in objs.items():
  v=intersection(ob,m)
  if v>.005:static.append({'a':name,'b':f"{g['body']}/{g['mesh']}/{g['index']}",'intersection_mm3':v})
original_frame=trimesh.load(OUT/'original-power-support-body.stl',force='mesh')
lookup={f"{g['body']}/{g['mesh']}/{g['index']}":m for g,m in world_meshes()}
for row in static:
 if row['a']=='integrated_support' and row['b'] in lookup:
  row['original_unmodified_overlap_mm3']=intersection(original_frame,lookup[row['b']])
 row['introduced_overlap_mm3']=max(0,row['intersection_mm3']-row.get('original_unmodified_overlap_mm3',0))
report={'static_collisions':static,'introduced_static_collision_count':sum(row['introduced_overlap_mm3']>.005 for row in static)};(OUT/'verification.json').write_text(json.dumps(report,indent=2));print('STATIC',json.dumps(static),flush=True)
# Single-joint limit sweep, others zero. These extremes are a geometric screen, not guaranteed reachable closed-loop states.
joints=[j for j in TREE.findall('.//worldbody//joint') if j.get('range')];states=[]
for j in joints:
 lo,hi=np.fromstring(j.get('range'),sep=' ')
 for angle in np.linspace(lo,hi,17):states.append((j.get('name'),float(angle)))
old=trimesh.load(OUT/'original-power-support-body.stl',force='mesh');added=trimesh.boolean.difference([objs['integrated_support'],old],engine='manifold')
checks={'new_structure':added,**{k:v for k,v in objs.items() if k!='integrated_support'}};collisions=[];counter=0;start=time.time()
for name,angle in states:
 for g,m in world_meshes({name:angle}):
  if g['body']=='trunk_base':continue
  for k,ob in checks.items():
   v=intersection(ob,m);counter+=1
   if v>.005:collisions.append({'joint':name,'rad':angle,'new_part':k,'obstacle':g['body']+'/'+g['mesh'],'intersection_mm3':v})
 if len(collisions)>1000:break
report.update(single_joint_states=len(states),mesh_pair_checks=counter,single_joint_collisions=collisions,elapsed_s=time.time()-start,scope='17 samples across each explicit XML joint range, others zero; no closure constraint solve; ground and cable dynamics excluded')
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print('SWEEP',len(states),counter,len(collisions),'elapsed',time.time()-start,flush=True)
