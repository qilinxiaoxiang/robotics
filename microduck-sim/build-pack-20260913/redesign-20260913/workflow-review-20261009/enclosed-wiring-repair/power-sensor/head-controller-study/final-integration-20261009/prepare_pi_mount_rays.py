from pathlib import Path
import json,numpy as np,trimesh,hashlib
F=Path(__file__).resolve().parent;r=json.loads((F/'custom-harness-package.json').read_text());P=np.array(r['piCurrentWorldDelta']);caprow=next(q for q in r['parts']if q['key']=='current_cap');cap=trimesh.load_mesh(caprow['file']);rows=[]
for y in [-30.,28.]:
 p=(P@np.array([44.8,y,127.3,1]))[:3];hits=cap.ray.intersects_location(np.array([p]),np.array([[0.,0,1]]),multiple_hits=True)[0];ds=sorted(h[2]-p[2]for h in hits if h[2]>p[2]);assert ds
 rows.append({'sourceY':y,'origin':p.tolist(),'capRayDistances':ds,'roofPostLengthMm':ds[0]+.7,'seats':[(P@np.array([x,y,130.7,1]))[:3].tolist() for x in [47.5,70.5]]})
(F/'pi-mount-roof-rays.json').write_text(json.dumps({'capSha256':hashlib.sha256(Path(caprow['file']).read_bytes()).hexdigest(),'piTransform':P.tolist(),'rows':rows},indent=2)+'\n');print(rows)
