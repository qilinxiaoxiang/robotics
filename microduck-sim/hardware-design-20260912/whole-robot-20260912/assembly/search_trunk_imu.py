from assembly_fk import *
import json,itertools
from pathlib import Path
O=Path(__file__).parent;C=O/'compact-battery'
obs=[(g['mesh'],m) for g,m in world_meshes() if g['mesh'] not in ['np_f970','power_support']]
for p in ['power-support-integrated-body.stl','battery-max-envelope-body.stl','large_regulator-envelope-body.stl','small_regulator-envelope-body.stl','small-regulator-cover-body.stl','two-retention-ties-envelope.stl']:obs.append((p,trimesh.load(C/p)))
def collides(a,b):
 if np.any(a.bounds[1]<b.bounds[0]) or np.any(b.bounds[1]<a.bounds[0]):return False
 return float(trimesh.boolean.intersection([a,b],engine='manifold').volume)>.005
results=[]
for dims in [(28,25,8),(25,28,8),(28,8,25),(25,8,28),(8,28,25),(8,25,28)]:
 found=[]
 for c in itertools.product(np.arange(-45,32,5),np.arange(-25,26,5),np.arange(5,39,5)):
  b=trimesh.creation.box(dims).apply_translation(c)
  if b.bounds[0,0]<-49 or b.bounds[1,0]>34 or b.bounds[0,1]<-31 or b.bounds[1,1]>31 or b.bounds[0,2]<2.5 or b.bounds[1,2]>40:continue
  if not any(collides(b,m) for n,m in obs):found.append({'center':list(c),'dims':dims})
 results+=found;print('DIMS',dims,'candidates',len(found),found[:15],flush=True)
(O/'trunk-imu-candidates.json').write_text(json.dumps(results,indent=2,default=float))
