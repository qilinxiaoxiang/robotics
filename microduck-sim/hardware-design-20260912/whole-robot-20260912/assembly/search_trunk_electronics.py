from assembly_fk import *
from compact_search import intersect
import itertools,json
from pathlib import Path
obs=[(g,m) for g,m in world_meshes() if g['mesh']!='np_f970']
res={}
for name,ds in [('reg1',[(11,43.2,31.8),(11,31.8,43.2),(31.8,11,43.2),(43.2,11,31.8),(43.2,31.8,11)]),('reg2',[(9.7,22.9,22.9),(22.9,9.7,22.9),(22.9,22.9,9.7)])]:
 found=[]
 for d in ds:
  for c in itertools.product(np.arange(-10,33,4),[-20,-10,0,10,20],np.arange(8,33,4)):
   box=trimesh.creation.box(d).apply_translation(c)
   if box.bounds[0,2]<2.5 or box.bounds[1,2]>40 or box.bounds[0,1]<-29 or box.bounds[1,1]>29 or box.bounds[1,0]>32 or box.bounds[0,0]<-22:continue
   if not any(intersect(box,m)>.001 for g,m in obs):found.append({'center':c,'dimensions':d})
 res[name]=found;print(name,len(found),found[:10],flush=True)
Path(__file__).with_name('trunk-electronics-candidates.json').write_text(json.dumps(res,indent=2,default=float))
