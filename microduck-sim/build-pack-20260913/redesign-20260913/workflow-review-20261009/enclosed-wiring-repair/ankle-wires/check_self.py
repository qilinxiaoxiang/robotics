from pathlib import Path
import json,hashlib,ast,math
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent/'motor-wires';src=(M/'local_route.py').read_text()
for n in ast.parse(src).body:
 if isinstance(n,ast.FunctionDef)and n.name in ['sample','tube','solid']:exec(ast.get_source_segment(src,n))
r=json.loads((D/'ankle-route-check.json').read_text());rows=[]
for w in r['strands']:
 pp=[]
 for p in w['primitives']:
  pts,tt=sample([p]);m=tube(pts,tt);pp.append((m.bounds,solid(m)))
 for i,(bb,a)in enumerate(pp):
  for j,(cc,b)in enumerate(pp[i+2:],i+2):
   if np.any(bb[1]<cc[0])or np.any(cc[1]<bb[0]):v=0
   else:c=a^b;assert c.status()==mf.Error.NoError;v=c.volume()
   rows.append({'wire':w['key'],'primitiveA':i,'primitiveB':j,'volumeMm3':v})
out={'scope':'Every non-adjacent exact line/arc primitive sweep in each strand; adjacent shared cross-section excluded. Distinct strands covered separately.','rows':rows,'passed':all(x['volumeMm3']<1e-7 for x in rows),'sourceSha256':hashlib.sha256((D/'ankle-route-check.json').read_bytes()).hexdigest()};(D/'self-check.json').write_text(json.dumps(out,indent=2));print(len(rows),[x for x in rows if x['volumeMm3']>1e-7])
