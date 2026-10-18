from pathlib import Path
import json,numpy as np,trimesh
F=Path(__file__).resolve().parent;r=json.loads((F/'custom-harness-package.json').read_text());T=np.array(r['boardNativeToWorld']);P=np.array(r['piCurrentWorldDelta']);caprow=next(q for q in r['parts']if q['key']=='current_cap');cap=trimesh.load_mesh(caprow['file']);out={'controller':[],'pi':[]}
for g,rows in [('controller',[(np.array([x,y,1.6]),T,T[:3,2])for x in [-10.25,10.25]for y in [-30.75,30.75]]),('pi',[(np.array([x,y,130.7]),P,-P[:3,2])for x in [47.5,70.5]for y in [-30,28]])]:
 for p,M,n in rows:
  o=(M@np.r_[p,1])[:3];hits=cap.ray.intersects_location(np.array([o]),np.array([n]),multiple_hits=True)[0];dist=sorted(float(np.dot(h-o,n))for h in hits if np.dot(h-o,n)>0);out[g].append({'seat':o.tolist(),'outwardBossAxis':n.tolist(),'capRayDistances':dist})
(F/'mount-datum-rays.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
