from assembly_fk import *
import json
from pathlib import Path
obs=[(g,m) for g,m in world_meshes() if g['mesh']!='np_f970']
def intersect(a,b):
 if np.any(a.bounds[1]<b.bounds[0]) or np.any(b.bounds[1]<a.bounds[0]):return 0.
 try:return max(0,float(trimesh.boolean.intersection([a,b],engine='manifold').volume))
 except Exception as e:return str(e)
records=[]
for x in [-36,-37,-38,-39,-40,-41,-42,-43,-44]:
 b=trimesh.creation.box([22,34,63]);b.apply_translation([x,0,-4]);c=[]
 for g,m in obs:
  v=intersect(b,m)
  if isinstance(v,str) or v>.001:c.append((g['body'],g['mesh'],v))
 records.append({'center':[x,0,-4],'collisions':c});print(records[-1],flush=True)
Path(__file__).with_name('compact-battery-position-search.json').write_text(json.dumps(records,indent=2))
