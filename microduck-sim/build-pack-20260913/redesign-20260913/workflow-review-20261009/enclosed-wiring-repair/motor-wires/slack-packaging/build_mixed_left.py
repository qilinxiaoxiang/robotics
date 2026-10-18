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
for w in json.loads((D/'mixed-right.json').read_text())['rows']:
 rid={'ttl-04-03':'ttl-09-08','ttl-02-01':'ttl-07-06'}[w['routeId']];wire_key=rid+'-'+w['key'].split('-')[-1];p=json.loads(json.dumps(w['primitives']));pts=np.array(w['controls'])*[1,-1,1];length=w['lengthMm']
 for q in p:
  for k in ['start','mid','end','center']: 
   if k in q:q[k][1]*=-1
  if 'normal'in q:q['normal']=[-q['normal'][0],q['normal'][1],-q['normal'][2]]
 m=trimesh.load_mesh(w['file']);m.apply_transform(np.diag([1,-1,1,1]));f=D/(wire_key+'-mixed.stl');m.export(f);a=solid(m);checks=[];hits=[]
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
 row={**w,'key':wire_key,'routeId':rid,'file':str(f),'sha256':sha(f),'primitives':p,'controls':pts.tolist(),'boundsMm':m.bounds.tolist(),'lengthMm':length,'checks':checks,'hits':hits};rows.append(row);solids.append((wire_key,a,m.bounds));print(wire_key,'bounds',m.bounds.tolist(),'hits',hits,flush=True)
pairs=[]
for i,(key,a,bounds)in enumerate(solids):
 for key2,b,bb in solids[:i]:
  if np.any(bounds[1]<bb[0])or np.any(bb[1]<bounds[0]):continue
  cut=a^b;v=cut.volume();pairs.append({'a':key,'b':key2,'volumeMm3':v,'boundsMm':list(cut.bounding_box())if v>1e-7 else None})
report={'status':'Independent surface-fold candidate; not published or accepted','rows':rows,'newWirePairs':pairs,'currentStaticClear':all(not r['hits']for r in rows)and all(p['volumeMm3']<1e-7 for p in pairs),'sourceManifestSha256':sha(J/'eight-leg-manifest.json'),'sourceCenterlinesSha256':sha(J/'eight-leg-centerlines.json'),'mixedNominalLengthsMm':[100,180],'newPrintingRequired':False};(D/'mixed-left.json').write_text(json.dumps(report,indent=2));print('pair hits',[p for p in pairs if p['volumeMm3']>1e-7])
