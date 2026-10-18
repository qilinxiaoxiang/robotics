import json,base64,os
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent.parent;cache=H/'usb-access/usb-repair/robot-source-cache';idx=json.loads((cache/'index.json').read_text());d=json.loads((cache/idx['parts']['motor11']).read_text());m=trimesh.Trimesh(np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3),process=True)
def info(m):
 a=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)));_,counts=np.unique(m.edges_sorted,axis=0,return_counts=True)
 return {'vertices':len(m.vertices),'faces':len(m.faces),'watertight':bool(m.is_watertight),'windingConsistent':bool(m.is_winding_consistent),'isVolume':bool(m.is_volume),'signedVolume':float(m.volume),'boundaryEdges':int(sum(counts==1)),'overSubscribedEdges':int(sum(counts>2)),'manifoldStatus':str(a.status()),'manifoldVolume':float(a.volume()),'bodies':len(m.split(only_watertight=False))}
r={'original':info(m)};m.fix_normals(multibody=True);r['normalRepairOnly']=info(m);r['surfaceVerticesUnchanged']=True
print(json.dumps(r));(D/'motor11-input-validity.json').write_text(json.dumps(r,indent=2)+'\n')
