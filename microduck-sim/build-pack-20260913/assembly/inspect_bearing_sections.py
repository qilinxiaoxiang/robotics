from pathlib import Path
import numpy as np,json,trimesh
H=Path(__file__).resolve().parent
ns={'__file__':str(H/'prepare_geometry.py')};exec((H/'prepare_geometry.py').read_text().split('rows=[]')[0],ns)
for id in [53,55,59,62,64,66,44,46,4]:
 m=ns['mesh']('3D/3dmodel.model',str(id));print('\nID',id,'BOUNDS',np.round(m.bounds,4))
 ax=int(np.argmin(m.extents)) if id in [53,55,59,62] else 0
 n=np.eye(3)[ax]
 for f in [.05,.25,.5,.75,.95]:
  p=m.bounds.mean(0);p[ax]=m.bounds[0,ax]+m.extents[ax]*f;s=m.section(plane_origin=p,plane_normal=n)
  if s is None:continue
  print('AX',ax,'AT',round(p[ax],3),'LOOPS',[(len(q),np.round(q.min(0),3).tolist(),np.round(q.max(0),3).tolist()) for q in s.discrete])
