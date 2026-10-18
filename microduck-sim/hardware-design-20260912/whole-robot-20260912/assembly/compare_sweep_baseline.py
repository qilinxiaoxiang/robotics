from assembly_fk import *
import json,itertools
from pathlib import Path
O=Path(__file__).parent/'compact-battery'
def inter(a,b):
 if np.any(a.bounds[1]<b.bounds[0]) or np.any(b.bounds[1]<a.bounds[0]):return 0.
 return max(0.,float(trimesh.boolean.intersection([a,b],engine='manifold').volume))
old=np.concatenate([]) if False else next(m for g,m in world_meshes() if g['mesh']=='np_f970')
configs={'old_battery':old,'reg_large_narrow':trimesh.creation.box([43.2,31.8,11]).apply_translation([-35.5,0,-48]),'small_shifted':trimesh.creation.box([22.9,9.7,22.9]).apply_translation([-4,0,17.5])}
results=[]
for j in TREE.findall('.//worldbody//joint'):
 if j.get('range') is None:continue
 lo,hi=np.fromstring(j.get('range'),sep=' ')
 for a in np.linspace(lo,hi,17):
  for g,m in world_meshes({j.get('name'):a}):
   if g['body']=='trunk_base':continue
   for n,b in configs.items():
    v=inter(b,m)
    if v>.005:results.append(dict(joint=j.get('name'),rad=a,item=n,obstacle=g['body']+'/'+g['mesh'],intersection_mm3=v))
(O/'sweep-baseline-and-alternatives.json').write_text(json.dumps(results,indent=2))
from collections import Counter
print(Counter(x['item'] for x in results))
