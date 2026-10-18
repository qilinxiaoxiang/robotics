from pathlib import Path
import json,numpy as np,trimesh
H=Path(__file__).resolve().parent;ns={'__file__':str(H/'prepare_geometry.py')};exec((H/'prepare_geometry.py').read_text().split('rows=[]')[0],ns)
rows=json.loads((H/'community-print-inventory.json').read_text())['objects'];res=[]
for id in [26,28,40,42,64,66]:
 r=next(r for r in rows if r['id']==id);m=ns['mesh']('3D/3dmodel.model',str(id));ref=ns['raw'](r['reference_mesh']);best=None
 for R in ns['rot']:
  vv=m.vertices@R.T;bb=np.array([vv.min(0),vv.max(0)]);t=ref.bounds.mean(0)-bb.mean(0)
  if np.linalg.norm(np.ptp(vv,axis=0)-ref.extents)>.12:continue
  mm=trimesh.Trimesh(vv+t,m.faces,process=False);p,_=trimesh.sample.sample_surface(mm,400,seed=32);q,_=trimesh.sample.sample_surface(ref,400,seed=33)
  d1=trimesh.proximity.closest_point(ref,p)[1];d2=trimesh.proximity.closest_point(mm,q)[1];score=max(np.quantile(d1,.95),np.quantile(d2,.95))
  if best is None or score<best[0]:best=(score,R,t,max(max(d1),max(d2)))
 x={'id':id,'source_name':r['source_name'],'reference':r['reference_mesh'],'surface_p95_mm':float(best[0]),'sample_max_mm':float(best[3]),'rotation':best[1].tolist(),'translation':best[2].tolist()};res.append(x);print(x,flush=True)
(H/'source-surface-refinement.json').write_text(json.dumps(res,indent=2))
