from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).parent;O=D.parents[1]/'roof-wiring-stage/motor-wires/obstacles';G=D.parents[2]/'leg-guide-20261006/full-build-data.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def solid(m):
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert str(a.status())=='Error.NoError' and a.volume()>0;return a
source=json.loads((D/'case-keeper.json').read_text());parts=[];data=json.loads(G.read_text())
for side,motor,route,sign in [('right',3,'local-route.json',1),('left',8,'mirror-route.json',-1)]:
 for kind,keys in [('case-anchor',['motor3-case-tie','motor3-case-lock'])]:
  a=None
  for key in keys:
   p=D/(key+'.stl');m=trimesh.load_mesh(p,process=True)
   if sign<0:m.apply_transform(np.diag([1,-1,1,1]))
   b=solid(m);a=b if a is None else a+b
  q=a.to_mesh64();m=trimesh.Trimesh(q.vert_properties,q.tri_verts,process=True);m.fix_normals();assert m.is_watertight
  f=D/f'{side}-{kind}-receiving.stl';m.export(f);checks=[]
  for p in O.glob('*.json'):
   o=json.loads(p.read_text());bb=np.array(o['expectedFinalBoundsMm'])
   if np.any(m.bounds[1]<bb[0])or np.any(bb[1]<m.bounds[0]):continue
   ob=trimesh.load_mesh(o['file']);ob.apply_translation(o.get('importTranslationMm',[0,0,0]));v=(a^solid(ob)).volume();checks.append({'obstacle':o['key'],'sourceSha256':o['sha256'],'overlapMm3':v})
  for w in json.loads((D/route).read_text())['strands']:
   p=Path(w['file']);v=(a^solid(trimesh.load_mesh(p))).volume();checks.append({'obstacle':p.name,'sourceSha256':sha(p),'overlapMm3':v})
  fast=[]
  for s in data['screws']:
   if s.get('moduleId')!=side+'-leg':continue
   c=np.array(s['world_center_mm']);ax=np.array(s['world_axis']);start=c-ax*max(14,s['length_mm']);end=c+ax*3;lo=np.minimum(start,end)-3;hi=np.maximum(start,end)+3
   if np.any(m.bounds[1]<lo)or np.any(hi<m.bounds[0]):continue
   v=(a^mf.Manifold.cube(hi-lo).translate(lo)).volume();actual_start=c-ax*max(6,s['length_mm']);alo=np.minimum(actual_start,end)-3;ahi=np.maximum(actual_start,end)+3;av=(a^mf.Manifold.cube(ahi-alo).translate(alo)).volume();fast.append({'id':s['id'],'long14mmScreenOverlapMm3':v,'conservativeAabbOverlapMm3':av,'actualLengthWith6mmRevisionFloor':max(6,s['length_mm']),'headAndRadiusMarginMm':3})
  row={'key':side+'-'+kind,'file':str(f),'sha256':sha(f),'worldBody':'upper_leg_'+side,'bounds':m.bounds.tolist(),'staticChecks':checks,'fastenerScreen':fast,'staticPassed':all(x['overlapMm3']<1e-7 for x in checks),'fastenerScreenPassed':all(x['conservativeAabbOverlapMm3']<1e-7 for x in fast)};parts.append(row);print(row['key'],row['staticPassed'],fast,flush=True)
out={'status':'CASE_ANCHOR_NEUTRAL_STATIC_CLEAR; flexible service loop adjusted during assembly','wholeHarnessAccepted':False,'sourceHashes':{str(D/'case-keeper.json'):sha(D/'case-keeper.json'),str(G):sha(G),str(D/'local-route.json'):sha(D/'local-route.json'),str(D/'mirror-route.json'):sha(D/'mirror-route.json')},'parts':parts,'materials':{'tiesPerLeg':2,'minimumLengthMmEach':150,'bodyMaxWidthMm':1.8,'bodyMaxThicknessMm':.8,'lockReceivingMm':[5,5,3],'inventory':'Unconfirmed club-supply requirement; existing allocations not reassigned; no purchase released.'},'retentionMeaning':'Primary tie encircles only the knee motor case, on upper-leg body. Its5x5x3 lock is oriented with3mm radialX thickness to avoid the folded ankle. Planned secondary tie loosely gathers the U loops at this anchor; its exact soft shape is adjusted physically, not exported as an accepted rigid sweep. No printed bracket.','assembly':[ 'Before closing the knee rear cover, insert its obstructed motor plug on the bench and place the primary case tie with its lock toward the free outer side.','Lead the cable through the existing lower/side clearance; retain the completed foot and ankle as one assembly. Do not pull a mated plug through a closed cover.','Insert the hip-side plug while its case side remains accessible. Position the three service loops and loosely close the secondary keeper on the same upper-leg anchor.','Check seating, then move the unpowered joints slowly across their intended usable range while redistributing slack. Stop for tension, rubbing or an exposed connector; do not tighten the service loop as a rigid cross-joint restraint.'],'limits':['No material stock assertion or tie pull-strength/life qualification.','Rigid anchor sampled joint result is in retention-motion.json. Flexible keeper shape is intentionally not exported as a fixed rigid object; no rigid soft-loop all-angle claim.','The full source joint-range chord budget is a reach lower bound, not flexible no-collision evidence.']}
(D/'retention-plan.json').write_text(json.dumps(out,indent=2))
