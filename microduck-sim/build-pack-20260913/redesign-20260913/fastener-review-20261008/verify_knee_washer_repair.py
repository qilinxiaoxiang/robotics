"""Preserve completed legs: one-at-a-time 0.5mm metal washer correction for installed M2x6."""
from pathlib import Path
import json,hashlib,numpy as np,trimesh,math
D=Path(__file__).resolve().parent;R=D.parent;n={'__file__':str(D/'probe_seats.py')};exec((D/'probe_seats.py').read_text().split('out=[]')[0],n)
solid=n['solid'];tri=n['tri'];cyl=n['cyl'];sample=n['sample'];data=n['data'];by=n['by'];ss={s['id']:s for s in data['screws']};mods={m['id']:m for m in data['modules']};sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[];errors=[];washers={};extra=[];steps=[]
ids=[s['id'] for s in data['screws'] if s['spec']=='M2 x 5 TAP' and s['moduleId'] in ['left-leg','right-leg']];assert len(ids)==8
# Only user-reported installed length changes; actual damage/seating status is not inferred.
for sid in ids:ss[sid]['length_mm']=6;ss[sid]['spec']='M2 x 6 TAP'
def bolt(sid,washer=0):
 s=ss[sid];v=np.array(s['world_axis']);a=np.array(s['world_center_mm'])+v*(washer if sid in ids else s.get('washer_mm',0));diam=2.6 if s['spec'].startswith('M2.6') else 2
 return cyl(a-v*s['length_mm'],a,diam/2)+cyl(a,a+v*1.72,2)
hardware={s['id']:bolt(s['id']) for s in data['screws'] if s['moduleId'] in ['left-leg','right-leg']}
for sid in ids:
 s=ss[sid];mid=s['moduleId'];key='lower' if mid=='left-leg' else 'right_lower';motor=s['partKey'];a=np.array(s['world_center_mm']);v=np.array(s['world_axis']);partkeys=mods[mid]['ownedPartKeys'];fixed={k:solid(k) for k in partkeys};fixed.update({'screw:'+q:h for q,h in hardware.items() if q!=sid and ss[q]['moduleId']==mid});fixed.update(washers)
 # A Ø4 envelope contains the measured Ø3.49945 published kit head.
 oldhead=cyl(a+v*.0001,a+v*1.72,2);oldshaft=cyl(a-v*6,a,1);newhead=cyl(a+v*.5001,a+v*(.5+1.72),2);newshaft=cyl(a+v*.5-v*6,a+v*.5,1)
 washer=cyl(a,a+v*.5,2)-cyl(a-v*.1,a+v*.6,1.1)
 removehead=sample({'screw_head':oldhead},fixed,[0,0,0],v*12,step=.25)
 removeshaft=sample({'screw_shaft':oldshaft},{k:q for k,q in fixed.items() if k!=motor},[0,0,0],v*12,step=.25)
 washerpath=sample({'washer':washer},fixed,v*12,step=.25)
 addhead=sample({'screw_head':newhead},fixed|{'new_washer':washer},v*12,step=.25)
 addshaft=sample({'screw_shaft':newshaft},{k:q for k,q in fixed.items() if k!=motor}|{'new_washer':washer},v*12,step=.25)
 tool=cyl(a+v*1,a+v*40.5,1.5);th={k:float((tool^q).volume()) for k,q in fixed.items() if (tool^q).volume()>1e-5}
 for name,path in [('removeHead',removehead),('removeShaft',removeshaft),('insertWasher',washerpath),('refastenHead',addhead),('refastenShaft',addshaft)]:
  if path['peakContactsMm3']:errors.append({'id':sid,'phase':name,'contacts':path['peakContactsMm3']})
 if th:errors.append({'id':sid,'tool':th})
 # Head remains supported even at maximum0.17mm radial play for nominalØ2 shank.
 # Nominal centered area: actual head circle minus washer bore circle.
 hd=3.4994456;bearing=math.pi*((hd/2)**2-1.1**2);bearing_m2=math.pi*((hd/2)**2-1.1**2)
 clearances=[]
 # Check user-compatible alternative dimensional envelopes and lateral play for selected documented washer.
 T=trimesh.geometry.align_vectors([0,0,1],v);u,w=T[:3,0],T[:3,1]
 for theta in np.linspace(0,2*np.pi,17)[:-1]:
  offset=(u*np.cos(theta)+w*np.sin(theta))*.17;shape=washer.translate(offset);hits={k:float((shape^q).volume()) for k,q in fixed.items() if (shape^q).volume()>1e-5};clearances.append({'offsetWorldMm':offset.tolist(),'hits':hits})
  # Deliberately retain these impossible unconstrained poses as negative controls.
  # They are not accepted seated poses: the receiving recess constrains centering.
 envelope=cyl(a,a+v*.6,2.1)-cyl(a-v*.1,a+v*.7,1.0)
 constrained=sample({'washerToleranceEnvelope':envelope},fixed,v*12,step=.25)
 if constrained['peakContactsMm3']:errors.append({'id':sid,'phase':'constrainedWasherToleranceEnvelope','contacts':constrained['peakContactsMm3']})
 altern=[]
 for inner,outer in [(2.2,4),(2.2,5),(2.7,5)]:
  q=cyl(a,a+v*.5,outer/2)-cyl(a-v*.1,a+v*.6,inner/2);hits={k:float((q^o).volume()) for k,o in fixed.items() if (q^o).volume()>1e-5};altern.append({'insideDiameterMm':inner,'outsideDiameterMm':outer,'thicknessMm':.5,'contacts':hits,'centeredHeadBearingAreaMm2':math.pi*((hd/2)**2-(inner/2)**2),'exactStockVerified':False})
 meshfile='washer-'+sid+'-world.stl';mesh=tri(washer);assert mesh.is_watertight and len(washer.decompose())==1;mesh.export(D/meshfile);wk='washer_repair_'+sid.replace('-','_');washers[wk]=washer;hardware[sid]=bolt(sid,.5)
 extra.append({'key':wk,'name':'Knee small-OD M2 metal washer ID2.2 OD4 x0.5 mm','mesh':meshfile,'meshSha256':sha(D/meshfile),'partKind':'fastener','fastenerId':sid,'color':'#aaaaaa','stackIndex':0})
 rows.append({'id':sid,'module':mid,'partKey':key,'installedLengthMm':6,'installedEvidence':'User explicitly confirmed M2x6 in already assembled legs on2026-10-08','oldNominalEntryMm':3.2,'manufacturerMaximumMm':3,'originalOverdepthMm':.2,'repairSpec':'M2 x 6 TAP + small-OD M2 metal washer ID2.2 OD4 x0.5 mm','newLengthMm':6,'newWorldCenterMm':a.tolist(),'newHeadSeatWorldMm':(a+v*.5).tolist(),'newWasherMm':.5,'newStackMm':s['stack_mm'],'newEntryMm':[2.7,2.7],'nominalDepthMarginMm':.3,'washerDrawingThicknessRangeMm':[.4,.6],'entryOverDrawingThicknessRangeMm':[2.6,2.8],'minimumDepthMarginOverWasherThicknessRangeMm':.2,'headActualModelDiameterMm':hd,'washerInsideMm':2.2,'washerOutsideMm':4,'centeredHeadBearingAreaMm2':bearing,'centeredM2WasherBearingAreaMm2':bearing_m2,'washerDimensionsMm':{'inner':2.2,'outer':4,'thickness':.5},'washersPerScrew':1,'maximumAcceptedCenterOffsetMm':.1,'constrainedWasherPath':constrained,'drawingMaximumRadialPlayMm':.17,'washerAlternatives':altern,'washerLateralChecks':clearances,'completeRetainedLegPartKeys':partkeys,'retainedScrewIds':[q for q in hardware if q!=sid and ss[q]['moduleId']==mid],'removeHead':removehead,'removeShaft':removeshaft,'insertWasher':washerpath,'refastenHead':addhead,'refastenShaft':addshaft,'driverContacts':th,'threadReceiverExcluded':motor,'noReprintRequired':True,'ankleOrFootDisassemblyRequired':False,'damageAssessment':'Length and nominal stack imply excessive seated depth; actual damage or seating cannot be inferred.'})
 steps.append({'id':'repair-'+sid,'screwId':sid,'station':'complete detached '+mid+' supported on bench, before torso/power support installation','visiblePartKeys':partkeys,'screwCountRemovedAtOnce':1,'removeTranslationWorldMm':(v*12).tolist(),'action':'Support the lower link without changing its pose. Remove this single screw; keep the other three knee-output screws and all other leg fasteners installed. Place one correctly dimensioned0.5mm metal washer under the head; reinstall the same M2x6 TAP screw to its existing seat. Check the washer is flat and centered and the link remains seated before proceeding to the next screw.','mustNotRemove':['ankle interface','foot interface','other three knee-output screws simultaneously'],'check':'No gap at output interface, washer flat, no forced tightening; with power disconnected check unobstructed joint motion before powering.'})
 print(sid,'checked',flush=True)
# After-torso alternative is deliberately rejected: the support blocks tools.
negative=[]
for row in rows:
 s=ss[row['id']];a=np.array(s['world_center_mm']);v=np.array(s['world_axis']);tool=cyl(a+v*1,a+v*40.5,1.5);vol=float((tool^solid('power_support')).volume());negative.append({'id':row['id'],'powerSupportToolOverlapMm3':vol})
assert sum(r['powerSupportToolOverlapMm3']>1e-5 for r in negative)>=4
r={'problemIds':['P5','P6'],'verifiedDate':'2026-10-08','integrationReady':False,'passed':not errors,'errors':errors,'sourceDataSha256':sha(R/'leg-guide-20261006/full-build-data.json'),'sourceHashes':{str(p.resolve()):sha(p) for p in [Path(__file__),D/'probe_seats.py',R/'leg-guide-20261006/full-build-data.json',R/'fastener-audit/sources/X330_dimension.pdf',D/'robotis-leader.glb',D/'JC-B4D10-SS304-washers.pdf']+[D/x['mesh'] for x in extra]},'currentUserEvidence':'User confirms already-installed knee screws are M2x6; no inference of damage, actual head seating or existing washer stock','conditionalFitRequirement':'Only the exact bounded metal washer dimensions with flat seating inside the original recess; maximum accepted eccentricity0.10mm. The bore permits0.17mm unconstrained play, but those poses collide with the recess and are rejected. If washer will not lie flat without forcing, do not tighten or substitute larger OD. Physical stock and printed recess remain unverified.','unconstrainedBorePlayAccepted':False,'selectedRepair':'Conditional: keep original assembled knee/lower/ankle/foot geometry; add one0.5mm metal washer under each of8 existing knee M2x6 TAP screw heads, one screw at a time on complete-leg bench','rows':rows,'steps':steps,'additionalParts':extra,'removedParts':[],'replacementMeshes':{},'washerQuantity':8,'newScrewQuantity':0,'requiredWasherStockVerified':False,'purchaseAuthorized':False,'primaryWasherDrawing':{'url':'https://www.jcfasteners.com/wp-content/uploads/DIN-433-Small-OD-Washer-B4D10-SS304.pdf','partNumber':'B4D1002001','standard':'** variant per NF-E25-513/514 in DIN433 small-OD catalogue; not genericDIN433M2','material':'SS304','nominalMm':{'ID':2.2,'OD':4,'thickness':.5},'IDRangeMm':[2.2,2.34],'ODRangeMm':[3.64,4],'thicknessRangeMm':[.4,.6],'verified':'2026-10-08','availability':'Drawing establishes dimensions only; source calls nonpreferred sizes potentially limited. Actual available stock unverified.'},'negativeAfterTorsoInstalled':negative,'headBearingBoundary':'Area is nominal geometric overlap, not washer bending/load/torque certification. Published head CAD does not inspect actual received screws. Use metal, not a printed shim.','newLowerLinkAlternative':'Integral-seat lower links are validated for a new build. Replacing already assembled lower links would reopen captured ankle interfaces; no force-fit-preserving replacement sequence has been validated.','physicalFitVerified':False,'strengthVerified':False,'samplingMm':.25,'readiness':'Conditional digital review only; not adopted as current main-guide default. Identify8 exact metal washers and confirm each original recess permits flat seating before execution. Strength and real screw/recess tolerances remain unverified.'}
assert r['sourceDataSha256']==hashlib.sha256(n['n']['raw']).hexdigest();(D/'knee-washer-repair.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':r['passed'],'errors':errors,'screws':len(rows),'paths':len(rows)*5,'samples':49,'driverChecks':len(rows)},indent=2));raise SystemExit(bool(errors))
