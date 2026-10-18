from pathlib import Path
import ast,json,math,hashlib,sys,gc
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;P=M/'slack-packaging';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=(M/'local_route.py').read_text()
for n in ast.parse(s).body:
 if isinstance(n,ast.FunctionDef)and n.name in ['primitives','sample','tube','solid']:exec(ast.get_source_segment(s,n).replace('R=(4. if ix in [3,4,5] else 2.)','R=2.'))
top=json.loads((M/'active-topology.json').read_text());inv=json.loads((P/'complete-interface-inventory.json').read_text());manifest=json.loads((P/'mixed-leg-manifest.json').read_text());native=[p for p in json.loads(Path(inv['manufacturerMotorReplacementManifest']).read_text())['parts']if p['motor']==2]
side=sys.argv[1];rid='ttl-05-04'if side=='right'else'ttl-10-09';r=next(r for r in top['routes']if r['id']==rid);fr=top['ports'][r['fromPort']];to=top['ports'][r['toPort']];rows=[]
for i,k in enumerate([-1,0,1]):
 A=np.array(fr['shoulder'])+np.array(fr['width'])*2.5*k;B=np.array(to['shoulder'])+np.array(to['width'])*2.5*k
 # One common side corridor; only short connector breakouts separate the three conductors.
 y=(-18+1.6*k)if side=='right'else(18+1.6*k)
 c=[A,A+[0,0,5],[-20,y,27],[-20,y,B[2]],B+[-5.5,0,0],B]
 ps=primitives(c);points,t=sample(ps);mesh=tube(points,t);f=D/f'{rid}-{i+1}-direct.stl';mesh.export(f);a=solid(mesh);checks=[];hits=[]
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
 row={'key':f'{rid}-{i+1}','routeId':rid,'controls':np.array(c).tolist(),'primitives':ps,'lengthMm':sum(p['lengthMm']for p in ps),'file':str(f),'sha256':sha(f),'boundsMm':mesh.bounds.tolist(),'checks':checks,'hits':hits};rows.append(row);print(row['key'],row['lengthMm'],hits,flush=True)
 del a;gc.collect()
pairs=[]
for i,p in enumerate(rows):
 a=solid(trimesh.load_mesh(p['file']))
 for q in rows[:i]:pairs.append({'a':p['key'],'b':q['key'],'volumeMm3':(a^solid(trimesh.load_mesh(q['file']))).volume()})
report={'status':'Candidate illustration, not a frozen vendor cable shape','rows':rows,'wirePairs':pairs,'passedStatic':all(not p['hits']for p in rows)and all(p['volumeMm3']<1e-7 for p in pairs),'sourceHashes':{str(P/'mixed-leg-manifest.json'):sha(P/'mixed-leg-manifest.json'),str(P/'complete-interface-inventory.json'):sha(P/'complete-interface-inventory.json'),str(Path(__file__)):sha(__file__)}}
(D/f'hip-{side}-direct.json').write_text(json.dumps(report,indent=2));print('pairs',pairs)
