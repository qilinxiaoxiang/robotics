from pathlib import Path
import json,trimesh as tm,manifold3d as mf,numpy as np
P=Path(__file__).resolve().parent
rows=[]
for f in (P/'delivery').glob('*/*.stl'):
 m=tm.load(f,force='mesh');s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)))
 r={'file':str(f),'watertight':bool(m.is_watertight),'volume':bool(m.is_volume),'manifoldStatus':str(s.status()),'triangles':len(m.faces)};rows.append(r)
(P/'delivery-stl-readback.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
