from pathlib import Path
import json,hashlib,time
import numpy as np,trimesh
D=Path(__file__).resolve().parent;W=D.parents[1];R=D.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=json.loads((D/'manifest.json').read_text());base=json.loads((W/'original-body-converter/fusion-import-manifest.json').read_text());obs={p['key']:p for p in base['parts']}
roof=D.parent/'roof/head-cap-roof-restored-candidate-world.stl'
obs['head_cap']={'key':'head_cap','file':str(roof),'importTranslationMm':[0,0,0]}
selected=list(obs)
# Replace invalid original OpenRB mesh with source-bound conservative component hulls.
selected.remove('openrb')
H=R/'head-redesign-20261008'
om=H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'
for c in json.loads(om.read_text())['components']:
 key='openrb_component_'+str(c['index']);obs[key]={'file':c['mesh'],'expectedFinalBoundsMm':c['bounds']};selected.append(key)
# Deliberately bounded static screen. Missing objects are explicit, not skipped passes.
rows=[];checks=[];hashes={str(D/'manifest.json'):sha(D/'manifest.json')};start=time.time()
for p in m['parts']:
 if not p['key'].startswith('i2s_'):continue
 wire=trimesh.load(p['file'],force='mesh',process=True);hashes[p['file']]=sha(p['file'])
 checks.append({'key':p['key'],'watertight':bool(wire.is_watertight),'windingConsistent':bool(wire.is_winding_consistent),'volumeMm3':float(wire.volume),'boundsMm':wire.bounds.tolist(),'faces':len(wire.faces)})
 if not wire.is_volume:
  rows.append({'wire':p['key'],'status':'INVALID_WIRE_NO_BOOLEAN'});continue
 for key in selected:
  if key not in obs:
   rows.append({'wire':p['key'],'obstacle':key,'status':'MISSING_FROM_CURRENT_MANIFEST'});continue
  q=obs[key]
  if key==p['key']:
   rows.append({'wire':p['key'],'obstacle':key,'status':'OWN_IDENTICAL_INSTANCE_NOT_OBSTACLE'});continue
  bounds=q.get('expectedFinalBoundsMm')
  if bounds is not None and (np.any(wire.bounds[1]<np.array(bounds)[0]) or np.any(np.array(bounds)[1]<wire.bounds[0])):
   rows.append({'wire':p['key'],'obstacle':key,'status':'AABB_SEPARATE'});continue
  mesh=trimesh.load(q['file'],force='mesh',process=True);mesh.apply_translation(q.get('importTranslationMm',[0,0,0]));hashes[q['file']]=sha(q['file'])
  if np.any(wire.bounds[1]<mesh.bounds[0]) or np.any(mesh.bounds[1]<wire.bounds[0]):status={'status':'AABB_SEPARATE'}
  elif not mesh.is_volume:status={'status':'INVALID_OBSTACLE_NO_BOOLEAN','watertight':bool(mesh.is_watertight),'windingConsistent':bool(mesh.is_winding_consistent)}
  else:
   try:
    inter=trimesh.boolean.intersection([wire,mesh],engine='manifold');empty=len(inter.faces)==0
    status={'status':'EMPTY_INTERSECTION' if empty else 'INTERSECTION' if inter.is_volume else 'INVALID_BOOLEAN_RESULT','intersectionMm3':0 if empty else float(inter.volume),'resultValid':bool(empty or inter.is_volume)}
   except Exception as e:status={'status':'BOOLEAN_ERROR','error':str(e)}
  rows.append({'wire':p['key'],'obstacle':key,**status});del mesh
  (D/'local-check-progress.json').write_text(json.dumps({'complete':False,'rows':rows},indent=2))
 del wire
r={'scope':'Bounded current static screen only; no articulation, self, complete obstacle, connector seating or physical acceptance','complete':True,'expectedWireCount':len(checks),'expectedObstacleKeys':selected,'expectedPairs':len(checks)*len(selected),'records':rows,'meshReadback':checks,'sourceHashes':hashes,'elapsedSeconds':time.time()-start,'wholeHarnessAccepted':False}
(D/'i2s-repair-check.json').write_text(json.dumps(r,indent=2));print(json.dumps({'rows':len(rows),'intersections':[x for x in rows if x['status']=='INTERSECTION'],'invalid':[x for x in rows if 'INVALID' in x['status']],'elapsedSeconds':r['elapsedSeconds']}))
