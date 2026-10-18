from pathlib import Path
import json,hashlib,ast,math,sys,gc
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;O=M.parents[1]/'roof-wiring-stage/motor-wires/obstacles'
src=(M/'local_route.py').read_text()
for n in ast.parse(src).body:
 if isinstance(n,ast.FunctionDef)and n.name in['primitives','sample','tube','solid']:exec(ast.get_source_segment(src,n).replace('R=(4. if ix in [3,4,5] else 2.)','R=radlist[ix] if radlist else 2.'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();top=json.loads((M/'active-topology.json').read_text());ports=top['ports'];obs=[json.loads(p.read_text())for p in O.glob('*.json')];rows=[]
def make(rid,k,fr,to,controls,solve,rad):
 global radlist
 radlist=rad
 p=primitives(controls(solve));length=sum(q['lengthMm']for q in p);solve+=(180-length)/2
 p=primitives(controls(solve));pts,t=sample(p)
 for q in p:
  if q['kind']=='line':
   # direction must agree with its parent polyline segment (not reverse after overlapping fillet trims)
   pass
 m=tube(pts,t);a=solid(m);f=D/f'{rid}-strand-{k+2}.stl';m.export(f);checks=[]
 for ob in obs:
  b=np.array(ob['expectedFinalBoundsMm'])
  if np.any(m.bounds[1]<b[0])or np.any(b[1]<m.bounds[0]):continue
  mm=trimesh.load_mesh(ob['file']);mm.apply_translation(ob.get('importTranslationMm',[0,0,0]));c=a^solid(mm);v=c.volume();checks.append({'obstacle':ob['key'],'sourceSha256':ob['sha256'],'volumeMm3':v,'bounds':list(c.bounding_box())if v>1e-7 else None})
 row={'key':rid+'-'+str(k+2),'routeId':rid,'wireSlot':k,'file':str(f),'sha256':sha(f),'source':fr,'target':to,'primitives':p,'controls':np.array(controls(solve)).tolist(),'boundsMm':m.bounds.tolist(),'lengthMm':sum(q['lengthMm']for q in p),'checks':checks};rows.append(row);print(row['key'],'solve',solve,'len',row['lengthMm'],'hits',[r for r in checks if r['volumeMm3']>1e-7],flush=True);return row
for k in [-1,0,1]:
 fr=ports['motor-4-socket-14'];to=ports['motor-3-socket-14'];A=np.array(fr['shoulder'])+np.array(fr['width'])*2.5*k;B=np.array(to['shoulder'])+np.array(to['width'])*2.5*k;yy=-33+k*1.6;xx=-12+k*1.6;zz=-32.5+k*1.6
 def controls(X):return [A,[xx,A[1],A[2]],[xx,yy,A[2]],[xx,yy,zz],[X,yy,zz],[X,yy-12,zz],[B[0],yy-12,zz],[B[0],-67.8,zz],[B[0],-67.8,B[2]],B]
 make('ttl-04-03',k,fr,to,controls,40,[2,2,2,4,4,4,2,2])
for k in [-1,0,1]:
 fr=ports['motor-2-socket-13'];to=ports['motor-1-socket-13'];A=np.array(fr['shoulder'])+np.array(fr['width'])*2.5*k;B=np.array(to['shoulder'])+np.array(to['width'])*2.5*k-np.array(to['outward'])*.6;E=-12.6+2*k;Z=-52.5 if k==-1 else -56+1.7*k;inner=61.5 if k==-1 else 63.5
 def controls(Q):
  X=-Q;yy=38-2*k
  c=[A,[A[0],-68,A[2]],[E,-68,A[2]],[E,-68,A[2]-5],[E,-inner,A[2]-5],[E,-inner,Z],[X,-inner,Z],[X,-yy,Z],[X,-yy,B[2]]]
  if k!=0:c +=[[-51,-yy,B[2]],[-47,-38,B[2]]]
  return c+[[B[0],-38,B[2]],B]
 make('ttl-02-01',k,fr,to,controls,65,None)
for k in [-1,0,1]:
 fr=ports['motor-3-socket-13'];to=ports['motor-2-socket-14'];A=np.array(fr['shoulder'])+np.array(fr['width'])*2.5*k;B=np.array(to['shoulder'])+np.array(to['width'])*2.5*k;Es=8.5+2.5*k;zf=-18+3*k;Et=-18.6-2*k;Ct=-33-2.5*k;zc=-41.5-2*k
 def controls(X):return[A,[A[0],-68,A[2]],[A[0],-68,zf],[Es,-68,zf],[Es,-68,-55],[Es,-60,-55],[X,-60,-55],[X,-48,-55],[Et,-48,-55],[Et,-61.5,-55],[Et,-61.5,zc],[Et,-68,zc],[Ct,-68,zc],[Ct,-68,B[2]],[B[0],-68,B[2]],B]
 make('ttl-03-02',k,fr,to,controls,30,None)
(D/'joint-right.json').write_text(json.dumps({'status':'candidate shared-port assignment; original topology not changed yet','strands':rows,'physicalAccepted':False,'allObstacleStaticClear':all(r['volumeMm3']<1e-7 for w in rows for r in w['checks'])},indent=2))
