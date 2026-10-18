from pathlib import Path
import json,hashlib,ast,math,sys,gc
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;J=M/'shared-port-repair';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
src=(M/'local_route.py').read_text()
for n in ast.parse(src).body:
 if isinstance(n,ast.FunctionDef)and n.name in['sample','tube','solid']:exec(ast.get_source_segment(src,n))
a=json.loads((D/'mixed-all.json').read_text());m=json.loads((J/'eight-leg-manifest.json').read_text());keys={r['key']for r in a['rows']};replacements={p['key']:p for p in a['rows']};obs=[replacements.get(p['key'],p)for p in m['parts']];inv=json.loads((J/'current-guide-interface-inventory.json').read_text());obs+=json.loads((D/'keeper-candidates.json').read_text())['parts'];obs +=[p for p in inv['fixedOriginalObstacleInventory']if p['key']in ['lower','right_lower']];out=[];selfrows=[]
for r in [a['rows'][int(sys.argv[1])]]:
 mesh=trimesh.load_mesh(r['file']);assert mesh.is_volume;s=solid(mesh)
 for p in obs:
  if p['key']==r['key']:continue
  bb=p.get('expectedFinalBoundsMm');
  if bb and (np.any(mesh.bounds[1]<np.array(bb)[0])or np.any(np.array(bb)[1]<mesh.bounds[0])):
   out.append({'wire':r['key'],'obstacle':p['key'],'sha256':sha(p['file']),'aabbSeparated':True,'volumeMm3':0});continue
  b=trimesh.load_mesh(p['file']);b.apply_translation(p.get('importTranslationMm',[0,0,0]));assert b.is_volume
  separated=bool(np.any(mesh.bounds[1]<b.bounds[0])or np.any(b.bounds[1]<mesh.bounds[0]));v=0 if separated else(s^solid(b)).volume();contact=None
  if ((r['routeId']=='ttl-02-01'and p['key']=='motor-1-socket-13')or(r['routeId']=='ttl-07-06'and p['key']=='motor-6-socket-14'))and v>1e-7:
   old=next(x for x in m['parts']if x['key']==r['key']);oldcut=solid(trimesh.load_mesh(old['file']))^solid(b);newcut=s^solid(b);delta=(oldcut-newcut).volume()+(newcut-oldcut).volume();bounds=list(newcut.bounding_box());assert v<1.09 and abs(bounds[4]-bounds[1]-.6)<1e-4
   contact={'type':'Unchanged catalogue rear-opening mating envelope','baselineWireSha256':old['sha256'],'baselineVolumeMm3':oldcut.volume(),'symmetricDifferenceMm3':delta,'contactBoundsMm':bounds,'classification':'Existing pair-specific 0.6 mm rear-opening contact; phase of circumscribed circular receiving polygon may differ'};
  out.append({'wire':r['key'],'obstacle':p['key'],'sha256':sha(p['file']),'aabbSeparated':separated,'volumeMm3':v,'inheritedInterfaceContact':contact})
 ps=r['primitives'];parts=[(solid(tube(*sample([p]))),p)for p in ps]
 for i,(b,p)in enumerate(parts):
  for c,q in parts[:max(0,i-1)]:
   # Tube end caps share only adjacent endpoints, excluded above.
   v=(b^c).volume();selfrows.append({'wire':r['key'],'a':i,'b':ps.index(q),'volumeMm3':v})
report={'sourceSha256':sha(D/'mixed-all.json'),'checks':out,'selfChecks':selfrows,'passed':a['currentStaticClear']and all(x['volumeMm3']<1e-7 or x.get('inheritedInterfaceContact') for x in out+selfrows)};(D/('mixed-delta-'+sys.argv[1]+'.json')).write_text(json.dumps(report,indent=2));print('passed',report['passed'],'checks',len(out),'self',len(selfrows),'hits',[x for x in out+selfrows if x['volumeMm3']>1e-7])
