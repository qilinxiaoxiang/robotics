"""Publish the finite station review as a strict overlay; never edits the guide."""
import copy,gzip,hashlib,json
from pathlib import Path
from check_delta import data,inventory,D,R,G
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
hashobj=lambda x:hashlib.sha256(canonical(x)).hexdigest()
base,effective,service=data();_,stations=inventory();plan=json.loads((D/'candidate-plan.json').read_text())
originalModules=[service['module'] if m['id']=='torso' else m for m in effective['modules'] if m['id'] in ['left-leg','right-leg','torso','power','imu','neck']]
originalOps={o['id']:o for m in originalModules for o in m['operations']};parts={p['key']:p for p in effective['parts']};screws={s['id']:s for s in effective['screws']}
# Exact lineage for the old all-prior-part report: only the declared IMU vector
# and immutable upstream provenance pointer changed. IMU gets its own positive receipt.
old=json.loads(gzip.decompress((G/'non-head-review/source-before.json.gz').read_bytes()));m=next(m for m in old['modules'] if m['id']=='imu');m['operations'][0]['partApproachVectors']={'imu_board':[-28,0,0],'imu_clamp':[-28,0,0]};old['sourceHashes']['build-pack-20260913/redesign-20260913/assembly-fasteners.json']=base['sourceHashes']['build-pack-20260913/redesign-20260913/assembly-fasteners.json'];assert old==base
historical=[G/'leg-assembly-access.json',G/'nonleg-access-audit.json',G/'foot-approach-stop.json',G/'audit-20261008/leg-final-contacts.json',G/'audit-20261008/nonleg-final-contact-bounds.json',G/'audit-20261008/final-motion-paths.json',G/'non-head-review/remaining-motion-review.json',G/'non-head-review/imu-corrected-path.json',G/'non-head-review/torso-service-verification.json',G/'non-head-review/torso-service-steps.json',R/'fastener-review-20261008/fastener-context-report.json']
for name in ['leg-assembly-access.json','nonleg-access-audit.json']:
 d=json.loads((G/name).read_text());assert d['passed'] and d['dataSha256']==sha(G/'full-build-data.json')
assert json.loads((G/'audit-20261008/final-motion-paths.json').read_text())['crossings']==0
assert json.loads((G/'non-head-review/torso-service-verification.json').read_text())['passed']
M=D.parent/'motor-wires';P=M/'slack-packaging';J=M/'shared-port-repair'
sourceFiles=[G/'full-build-data.json',G/'current_stock_fasteners.py',R/'fastener-review-20261008/fastener-patch-proposal.json',R/'fastener-review-20261008/neck_pitch-m2x6-seat-world.stl',P/'mixed-leg-manifest.json',P/'operation-dependencies.json',P/'INSTALL-SEQUENCE.md',J/'four-preplugged-delta.json',D/'candidate-plan.json',D/'check_delta.py',D/'check_complete_carry.py',D/'check_neck_seat_delta.py',Path(__file__)]+historical
patches=[];review=[]
for row in stations:
 op=row['operation'];oid=op['id'];module=row['moduleId'];changes=copy.deepcopy(plan['operationPatches'].get(oid,{}));changes.pop('addedMotionDeltaKeys',None)
 # The static screw carrier is the same partKey used by checked actual hardware.
 changes.update(priorScrewIds=row['priorScrewIds'],movingScrewIds=row['movingScrewIds'],movingScrewPartKeys={sid:screws[sid]['partKey'] for sid in row['movingScrewIds']})
 refs=[str(G/'leg-assembly-access.json')] if 'leg' in module else [str(G/'nonleg-access-audit.json'),str(G/'non-head-review/remaining-motion-review.json')]
 if module=='torso':refs=[str(G/'non-head-review/torso-service-verification.json')]
 if oid=='imu-01':refs.append(str(G/'non-head-review/imu-corrected-path.json'))
 delta=[]
 if op['screwIds']:delta.append(D/f'{oid}-tool.json')
 if row['movingScrewIds'] and op.get('approachVector') and not op.get('motionWaypoints'):delta.append(D/f'{oid}-complete-carry.json')
 if oid in ['neck-03','neck-07','neck-09','neck-11']:delta.append(D/f'{oid}-seat-delta.json')
 for p in delta:
  rr=json.loads(p.read_text());assert rr['passed'],p
  resource=p.with_name(p.stem.replace('-delta','')+'-resource.json') if p.name.endswith('-seat-delta.json') else p.with_name(p.stem+'-resource.json')
  assert resource.exists(),resource
  guard=json.loads(resource.read_text());assert guard['exitCode']==0 and guard['stoppedByGuard'] is None,(resource,guard)
  assert rr['scriptSha256']==sha(D/('check_neck_seat_delta.py' if p.name.endswith('-seat-delta.json') else 'check_complete_carry.py' if p.name.endswith('-complete-carry.json') else 'check_delta.py'))
  sourceFiles.extend([p,resource,D/'station-inputs'/f'{oid}.json']);refs.append(str(p))
 status='sampled-rigid-path'
 caption='Source-bound rigid placement samples are checked at 0.25 mm spacing. Exact source mating contacts are kept separately; this is not a physical fit or flexible-wire test.'
 if op['screwIds']:
  status='tool-envelope-checked';caption='The stated driver envelope and previously installed screw heads were checked at this assembly station. Bit fit, hand grip and tightening torque still require the real tool.'
 if op.get('requiresPhysicalFit') or (op.get('animationBlockedReason') and not op.get('motionStop')):
  status='physical-fit-checkpoint';caption='This remains a physical fitting checkpoint. No collision-free rigid insertion is claimed. Preserve an already assembled ankle and do not pull a tight joint together with a screw.'
 elif op.get('motionStop'):
  status='measured-contact-stop';caption='The displayed path stops before measured contact and does not reach the seated position. Preserve the already seated foot; do not force the target shown by the source model.'
 elif not op['add'] and not op.get('moveKeys') and not op['screwIds']:
  status='inspection';caption='Inspection step: no insertion path is asserted.'
 changes['motionEvidence']={'status':status,'caption':caption,'receiptRefs':refs,'physicalAssemblyVerified':False,'scope':'Current station and specified rigid parts/hardware only; cables are dressed by hand before closure.'}
 prepare=[('Keep this bench subassembly detached from the rest of the robot.' if op.get('isolatedPartKeys') and module!='torso' else 'Support the assembled parts and keep the access side open.')]
 if op['screwIds']:prepare.append('Prepare '+str(len(op['screwIds']))+' listed screws and the specified compatible driver; retain removed hardware for reuse.' if op.get('screwAction')=='remove' else 'Prepare '+str(len(op['screwIds']))+' listed screws and a compatible driver. Use the existing specified hardware quantities.')
 assemble=[op['text']] if op.get('text') else [op['title']+'.']
 check=['Confirm the intended seats are aligned and no lead is pinched before the next closure.']
 if op.get('beforeClose'):check.extend(op['beforeClose'])
 if op.get('toolAccessModels'):
  for sid,model in op['toolAccessModels'].items():
   direction=('toward the torso center' if module=='torso' else 'outward from the torso')
   prepare.append(f'{sid}: use a right-angle driver with a 3 mm diameter bit, 18 mm axial working projection, and a 6 mm diameter side arm no longer than {model.get("handleLengthMm",50)} mm; orient the arm {direction}.')
  check.append('The long straight-driver handle does not fit here. Confirm the actual compact tool can turn without pressing on the adjacent part.')
 if module in ['left-leg','right-leg']:
  side='Left' if module=='left-leg' else 'Right';n=int(oid[-2:]);prefix='' if module=='left-leg' else 'right_';motor=6 if prefix=='' else 1
  if n==7:check=['Keep the existing completed ankle intact. For a loose build, stop if the sleeve or boss cannot enter freely; this animation does not prove that rigid fit.']
  if n==11:
   changes['title']='Fit the foot on the detached ankle bench'
   assemble=['Keep the lower link, ankle and motor together on the bench. Fit the foot before connecting this unit to the knee. The animation stops before contact; do not use the screw to force the press fit.']
   check=['If the foot is already assembled, preserve it and continue with the intact module. A fresh tight fit remains a separate physical checkpoint.']
  if n==12:
   changes['title']='Secure the foot before the knee connection'
   assemble=['With the ankle-foot module still detached from the thigh, tighten the listed foot retainer after the fit is confirmed. This order leaves room for the driver handle.']
   check=['Retain the whole ankle-foot module. Do not dismantle the already completed foot to repeat this demonstration.']
  if n==9:
   changes['title']='Join the complete ankle-foot module to the knee'
   assemble=['Bring the lower link, ankle, foot, motor, sleeve, washer and their installed screws together along the shown side approach. Dress both motor leads before the knee joint closes.']
   check=['Confirm that the knee output locates squarely in the lower-link seat and the mating faces meet without forcing.', 'Keep the ankle-foot unit intact. Check that the connected leads retain a gentle service loop and stay clear of the joint and screw seats.']
  if n==10:
   assemble=['Preserve the completed leg. Its confirmed M2×6 knee screws nominally enter 3.2 mm through the original 2.8 mm seat, exceeding the 3 mm manufacturer depth limit. This is not proof of damage and is not an accepted fresh-build stack.']
   check=['Keep the installed ankle and foot intact. The existing knee screw stack remains a separate physical repair decision; this motion review does not clear it.']
  if n==14:check=['Complete these yaw-output screws on the detached bench before the roll motor hides the driver direction.']
  if n==18:check=['Complete the pitch-output screws while the yaw/roll module is still separate; join that module only in the following operation.']
  if n in [13,15]:prepare.append('Insert the identified motor plugs before seating this motor, following the linked regional cable action. Guide the flexible leads by hand; they do not translate as a rigid final-shaped bundle.')
 if oid=='neck-04':assemble=['Use the revised integral-seat neck-pitch bracket with four M2×6 TAP screws and no separate neck spacers. Complete them on this detached bench before joining ID11.']
 if oid=='imu-02':assemble=['Use the two M2×6 TAP pressure screws. Stop when each tip contacts the rail; keep the 1.8 mm head stand-off instead of driving the heads flush.']
 if module=='torso' and oid=='torso-service-01':prepare.insert(0,'Use the removal branch only for a hip already fastened. Do not assemble these seven connections merely to remove them; the loose torso core begins at the named preparation operation.')
 # Keep all inserted prose English; legacy source field remains bound but is not rendered as the new instruction.
 changes['tutorial']={'prepare':prepare,'assemble':assemble,'check':check}
 if any(ord(ch)>127 and '\u4e00'<=ch<='\u9fff' for text in assemble for ch in text):raise AssertionError(('Chinese source instruction',oid))
 if oid in plan['operationPatches'] or oid in ['neck-04','imu-02','left-leg-10','right-leg-10']:
  changes['text']=' '.join(assemble)
 patches.append({'moduleId':module,'operationId':oid,'expectedOperationSha256':hashobj(originalOps[oid]),'set':changes})
 review.append({'operationId':oid,'moduleId':module,'status':status,'newReceipts':[str(p) for p in delta]})
# All operation ordering and preplug statements continue to consume the frozen mixed wiring sources.
for side in ['left','right']:
 order=plan['moduleOrders'][side+'-leg'];assert order.index(side+'-leg-12')<order.index(side+'-leg-09')
assert all(json.loads((D/'negative-original-order'/f'{s}-leg-12-tool.json').read_text())['passed'] is False for s in ['left','right'])
sourceFiles=list(dict.fromkeys(sourceFiles));out={'schemaVersion':1,'id':'non-head-motion-completion-20261009','integrationReady':True,'problemIds':['P5','P6'],'sourceDataSha256':sha(G/'full-build-data.json'),'operationHashEncoding':'json.dumps(sort_keys=True,separators=(comma,colon),ensure_ascii=True,allow_nan=False).encode(utf-8)','moduleOrders':plan['moduleOrders'],'operationPatches':patches,'sourceHashes':{str(p.resolve()):sha(p) for p in sourceFiles},'physicalAssemblyVerified':False,'completeRigidAssemblyPathVerified':False,'acceptanceScope':'Digital operation order, explicit retained hardware and specified tool receiving envelopes. Existing ankle/foot fit and user-installed knee fastener stack remain unresolved; no new printed part or forced dismantling is introduced.'}
(D/'assembly-motion-overlay.json').write_text(json.dumps(out,indent=2)+'\n')
summary={'passedDigitalDelta':True,'operations':len(patches),'toolStations':sum(bool(r['operation']['screwIds']) for r in stations),'toolScrews':sum(len(r['operation']['screwIds']) for r in stations),'completeCarriedHardwarePaths':7,'integralNeckSeatDeltaPaths':4,'sourceLineageExactExceptDeclaredImuVectorAndProvenance':True,'wholeAssemblyAccepted':False,'operationsReview':review,'overlaySha256':sha(D/'assembly-motion-overlay.json'),'limits':out['acceptanceScope']}
(D/'acceptance.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='operationsReview'}))
