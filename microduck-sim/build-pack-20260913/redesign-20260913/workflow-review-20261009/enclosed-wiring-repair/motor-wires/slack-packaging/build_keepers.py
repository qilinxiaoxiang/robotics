from pathlib import Path
import ast,json,math,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;J=M/'shared-port-repair';O=M.parents[1]/'roof-wiring-stage/motor-wires/obstacles';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
src=(M/'case_keeper.py').read_text()
for n in ast.parse(src).body:
 if isinstance(n,ast.FunctionDef)and n.name in ['solid','contour','ring']:exec(ast.get_source_segment(src,n))
parts={
'right-knee-keeper':ring([-21.5,15.3,-37,-6.5],1.5,.8,2.5).transform([[1,0,0,0],[0,0,1,-56.3],[0,1,0,0]])+mf.Manifold.cube([3,5,5]).translate([13.7,-57.5,-24]),
'right-thigh-frame-keeper':ring([-47.3,17.3,-53.5,-3],1.5,.8,2.5).transform([[1,0,0,0],[0,0,1,-67.25],[0,1,0,0]])+mf.Manifold.cube([4.5,5,3]).translate([16.5,-68.5,-37]),
'right-ankle-slack-keeper':ring([-63,-45.3,-73.5,-59.2],1.5,.8,2.5).translate([0,0,-51.5])+mf.Manifold.cube([3,4.5,4]).translate([-65.2,-68,-52.2]),
}
parts.update({k.replace('right-','left-'):v.transform([[1,0,0,0],[0,-1,0,0],[0,0,1,0]])for k,v in list(parts.items())});rows=[];inventory=json.loads((J/'current-guide-interface-inventory.json').read_text());obs=inventory['fixedOriginalObstacleInventory']+inventory['existingAdjustableTieReceivingBodies'];native=[p for p in json.loads((M.parent/'ankle-wires/native-motors/manifest.json').read_text())['parts']if p['motor']==2];top=json.loads((M/'active-topology.json').read_text());wires=json.loads((J/'eight-leg-manifest.json').read_text())['parts'];repl={r['key']:r for r in json.loads((D/'mixed-all.json').read_text())['rows']};obs +=[repl.get(p['key'],p) for p in wires]
for key,a in parts.items():
 t=a.to_mesh64();m=trimesh.Trimesh(t.vert_properties,t.tri_verts,process=True);assert m.is_volume;f=D/(key+'.stl');m.export(f);checks=[]
 for ob in obs:
  bb=ob.get('expectedFinalBoundsMm',ob.get('boundsMm'));bb=np.array(bb)if bb else None
  if bb is not None and(np.any(m.bounds[1]<bb[0])or np.any(bb[1]<m.bounds[0])):continue
  k=ob['key'];meshes=[]
  if key.endswith('knee-keeper') and k==key.split('-')[0]+'-case-anchor':continue # This ordinary tie is resized/repositioned, not a retained hard obstacle.
  if k.startswith('motor')and k[5:].isdigit():
   T=np.array(top['ports'][f'motor-{int(k[5:])}-socket-13']['transform'])
   for p in native:
    b=trimesh.load_mesh(p['file']);b.apply_transform(T@np.linalg.inv(p['worldTransform']));meshes.append((k+'-solid'+str(p['solid']),b))
  else:
   b=trimesh.load_mesh(ob['file']);b.apply_translation(ob.get('importTranslationMm',[0,0,0]));meshes=[(k,b)]
  for k,b in meshes:
   if np.any(m.bounds[1]<b.bounds[0])or np.any(b.bounds[1]<m.bounds[0]):continue
   assert b.is_volume;cut=a^solid(b);v=cut.volume();checks.append({'key':k,'volumeMm3':v,'boundsMm':list(cut.bounding_box())if v>1e-7 else None})
 row={'key':key,'file':str(f),'sha256':sha(f),'boundsMm':m.bounds.tolist(),'checks':checks,'body':'upper_leg_right'if key.startswith('right')else'upper_leg_left','routeId':('ttl-04-03'if 'knee'in key else'ttl-02-01')if key.startswith('right')else('ttl-09-08'if 'knee'in key else'ttl-07-06'),'role':'Adjustable ordinary cable-tie keeper; not a printed part'};rows.append(row);print(key,'hits',[x for x in checks if x['volumeMm3']>1e-7],flush=True)
(D/'keeper-candidates.json').write_text(json.dumps({'parts':rows,'tiePairs':[{'a':ka,'b':kb,'volumeMm3':(a^b).volume()}for i,(ka,a)in enumerate(parts.items())for kb,b in list(parts.items())[:i]],'accepted':False,'stock':'Club-supply requirement, not verified inventory','receivingTie':{'widthMm':2.5,'thicknessMm':.8,'minimumLengthMm':120,'lockHeadMm':[4.5,4,3]},'adjustment':'Keep loose until manual joint sweep; retain spare folds on upper-leg body, never strap to lower/ankle.'},indent=2))
