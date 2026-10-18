from pathlib import Path
import ast,json,math,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;J=M/'shared-port-repair';O=M.parents[1]/'roof-wiring-stage/motor-wires/obstacles';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
src=(M/'local_route.py').read_text()
for n in ast.parse(src).body:
 if isinstance(n,ast.FunctionDef)and n.name in['primitives','sample','tube','solid']:exec(ast.get_source_segment(src,n).replace('R=(4. if ix in [3,4,5] else 2.)','R=radlist[ix]'))
top=json.loads((M/'active-topology.json').read_text());obstacles=[json.loads(f.read_text())for f in O.glob('*.json')];native=[p for p in json.loads((M.parent/'ankle-wires/native-motors/manifest.json').read_text())['parts']if p['motor']==2];rows=[];solids=[]
for slot,k in enumerate([-1,0,1]):
 fr=top['ports']['motor-4-socket-14'];to=top['ports']['motor-3-socket-14'];A=np.array(fr['shoulder'])+np.array(fr['width'])*2.5*k;B=np.array(to['shoulder'])+np.array(to['width'])*2.5*k;xx=-18.5-1.6*k;zz=-33.5+1.6*k;yr=-75+1.6*k;yb=-61+1.6*k;yb2=-45+1.6*k;bottom=-58
 def controls(Z):return[A,[xx,A[1],A[2]],[xx,A[1],zz],[xx,yb,zz],[xx,yb,bottom],[xx,yr,bottom],[xx,yr,Z],[B[0],yr,Z],[B[0],yr,bottom],[B[0],yb2,bottom],[B[0],yb2,zz],[B[0],-68.45,zz],[B[0],-68.45,B[2]],B]
 radlist=[2,2,4,4,4,4,4,4,4,2,2,2];Z=-30;p=primitives(controls(Z));Z+=(180-sum(x['lengthMm']for x in p))/2
 try:p=primitives(controls(Z))
 except Exception as e:rows.append({'slot':slot,'failedCorner':str(e),'solvedTop':Z});continue
 # Reject negative straight runs after overlapping fillet trims, not merely nonzero norms.
 pts=np.array(controls(Z));valid=True
 for q in p:
  if q['kind']=='line':
   v=np.array(q['end'])-q['start'];valid &= any(np.dot(v,b-a)>0 and np.linalg.norm(np.cross(v,b-a))<1e-6 for a,b in zip(pts,pts[1:]))
 m=tube(*sample(p));s=solid(m);f=D/f'knee-rear-fold-{slot+1}.stl';m.export(f);hits=[];checks=[]
 for ob in obstacles:
  bb=np.array(ob['expectedFinalBoundsMm'])
  if np.any(m.bounds[1]<bb[0])or np.any(bb[1]<m.bounds[0]):continue
  key=ob['key'];near=[]
  if key.startswith('motor')and key[5:].isdigit():
   T=np.array(top['ports'][f'motor-{int(key[5:])}-socket-13']['transform'])
   for body in native:
    mm=trimesh.load_mesh(body['file']);mm.apply_transform(T@np.linalg.inv(body['worldTransform']));near.append((key+'-solid'+str(body['solid']),mm))
  else:
   mm=trimesh.load_mesh(ob['file']);mm.apply_translation(ob.get('importTranslationMm',[0,0,0]));near=[(key,mm)]
  for label,mm in near:
   if np.any(m.bounds[1]<mm.bounds[0])or np.any(mm.bounds[1]<m.bounds[0]):continue
   assert mm.is_volume;c=s^solid(mm);v=c.volume();checks.append({'key':label,'volumeMm3':v});
   if v>1e-7:hits.append({'key':label,'volumeMm3':v,'boundsMm':list(c.bounding_box())})
 row={'key':f'ttl-04-03-{slot+1}','slot':slot,'controls':pts.tolist(),'primitives':p,'lengthMm':sum(x['lengthMm']for x in p),'boundsMm':m.bounds.tolist(),'file':str(f),'sha256':sha(f),'checks':checks,'hits':hits,'solvedTopZ':Z,'forwardRuns':bool(valid)};rows.append(row);solids.append(s);print(slot,Z,row['lengthMm'],hits,flush=True)
selfs=[{'a':i,'b':j,'volumeMm3':(a^b).volume()}for i,a in enumerate(solids)for j,b in enumerate(solids[:i])]
(D/'knee-rear-fold.json').write_text(json.dumps({'status':'Independent packaging candidate; original routes unchanged','rows':rows,'wireWire':selfs,'candidateClear':len(solids)==3 and all(not r['hits']and r['forwardRuns']for r in rows)and all(r['volumeMm3']<1e-7 for r in selfs),'sourceCenterlinesSha256':sha(J/'eight-leg-centerlines.json')},indent=2));print(selfs)
