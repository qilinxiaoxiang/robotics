"""Per-position M2x5 replacement investigation; writes only this review directory."""
from pathlib import Path
import json,hashlib,numpy as np,trimesh,sys
D=Path(__file__).resolve().parent;R=D.parent;n={'__file__':str(D/'probe_seats.py')};exec((D/'probe_seats.py').read_text().split('out=[]')[0],n)
data=n['data'];ss=n['ss'];by=n['by'];solid=n['solid'];cyl=n['cyl'];tri=n['tri'];man=n['man'];sample=n['sample'];collisions=n['collisions'];source=n['n']['raw'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();errors=[];rows=[];paths=[];toolrows=[];washers=[]
inputs=[R/'leg-guide-20261006/full-build-data.json',R/'assembly-fasteners.json',R/'fastener-audit/joint-fasteners.json',R/'fastener-audit/joint-stack-measurements.json',R/'fastener-audit/sources/X330_dimension.pdf',R/'fastener-audit/electronics_audit.py',R/'fastener-audit/verify_joint_fasteners.py',D/'probe_seats.py',D/'robotis-leader.glb',R/'head-redesign-20261008/viewer-candidate.json',R/'head-redesign-20261008/camera-retainer/camera-retainer-report.json',R/'head-redesign-20261008/curved-head/curved-head-review.json',R/'head-redesign-20261008/jaw-access/viewer-fragment.json']
# Exact primary published kit CAD screw names and head envelopes.
sc=trimesh.load(D/'robotis-leader.glb',force='scene');official=[]
for nod,length,seat in [('part_0158',4,70.5),('part_0137',6,16.6)]:
 T,k=sc.graph[nod];m=sc.geometry[k].copy().apply_transform(T);m.apply_scale(1000);diam=max(m.extents[[0,2]]);height=m.bounds[1,1]-seat
 assert diam<4 and height<1.72
 official.append({'node':nod,'sourceName':k,'lengthMm':length,'headDiameterMm':float(diam),'headHeightMm':float(height),'nominalShaftTipMm':float(m.bounds[0,1]),'sourceHeadSeatMm':seat})
legstations={}
for mod in data['modules']:
 if mod['id'] not in ['left-leg','right-leg']:continue
 visible=set()
 for op in mod['operations']:
  visible.update(op['add'])
  if op['id'].endswith('-10'):legstations[mod['id']]=sorted(visible);break
selected=[s for s in ss if s.get('spec')=='M2 x 5 TAP'];assert len(selected)==12
cand={key:man(trimesh.load(D/(key+'-m2x6-seat-world.stl'),force='mesh')) for key in ['neck_pitch','lower','right_lower']}
adds={key:cand[key]-solid(key) for key in cand}
for key,motor in [('neck_pitch',13),('lower',7),('right_lower',2)]:
 host=cand[key];mesh=tri(host);assert mesh.is_watertight and len(host.decompose())==1
 if key!='neck_pitch':assert float((solid(key)-host).volume())<1e-5
 else:
  removed=solid(key)-host;allowed=None
  for s in [s for s in selected if s['servo_ids']==[motor]]:
   a=np.array(s['world_center_mm']);v=np.array(s['world_axis']);q=cyl(a-v*(max(s['stack_mm'])+.01),a+v*1.1,1.2);allowed=q if allowed is None else allowed+q
  assert float((removed-allowed).volume())<1e-5
  assert 2<float(removed.volume()) < 4*np.pi*((1.2**2-1.1**2)*2.91+1.1**2*.201)+.05 # four0.2mm membranes plus radius1.1→1.2 bore relief; .05mm³ tessellation margin
 assert collisions(adds[key],[key])=={}
 for s in [s for s in selected if s['servo_ids']==[motor]]:
  lo,hi=s['stack_mm'];old=s['length_mm'];v=np.array(s['world_axis']);a=np.array(s['world_center_mm']);newseat=a+v
  opts=[{'spec':f'M2 x {L} TAP','addedStackMm':w,'entryMm':[L-hi-w,L-lo-w],'manufacturerMaxExceededMm':max(0,L-lo-w-3),'meetsProjectEntryFloor':L-hi-w>1.6,'ownedWasherEstablished':False if w else None} for L,w in [(4,0),(6,0),(6,.5),(6,1)]]
  assert opts[0]['entryMm'][1]<1.6 and opts[1]['manufacturerMaxExceededMm']>.09
  entry=opts[3]['entryMm'];assert min(entry)>1.6 and max(entry)<3
  # Exact-source extension keeps screw tip and motor interface unchanged.
  assert np.max(np.abs(newseat-v*6-(a-v*5)))<1e-10
  head=cyl(newseat+v*.0001,newseat+v*1.72,2);tipshaft=cyl(newseat-v*6,newseat,1);assert collisions(head,[key])=={} and (head^host).volume()<1e-5
  # Only intentional tapping into target motor is excluded; printed holder remains in shaft obstacles.
  screwstation=[key,'motor13','neck_pitch_ring'] if motor==13 else legstations[s['moduleId']]
  obs={k:solid(k) for k in screwstation if k not in [key,f'motor{motor}']};obs[key]=host
  # Empty remote stations are not required: conservative whole final robot is clear for the head route.
  hp=sample({'head':head},{k:solid(k) for k in screwstation if k!=key}|{key:host},v*16,step=.25)
  sp=sample({'shaft':tipshaft},obs,v*16,step=.25)
  if hp['peakContactsMm3'] or sp['peakContactsMm3']:errors.append({'screw':s['id'],'headRoute':hp['peakContactsMm3'],'shaftRoute':sp['peakContactsMm3']})
  paths.append({'id':s['id'],'head':hp,'shaft':sp,'threadReceiverExcludedOnly':f'motor{motor}'})
  # Driver at the allowed fastening station (detached bracket for neck).
  station=screwstation
  tool=cyl(newseat+v*.5,newseat+v*40,1.5);hits={k:float((tool^(host if k==key else solid(k))).volume()) for k in station if (tool^(host if k==key else solid(k))).volume()>1e-5}
  toolrows.append({'id':s['id'],'station':'detached pitch bracket' if motor==13 else 'leg bench before torso joining','shaftDiameterMm':3,'lengthOutwardMm':40,'hits':hits})
  if hits:errors.append({'tool':s['id'],'hits':hits})
  w=cyl(a,a+v*.5,2.5)-cyl(a-v*.1,a+v*.6,1.35);wh=cyl(a+v*.5001,a+v*(.5+1.72),2);whits=collisions(w,[key]);hhits=collisions(wh,[key]);washers.append({'id':s['id'],'spec':'M2 x 6 TAP + DIN433 M2.5 metal washer ID2.7 OD5 thickness0.5 mm','washerContacts':whits,'headContacts':hhits,'entryMm':opts[2]['entryMm'],'availableStockVerified':False,'activeRecommendation':False})
  rows.append({'id':s['id'],'module':s['moduleId'],'printedPart':key,'stockFile':by[key]['stockFile'],'threadType':'M2 tapping into XL330 Ø1.6 blind pilot; machine screw not interchangeable','originalStackMm':s['stack_mm'],'outputMaximumMm':3,'projectEntryFloorMm':1.6,'floorSource':'Existing project gate uses >1.6 mm; not a manufacturer minimum or strength proof','options':opts,'selectedNewBuildSpec':'M2 x 6 TAP','newSeatAdditionMm':1,'seatOuterDiameterMm':5,'seatThroughDiameterMm':2.4,'existingBoreCleanup': 'Open four source0.2mm sacrificial membranes and provide continuousØ2.4 clearance at unchanged axes' if motor==13 else 'No existing bore change','entryMm':entry,'tipMarginMm':3-max(entry),'newHeadSeatWorldMm':newseat.tolist(),'tipUnchanged':True,'reprintPart':key,'currentAssembledAction':'Preserve completed leg; do not replace its links or assert installed screw length' if motor in [2,7] else 'Reprint neck_pitch with four integral seats before this joint is assembled','newHeadEnvelopeMm':[4,1.72],'negativeOriginalBoreMembraneMm3':float((cyl(a-v*5,a,1)^solid(key)).volume()) if motor==13 else 0})
 print(key,'verified hardware routes',flush=True)
# Candidate seat additions follow the source assembly paths; exact whole moving sets remain unchanged.
prior=set()
for mod in data['modules']:
 for op in mod['operations']:
  prior.update(op['add']);moving=op.get('moveKeys',[])
  affected=set(moving)&set(adds)
  if not affected:continue
  fixed=(set(op.get('isolatedPartKeys',prior))&prior)-set(moving);v=op.get('approachVector',[0,0,0]);result=sample({k+'_seat':adds[k] for k in affected},{k:solid(k) for k in fixed},v,step=.25)
  paths.append({'operation':op['id'],'type':'incremental added-seat route','movingFullGroup':moving,'fixed':sorted(fixed),'result':result})
  if result['peakContactsMm3']:errors.append({'operation':op['id'],'addedSeatHits':result['peakContactsMm3']})
# Pressure tips, not screw heads, are the clamp stop for the IMU mount.
imu=[]
for s in [s for s in ss if s.get('groupId')=='imu_clamp']:
 a=np.array(s['world_center_mm']);v=np.array(s['world_axis']);new=a+v;head=cyl(new,new+v*1.72,2);shaft=cyl(new-v*6,new,1)
 hp=sample({'head':head},{k:solid(k) for k in by},v*16,step=.25);sp=sample({'shaft':shaft},{k:solid(k) for k in by if k!='imu_clamp'},v*16,step=.25)
 if hp['peakContactsMm3'] or sp['peakContactsMm3']:errors.append({'imu':s['id'],'head':hp['peakContactsMm3'],'shaft':sp['peakContactsMm3']})
 tool=cyl(new+v*.5,new+v*40,1.5);hits=collisions(tool);assert not hits
 # Radial rays through the actual current holder resolve 4.0 mm material, versus old reported4.2.
 mesh=tri(solid('imu_clamp'));origin=np.array([new+[.9,0,10],new+[-.9,0,10],new+[0,.9,10],new+[0,-.9,10]]);loc,ray,_=mesh.ray.intersects_location(origin,np.tile([0,0,-1],(4,1)));bounds=[sorted(loc[(ray==i)&(loc[:,2]>=29.5),2].tolist()) for i in range(4)];wall=[max(z)-min(z) for z in bounds];assert all(abs(w-4)<1e-4 for w in wall)
 imu.append({'id':s['id'],'newSpec':'M2 x 6 TAP pressure screw; no nut, no washer','newLengthMm':6,'newHeadSeatWorldMm':new.tolist(),'tipWorldMm':(new-v*6).tolist(),'tipContactPlaneZMm':29.5,'holderTopZMm':33.7,'holderBottomZMm':29.7,'headStandOffAtContactMm':1.8,'actualPilotMaterialDepthMm':wall,'radialRayZBoundsMm':bounds,'oldReportedPilotDepthMm':4.2,'requiredCorrection':'4.2 mm includes the 0.2 mm air gap below holder; actual threaded material is4.0mm.','negativeM2x4AtSeatedHead':{'headZMm':33.7,'tipZMm':29.7,'gapAboveRailMm':.2,'result':'head bottoms before tip reaches rail; no pressure clamp'},'negativeM2x6IfHeadSeated':{'tipZMm':27.7,'penetrationIntoRailMm':1.8,'result':'stop by tip contact, not by seating the head'},'reprintRequired':False,'headPath':hp,'shaftPath':sp,'toolContacts':hits,'threadType':'M2 tapping in original1.6mm printed pilot; no interchange claim for a machine screw'})
assert hashlib.sha256(source).hexdigest()==sha(R/'leg-guide-20261006/full-build-data.json')
inputs += list(D.glob('*-m2x6-seat-*.stl'))
sourcehashes={str(p.resolve()):sha(p) for p in inputs+[Path(__file__)]}
report={'problemIds':['P5','P6'],'verifiedDate':'2026-10-08','passed':not errors,'errors':errors,'scope':'M2x5 per-position design replacement and incremental rigid clearance; optional lower links do not reopen completed legs; no strength or physical commissioning certification','sourceDataSha256':hashlib.sha256(source).hexdigest(),'sourceHashes':sourcehashes,'inventory':{'servoM2x5':12,'imuM2x5':2,'currentM2Point5x5':0,'headCandidateM2x5':0},'officialKitGeometry':official,'primarySources':[{'url':'https://docs.robotis.com/interactive/omx/models/leader.glb','meaning':'Exact PTS2_M2X4/6 head geometry; published model is not dimensional inspection of user hardware'},{'url':'https://docs.robotis.com/docs/actuators/dynamixel/x-series/xl330-m288/','legacyOfficialUrl':'https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/','meaning':'Official drawing download entry'},{'url':'https://www.besttechnology.co.jp/modules/knowledge/gate.php/X330_dimension.pdf?way=attach&_noumb&refer=Dynamixel%20XL330-M077&openfile=X330_dimension.pdf','meaning':'ROBOTIS authored drawing28May2020:4xØ1.6 DP3(max), use M2 tapping screw; no minimum engagement specified'}],'servoRows':rows,'imuRows':imu,'washerAlternative':washers,'paths':paths,'tools':toolrows,'hardwareInventoryBoundary':'Kit M2x4/M2x6 availability reported by user; replacement washer stock not established, so no washer is silently allocated. Installed knee lengths remain unknown.','physicalFitVerified':False,'strengthVerified':False,'fullJointRangeVerified':False,'activeMainGuideChanged':False}
(D/'fastener-choice-report.json').write_text(json.dumps(report,indent=2)+'\n')
patch={'schemaVersion':1,'integrationReady':False,'sourceDataSha256':report['sourceDataSha256'],'sourceHashes':sourcehashes,'reportFile':'fastener-choice-report.json','reportSha256':sha(D/'fastener-choice-report.json'),'targetSchema':'per-ID effective fastener overlay; canonical source histories remain unchanged','replacements':[{k:r[k] for k in ['id','module','printedPart','selectedNewBuildSpec','newSeatAdditionMm','entryMm','tipMarginMm','newHeadSeatWorldMm','reprintPart','currentAssembledAction']} for r in rows],'guideOnlyReplacements':[{k:r[k] for k in ['id','newSpec','newLengthMm','newHeadSeatWorldMm','headStandOffAtContactMm','actualPilotMaterialDepthMm','tipContactPlaneZMm','reprintRequired']} for r in imu],'geometryCandidates':{k:{'worldMesh':k+'-m2x6-seat-world.stl','worldMeshSha256':sha(D/(k+'-m2x6-seat-world.stl')),'sourceFrameMesh':k+'-m2x6-seat-source-frame.stl','sourceFrameMeshSha256':sha(D/(k+'-m2x6-seat-source-frame.stl')),'optionalForAlreadyAssembledLeg':k!='neck_pitch'} for k in cand},'noPurchase':True,'preserveCompletedLegs':True,'noBlanketStringReplacement':True,'physicalFitVerified':False}
(D/'fastener-patch-proposal.json').write_text(json.dumps(patch,indent=2)+'\n');print(json.dumps({'passed':not errors,'errors':errors,'rows':len(rows),'imu':len(imu),'paths':len(paths),'tools':len(toolrows),'source':report['sourceDataSha256']},indent=2));raise SystemExit(bool(errors))
