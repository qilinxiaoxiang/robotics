"""Locate current neutral clash; no source cuts or integration claims."""
import json
from pathlib import Path
import segmented_yaw_forward_worker as w
w.core.guard();w.current();s=json.loads((w.OUT/'self-summary.json').read_text());assert s['passed'] and s['planHash']==w.sha(w.OUT/'plan.json')
w.core.OUT=w.OUT;w.core.geom=w.route;w.core.passed_self=lambda:s;w.core.mesh(-1)
import trimesh,numpy as np,manifold3d as mf
man=w.H/'camera-ribbon-repair/positive-x225/candidate-manifest.json';d=json.loads(man.read_text());src=w.H/d['replacementMeshes']['head_bottom'];route=w.OUT/'meshes/-1.stl'
def load(p):
 m=trimesh.load(p,force='mesh');assert m.is_watertight and m.is_volume;a=mf.Manifold(mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32)));assert a.status()==mf.Error.NoError and a.volume()>0;return m,a
rm,a=load(route);hm,b=load(src);hit=a^b;assert hit.status()==mf.Error.NoError
out=w.OUT/'headbottom-neutral-intersection.stl';m=hit.to_mesh();tm=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);assert tm.is_watertight and tm.is_volume;tm.export(out);read=trimesh.load(out,force='mesh');assert read.is_watertight and read.is_volume
r={'accepted':False,'sourceCut':False,'diagnosticOnly':True,'receivingMeshLimitation':'24-sided circumscribed loft is used only to locate/visualize already-detected strict capsule failure; volume is not proof of nominal circular-wire exact intersection. No continuous acceptance from mesh alone.','intersectionMeshVolumeMm3':float(hit.volume()),'intersectionBoundsMm':read.bounds.tolist(),'components':[{'volumeMm3':float(c.volume),'boundsMm':c.bounds.tolist()} for c in read.split()],'headBottomBoundsMm':hm.bounds.tolist(),'routeBoundsMm':rm.bounds.tolist(),'sourceHashes':{str(p):w.sha(p) for p in [Path(__file__),src,route,out,man,w.OUT/'plan.json']},'nextCriterion':'Check if swept clearance stays within a local inward-facing neck opening without cutting outer cheek wall, bearing seats or jaw supports. No cut made.'};w.save(w.OUT/'headbottom-clash.json',r);print(json.dumps(r))
