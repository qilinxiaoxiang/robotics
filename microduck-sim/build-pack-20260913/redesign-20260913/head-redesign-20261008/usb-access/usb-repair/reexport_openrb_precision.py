from pathlib import Path
import os,json,base64,sys,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
from types import SimpleNamespace
h=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008');d=h/'usb-access/usb-repair';c=d/'robot-source-cache';idx=json.loads((c/'index.json').read_text());f=c/idx['parts']['openrb'];r=json.loads(f.read_text());m=tm.Trimesh(np.frombuffer(base64.b64decode(r['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(r['indexB64']),'<u4').reshape(-1,3),process=True)
tfile=h/'curved-head/openrb-pose-checkpoint.json';t=np.array(json.loads(tfile.read_text())['transformFromGuideWorld']);s=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)));assert s.status()==mf.Error.NoError
q=s.to_mesh64();n=tm.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=False)
def dig(mm):
 a=np.ascontiguousarray(mm.vertices[mm.faces],dtype=np.float64);b=np.sort(a.view('V24').reshape(-1,3),axis=1);return hashlib.sha256(np.sort(b.view('V72').reshape(-1)).tobytes()).hexdigest()
result={'sourceFaces':len(m.faces),'sourceWatertight':bool(m.is_watertight),'sourceVolume':bool(m.is_volume),'normalizedFaces':len(n.faces),'normalizedWatertight':bool(n.is_watertight),'normalizedVolume':bool(n.is_volume),'triangleSame':dig(m)==dig(n),'zeroAreaSourceFaces':int(sum(m.area_faces<1e-15)),'boundsSame':bool(np.array_equal(m.bounds,n.bounds))}
print(json.dumps(result));(d/'openrb-source-topology-diagnostic.json').write_text(json.dumps(result,indent=2)+'\n')
