from pathlib import Path
import numpy as np,json,collections
H=Path(__file__).resolve().parent
ns={'__file__':str(H/'prepare_geometry.py')};exec((H/'prepare_geometry.py').read_text().split('rows=[]')[0],ns)
cs={'__file__':str(H/'inspect_joint_interfaces.py')};exec((H/'inspect_joint_interfaces.py').read_text().split('rows=[]')[0],cs)
out=[]
for oid in [44,46,64,66,62]:
 m=ns['mesh']('3D/3dmodel.model',str(oid));features=collections.defaultdict(list)
 for ax in range(3):
  for v in np.arange(m.bounds[0,ax]+.2,m.bounds[1,ax]-.1,.5):
   for c in cs['circles'](m,ax,v):
    if c['radius']>.5:features[(ax,round(c['radius'],2),tuple(round(x,2) for x in c['center_other_axes']))].append(float(v))
 out.append({'id':oid,'circular_features':[{'axis':k[0],'radius_mm':k[1],'center_other_axes_mm':k[2],'plane_range_mm':[min(v),max(v)],'section_count':len(v)} for k,v in features.items() if len(v)>1]})
(H/'community-ankle-circle-sections.json').write_text(json.dumps(out,indent=2))
for r in out:print(r)
