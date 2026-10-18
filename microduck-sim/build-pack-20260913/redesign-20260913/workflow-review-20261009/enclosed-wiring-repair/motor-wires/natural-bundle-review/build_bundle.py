from pathlib import Path
import ast,json,math,hashlib,sys,gc
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;P=M/'slack-packaging';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=(M/'local_route.py').read_text()
for n in ast.parse(s).body:
 if isinstance(n,ast.FunctionDef)and n.name in ['primitives','sample','tube','solid']:exec(ast.get_source_segment(s,n).replace('R=(4. if ix in [3,4,5] else 2.)','R=radii[ix]').replace('r=(.75+.003)/math.cos(math.pi/n)','r=(1.7+.003)/math.cos(math.pi/n)'))
def tube(pts,tans):
 n=32;vs=[];dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))];L=dist[-1]
 for index,(point,t) in enumerate(zip(pts,tans)):
  width=np.cross([1.,0,0],t)
  if np.linalg.norm(width)<.1:width=np.array([0.,0.,1.])
  width/=np.linalg.norm(width)
  if index<50:
   target=np.array([1.,0,0]);target-=np.dot(target,t)*t
   if np.linalg.norm(target)>.1:
    target/=np.linalg.norm(target);u=min(1,dist[index]/8);width=(1-u)*target+u*width;width/=np.linalg.norm(width)
  normal=np.cross(t,width);normal/=np.linalg.norm(normal)
  spread=1.6;r=.757/math.cos(math.pi/n)
  for q in np.arange(n)*2*math.pi/n:vs.append(point+(spread*np.sign(math.cos(q))+r*math.cos(q))*width+r*math.sin(q)*normal)
 faces=[]
 for i in range(len(pts)-1):
  for j in range(n):a=i*n+j;b=i*n+(j+1)%n;faces.extend([[a,b,b+n],[a,b+n,a+n]])
 vs.extend([pts[0],pts[-1]]);st=len(vs)-2;en=st+1
 for j in range(n):faces.extend([[st,(j+1)%n,j],[en,(len(pts)-1)*n+j,(len(pts)-1)*n+(j+1)%n]])
 m=trimesh.Trimesh(vs,faces,process=True);m.fix_normals();assert m.is_volume;return m
top=json.loads((M/'active-topology.json').read_text());inv=json.loads((P/'complete-interface-inventory.json').read_text());manifest=json.loads((P/'mixed-leg-manifest.json').read_text());native=[p for p in json.loads(Path(inv['manufacturerMotorReplacementManifest']).read_text())['parts']if p['motor']==2]
side=sys.argv[1];rid='ttl-05-04'if side=='right'else'ttl-10-09';r=next(r for r in top['routes']if r['id']==rid);fr=top['ports'][r['fromPort']];to=top['ports'][r['toPort']];rows=[]
for i,k in enumerate([0]):
 A=np.array(fr['shoulder'])+np.array(fr['width'])*2.5*k;B=np.array(to['shoulder'])+np.array(to['width'])*2.5*k
 # One common side corridor; only short connector breakouts separate the three conductors.
 outerY=19.5 if side=='right'else 19.2
 sign=1 if side=='right'else -1
 c=[A,A+[0,0,6],[-20.2,-outerY*sign,28],[-20.2,-outerY*sign,-42],[-20.2,-13.5*sign,-42],[-20.2,-13.5*sign,-10],[-20.2,-7.5*sign,-10],[-20.2,-7.5*sign,B[2]],B+[-6,0,0],B]
 radii=[2.5,4,2.5,2.5,2.5,2.5,3,2]
 ps=primitives(c);points,t=sample(ps);mesh=tube(points,t);f=D/f'{rid}-bundle.stl';mesh.export(f);a=solid(mesh);checks=[];hits=[]
 for ob in inv['fixedOriginalObstacleInventory']:
  bb=ob.get('expectedFinalBoundsMm')
  if bb is not None and (np.any(mesh.bounds[1]<np.array(bb)[0])or np.any(np.array(bb)[1]<mesh.bounds[0])):continue
  key=ob['key'];objects=[]
  if key.startswith('motor')and key[5:].isdigit():
   T=np.array(top['ports'][f'motor-{int(key[5:])}-socket-13']['transform'])
   for p in native:
    mm=trimesh.load_mesh(p['file']);mm.apply_transform(T@np.linalg.inv(p['worldTransform']));objects.append((key+'/'+str(p['solid']),mm,p['file']))
  else:
   mm=trimesh.load_mesh(ob['file']);mm.apply_translation(ob.get('importTranslationMm',[0,0,0]));objects=[(key,mm,ob['file'])]
  for key,mm,source in objects:
   if np.any(mesh.bounds[1]<mm.bounds[0])or np.any(mm.bounds[1]<mesh.bounds[0]):continue
   assert mm.is_volume,key;cut=a^solid(mm);v=cut.volume();q={'key':key,'source':source,'sha256':sha(source),'volumeMm3':v,'boundsMm':list(cut.bounding_box())if v>1e-7 else None};checks.append(q)
   if v>1e-7:hits.append(q)
 for p in manifest['parts']:
  if p['routeId']==rid:continue
  bb=np.array(p['expectedFinalBoundsMm'])
  if np.any(mesh.bounds[1]<bb[0])or np.any(bb[1]<mesh.bounds[0]):continue
  mm=trimesh.load_mesh(p['file']);assert mm.is_volume;cut=a^solid(mm);v=cut.volume();q={'key':p['key'],'source':p['file'],'sha256':p['sha256'],'volumeMm3':v,'boundsMm':list(cut.bounding_box())if v>1e-7 else None};checks.append(q)
  if v>1e-7:hits.append(q)
 row={'key':f'{rid}-bundle','routeId':rid,'controls':np.array(c).tolist(),'primitives':ps,'lengthMm':sum(p['lengthMm']for p in ps),'file':str(f),'sha256':sha(f),'boundsMm':mesh.bounds.tolist(),'checks':checks,'hits':hits};rows.append(row);print(row['key'],row['lengthMm'],hits,flush=True)
 del a;gc.collect()
pairs=[]
for i,p in enumerate(rows):
 a=solid(trimesh.load_mesh(p['file']))
 for q in rows[:i]:pairs.append({'a':p['key'],'b':q['key'],'volumeMm3':(a^solid(trimesh.load_mesh(q['file']))).volume()})
report={'status':'Candidate illustration, not a frozen vendor cable shape','rows':rows,'wirePairs':pairs,'passedStatic':all(not p['hits']for p in rows)and all(p['volumeMm3']<1e-7 for p in pairs),'sourceHashes':{str(P/'mixed-leg-manifest.json'):sha(P/'mixed-leg-manifest.json'),str(P/'complete-interface-inventory.json'):sha(P/'complete-interface-inventory.json'),str(Path(__file__)):sha(__file__)}}
(D/f'hip-{side}-bundle.json').write_text(json.dumps(report,indent=2));print('pairs',pairs)
