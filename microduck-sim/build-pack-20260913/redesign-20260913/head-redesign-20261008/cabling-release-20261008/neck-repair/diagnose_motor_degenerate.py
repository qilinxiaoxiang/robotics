import json,base64,os
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent.parent;cache=H/'usb-access/usb-repair/robot-source-cache';idx=json.loads((cache/'index.json').read_text());d=json.loads((cache/idx['parts']['motor11']).read_text());m=trimesh.Trimesh(np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3),process=True)
area=m.area_faces;before=float(m.volume);zero=area==0;dup=~m.unique_faces();repeated=np.any(np.diff(np.sort(m.faces,axis=1),axis=1)==0,axis=1);keep=~zero&~dup
r={'originalVolumeMm3':before,'exactZeroAreaFaces':int(sum(zero)),'duplicateFaces':int(sum(dup)),'repeatedVertexFaces':int(sum(repeated)),'maximumRemovedFaceArea':float(area[~keep].max(initial=0)),'totalRemovedFaceArea':float(sum(area[~keep]))}
m.update_faces(keep);m.remove_unreferenced_vertices();r.update(watertightAfter=bool(m.is_watertight),isVolumeAfter=bool(m.is_volume),volumeAfter=float(m.volume),volumeDelta=float(m.volume)-before,facesAfter=len(m.faces))
a=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)));r['manifoldStatus']=str(a.status());print(json.dumps(r));(D/'motor11-degenerate-face-diagnostic.json').write_text(json.dumps(r,indent=2)+'\n')
