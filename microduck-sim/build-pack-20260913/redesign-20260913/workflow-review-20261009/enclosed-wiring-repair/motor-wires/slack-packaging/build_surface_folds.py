"""One bounded packaging edit: turn the two long flat spare U runs up along the leg edge.
Registered terminal strips and existing channel control points are retained.
"""
from pathlib import Path
import ast,json,math,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;J=M/'shared-port-repair';O=M.parents[1]/'roof-wiring-stage/motor-wires/obstacles';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
src=(M/'local_route.py').read_text()
for n in ast.parse(src).body:
 if isinstance(n,ast.FunctionDef)and n.name in['primitives','sample','tube','solid']:exec(ast.get_source_segment(src,n).replace('R=(4. if ix in [3,4,5] else 2.)','R=radlist[ix]'))
old=json.loads((J/'joint-right.json').read_text());top=json.loads((M/'active-topology.json').read_text());obs=[json.loads(f.read_text())for f in O.glob('*.json')];native=[p for p in json.loads((M.parent/'ankle-wires/native-motors/manifest.json').read_text())['parts']if p['motor']==2];rows=[];solids=[]
for w in old['strands']:
 if w['routeId']=='ttl-03-02':continue
 k=w['wireSlot'];c=w['controls'];route=w['routeId']
 if route=='ttl-04-03':
  X=20.2-2.5*k;z=c[4][2];yy=c[4][1]
  def controls(H):return c[:4]+[[X,yy,z],[X,yy-11,z],[X,yy-11,z+H],[X,yy-23,z+H],[X,yy-23,z],[X,yy-12,z]]+c[6:]
  radlist=[2,2,2,4,4,4,4,4,4,4,2,2]
 else:
  X=-57.65-3.25*k;z=c[5][2];yy=c[5][1]
  def controls(H):return c[:5]+[[X,yy,z],[X,yy,z+H],[X,yy-8,z+H],[X,yy-8,z],[X,c[6][1],z],[X,c[7][1],c[7][2]]]+c[8:]
  radlist=[2]* (len(controls(25))-2)
  for ix in[4,5,6,7]:radlist[ix]=3.8
 H=25;p=primitives(controls(H));H+=(180-sum(q['lengthMm']for q in p))/2;assert H>(8 if route=='ttl-04-03'else 7),(w['key'],H);pts=np.array(controls(H));p=primitives(pts);length=sum(q['lengthMm']for q in p);assert abs(length-180)<1e-6
 # Explicit trimming check at every original polyline segment, including two adjacent corners.
 trims=[0]+[radlist[i]*math.tan(math.acos(np.clip(np.dot((b-a)/np.linalg.norm(b-a),(d-b)/np.linalg.norm(d-b)),-1,1))/2)for i,(a,b,d)in enumerate(zip(pts,pts[1:],pts[2:]))]+[0]
 assert all(trims[i]+trims[i+1]<=np.linalg.norm(b-a)+1e-7 for i,(a,b)in enumerate(zip(pts,pts[1:]))),'reversed straight'
 m=tube(*sample(p));f=D/(w['key']+'-surface-fold.stl');m.export(f);a=solid(m);checks=[];hits=[]
 for ob in obs:
  bb=np.array(ob['expectedFinalBoundsMm'])
  if np.any(m.bounds[1]<bb[0])or np.any(bb[1]<m.bounds[0]):continue
  key=ob['key'];meshes=[]
  if key.startswith('motor')and key[5:].isdigit():
   T=np.array(top['ports'][f'motor-{int(key[5:])}-socket-13']['transform'])
   for b in native:
    mm=trimesh.load_mesh(b['file']);mm.apply_transform(T@np.linalg.inv(b['worldTransform']));meshes.append((key+'-solid'+str(b['solid']),mm))
  else:
   mm=trimesh.load_mesh(ob['file']);mm.apply_translation(ob.get('importTranslationMm',[0,0,0]));meshes=[(key,mm)]
  for label,mm in meshes:
   if np.any(m.bounds[1]<mm.bounds[0])or np.any(mm.bounds[1]<m.bounds[0]):continue
   assert mm.is_volume;b=solid(mm);cut=a^b;v=cut.volume();checks.append({'key':label,'sourceSha256':ob['sha256'],'volumeMm3':v})
   if v>1e-7:hits.append({'key':label,'volumeMm3':v,'boundsMm':list(cut.bounding_box())})
 row={**w,'file':str(f),'sha256':sha(f),'primitives':p,'controls':pts.tolist(),'boundsMm':m.bounds.tolist(),'lengthMm':length,'packagingFoldHeightMm':H,'checks':checks,'hits':hits};rows.append(row);solids.append((w['key'],a,m.bounds));print(w['key'],'H',H,'bounds',m.bounds.tolist(),'hits',hits,flush=True)
pairs=[]
for i,(key,a,bounds)in enumerate(solids):
 for key2,b,bb in solids[:i]:
  if np.any(bounds[1]<bb[0])or np.any(bb[1]<bounds[0]):continue
  cut=a^b;v=cut.volume();pairs.append({'a':key,'b':key2,'volumeMm3':v,'boundsMm':list(cut.bounding_box())if v>1e-7 else None})
report={'status':'Independent surface-fold candidate; not published or accepted','rows':rows,'newWirePairs':pairs,'currentStaticClear':all(not r['hits']for r in rows)and all(p['volumeMm3']<1e-7 for p in pairs),'sourceManifestSha256':sha(J/'eight-leg-manifest.json'),'sourceCenterlinesSha256':sha(J/'eight-leg-centerlines.json'),'stockLengthMm':180,'newPrintingRequired':False};(D/'surface-folds-right.json').write_text(json.dumps(report,indent=2));print('pair hits',[p for p in pairs if p['volumeMm3']>1e-7])
