from pathlib import Path
import json,math,ast
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent/'motor-wires';O=D.parents[1]/'roof-wiring-stage/motor-wires/obstacles';src=(M/'local_route.py').read_text()
for n in ast.parse(src).body:
 if isinstance(n,ast.FunctionDef)and n.name in ['sample','tube','solid']:exec(ast.get_source_segment(src,n))
top=json.loads((M/'active-topology.json').read_text());p=top['ports']['motor-1-socket-13'];B=np.array(p['shoulder'])-np.array(p['width'])*2.5;u=np.array(p['outward']);obs=[]
for f in O.glob('*.json'):
 q=json.loads(f.read_text())
 if q['key'] in ['right_lower','motor1','right_ankle']:
  m=trimesh.load_mesh(q['file']);m.apply_translation(q.get('importTranslationMm',[0,0,0]));obs.append((q['key'],solid(m)))
rows=[]
for deg in [-15]:
 v=np.array([-math.cos(math.radians(deg)),0,math.sin(math.radians(deg))]);center=B+2*v;end=B+2*(u+v);normal=np.cross(u,v);mid=center+(-2*v)*math.cos(math.pi/4)+np.cross(normal,-2*v)*math.sin(math.pi/4)
 pr=[{'kind':'arc','start':B.tolist(),'mid':mid.tolist(),'end':end.tolist(),'center':center.tolist(),'normal':normal.tolist(),'radiusMm':2,'sweepRadians':math.pi/2,'lengthMm':math.pi},{'kind':'line','start':end.tolist(),'end':(end+v*5).tolist(),'lengthMm':5}];pts,tan=sample(pr);a=solid(tube(pts,tan));hits=[{'key':k,'v':(a^b).volume()}for k,b in obs];rows.append({'angle':deg,'hits':hits,'primitives':pr});print(deg,hits)
(D/'target-elbow-midpoint-check.json').write_text(json.dumps(rows,indent=2))
