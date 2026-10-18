from pathlib import Path
import json,numpy as np,trimesh
H=Path(__file__).resolve().parent
ns={'__file__':str(H/'prepare_geometry.py')};exec((H/'prepare_geometry.py').read_text().split('rows=[]')[0],ns)
rows=json.loads((H/'community-print-inventory.json').read_text())['objects'];done=set();res=[]
for r in rows:
 if r['source_name'] in done:continue
 done.add(r['source_name'])
 if 'reference_mesh' not in r:continue
 m=ns['mesh']('3D/3dmodel.model',str(r['id']));ref=ns['raw'](r['reference_mesh']);T=np.eye(4);T[:3,:3]=r['source_to_reference_rotation'];T[:3,3]=r['source_to_reference_translation_mm'];m.apply_transform(T)
 # Evenly seeded surface samples assess geometric surfaces, independent of tessellation density.
 p,_=trimesh.sample.sample_surface(m,3000,seed=31);q,_=trimesh.sample.sample_surface(ref,3000,seed=31)
 d1=trimesh.proximity.closest_point(ref,p)[1];d2=trimesh.proximity.closest_point(m,q)[1]
 x={'id':r['id'],'source_name':r['source_name'],'candidate':r['reference_mesh'],'source_to_ref_p95_mm':float(np.quantile(d1,.95)),'ref_to_source_p95_mm':float(np.quantile(d2,.95)),'sample_max_mm':float(max(max(d1),max(d2))),'samples_per_direction':3000};res.append(x);print(x,flush=True)
(H/'source-surface-comparison.json').write_text(json.dumps(res,indent=2))
