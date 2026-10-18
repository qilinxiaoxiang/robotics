from pathlib import Path
import json,math,hashlib,ast
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent/'motor-wires';W=D.parents[1];O=W/'roof-wiring-stage/motor-wires/obstacles'
src=(M/'local_route.py').read_text()
for node in ast.parse(src).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['primitives','sample','tube','solid']:
  code=ast.get_source_segment(src,node)
  if node.name=='primitives':code=code.replace('R=(4. if ix in [3,4,5] else 2.)','R=2. if ix<4 or ix==len(pts)-3 else 4.')
  exec(code)
top=json.loads((M/'active-topology.json').read_text());route=next(r for r in top['routes']if r['id']=='ttl-02-01');fr=top['ports'][route['fromPort']];to=top['ports'][route['toPort']]
A=np.array(fr['shoulder']);B=np.array(to['shoulder']);Y=-68.0;Z=-55.
def controls(X):return [A,[A[0],Y,A[2]],[-18,Y,A[2]],[-18,-63.5,A[2]],[-18,-63.5,-56],[X,-63.5,-56],[X,-37.4,-56],[X,-37.4,B[2]],[B[0],-37.4,B[2]],B]
X=-65.;p=primitives(controls(X));X-=(180-sum(q['lengthMm']for q in p))/2;p=primitives(controls(X));pts,tans=sample(p);m=tube(pts,tans);a=solid(m);m.export(D/'ankle-right-center.stl');rows=[]
for f in O.glob('*.json'):
 ob=json.loads(f.read_text());bb=np.array(ob['expectedFinalBoundsMm'])
 if np.any(m.bounds[1]<bb[0])or np.any(bb[1]<m.bounds[0]):continue
 b=trimesh.load_mesh(ob['file']);b.apply_translation(ob.get('importTranslationMm',[0,0,0]));c=a^solid(b);v=c.volume();rows.append({'key':ob['key'],'volumeMm3':v,'boundsMm':list(c.bounding_box()) if v>1e-7 else None})
r={'primitives':p,'controls':np.array(controls(X)).tolist(),'lengthMm':sum(q['lengthMm']for q in p),'rows':rows,'hits':[r for r in rows if r['volumeMm3']>1e-7]};(D/'core-check.json').write_text(json.dumps(r,indent=2));print(json.dumps({'length':r['lengthMm'],'X':X,'hits':r['hits']}))
