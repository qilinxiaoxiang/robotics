from pathlib import Path
import json,hashlib,os
assert os.environ.get('MICRODUCK_BOUNDED_CAD')
import trimesh,numpy as np
D=Path(__file__).resolve().parent;p=D/'head-cap-prototype-print.stl';m=trimesh.load(p,force='mesh');r={'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'watertight':bool(m.is_watertight),'boundsMm':m.bounds.tolist(),'bedZmm':float(m.bounds[0,2]),'contactBands':[]}
for eps in [.0001,.001,.01,.02]:
 mask=(m.face_normals[:,2]<-.999)&(m.triangles[:,:,2].max(axis=1)<=m.bounds[0,2]+eps)
 r['contactBands'].append({'maxHeightAboveBedMm':eps,'minOutwardNormalMinusZ':.999,'areaMm2':float(m.area_faces[mask].sum()),'faces':int(mask.sum()),'vertexZRangeMm':[float(m.triangles[mask,:,2].min()),float(m.triangles[mask,:,2].max())]if mask.any()else None})
r['interpretation']='Actual exported mesh faces near its lowest bed plane; no geometry shaved or support added. Native first-layer readback remains slicer responsibility.'
(D/'print-contact.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['contactBands']))
