from pathlib import Path
import numpy as np,trimesh,json
p=Path(__file__).with_name('review_integrated.py');ns={'__file__':str(p)};exec(p.read_text().split('rows=[];seen=set()')[0],ns)
it=ns['solids']['head_bottom']^ns['solids']['upper_pad'];src=ns['source']('head_bottom')^ns['source']('upper_pad');extra=it-src
vm=extra.to_mesh();v=np.asarray(vm.vert_properties)[:,:3];sm=ns['source']('head_bottom').to_mesh();old=trimesh.Trimesh(np.asarray(sm.vert_properties)[:,:3],np.asarray(sm.tri_verts),process=False)
d=[]
for a in range(0,len(v),4):d.extend(trimesh.proximity.closest_point_naive(old,v[a:a+4])[1].tolist())
r={'pair':['head_bottom','upper_pad'],'sourceContactMm3':float(src.volume()),'currentContactMm3':float(it.volume()),'outsideSourceMm3':float(extra.volume()),'outsideVertices':len(v),'maximumOutsideVertexDistanceToOriginalHeadShellSurfaceMm':max(d),'exportSimplificationSurfaceToleranceMm':.00001,'scope':'Final seated source contact. The small added remeshing residual is bounded independently; no motion-path or material-fit acceptance.'}
(Path(__file__).parent/'upperpad-source-contact-review.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
