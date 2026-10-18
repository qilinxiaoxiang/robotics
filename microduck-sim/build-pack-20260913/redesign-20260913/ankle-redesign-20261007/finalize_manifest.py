from pathlib import Path
import json,base64,hashlib,numpy as np,trimesh,manifold3d as mf
from scipy.spatial.transform import Rotation
R=Path(__file__).resolve().parent;G=R.parent/'leg-guide-20261006';SIM=R.parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def finalize(manifest):
 d=json.loads((G/'full-build-data.json').read_text());rows={p['key']:p for p in d['parts']};identities={}
 for side in ['left','right']:
  s=manifest['sides'][side];T=np.array(s['frameWorld']);outward=T[:3,:3]@np.array([0,0,1]);lower='lower' if side=='left' else 'right_lower';motor='motor6' if side=='left' else 'motor1';washer='washer6' if side=='left' else 'washer1';foot='foot' if side=='left' else 'right_foot';base=side+'_base';cap=side+'_cheek';ring=side+'_sleeve';sid=6 if side=='left' else 1
  s['contextKeys']=[lower,motor,washer,foot];s['sourceScrews']=[q for q in d['screws'] if sid in q.get('servo_ids',[]) or q['id']==side+'-foot-retainer']
  s['fasteners']=[]
  screwOutward=T[:3,:3]@np.array([0,1,0]);Ry=Rotation.from_euler('x',-90,degrees=True).as_matrix()
  for i,x in enumerate([-12.,12.],1):
   key=f'{side}_cheek_screw{i}';local=[x,6.,4.5];center=T[:3,:3]@local+T[:3,3];a=mf.Manifold.cylinder(8,1,1,48).transform(np.c_[Ry,[x,-2.,4.5]])+mf.Manifold.cylinder(1.72,2,2,48).transform(np.c_[Ry,[x,6.,4.5]]);mm=a.to_mesh();m=trimesh.Trimesh(np.asarray(mm.vert_properties)[:,:3],np.asarray(mm.tri_verts),process=True).apply_transform(T);stl=R/'STL'/f'{side}-cheek-screw{i}-world.stl';m.export(stl)
   s['parts']=[p for p in s['parts'] if p['key']!=key]
   s['parts'].append({'key':key,'name':'Black M2 × 8 TAP side screw','color':'#303238','stl':str(stl),'coordinateFrame':'guide-world-mm','geometryKind':'Specified installation envelope; TAP threads not explicitly modelled.'})
   s['fasteners'].append({'key':key,'spec':'M2 x 8 TAP','packet':'PHS_M2X08_TAP_K','quantity':1,'length':8.,'headDiameter':4.,'headHeight':1.72,'center':center.tolist(),'axis':screwOutward.tolist(),'axisConvention':'Outward; screw insertion is -axis','headSeatLocal':local,'tipLocal':[x,-2.,4.5],'headSeatWorld':center.tolist(),'tipWorld':(T[:3,:3]@np.array([x,-2.,4.5])+T[:3,3]).tolist(),'clearanceDiameter':2.3,'clearanceLength':4.5,'clampedMaterialLength':4.,'openRegisterSlotLength':.5,'pilotDiameter':1.6,'pilotDepth':4.,'pilotYLocal':[-2.5,1.5],'engagement':3.5,'blindPilotReserve':.5,'baseBackYAtPilot':-4.5,'tipToOuterExit':2.5,'blindEndToOuterWall':2.,'interfacingParts':[cap,base],'pilotMinimumRadialWallBeforeThread':1.2,'nominalWallAfterTwoMmThread':1.,'washer':None,'driverDiameter':3.5,'driverReach':15.,'typeWarning':'Use black PHS_M2X08_TAP_K self-tapping screws. Machine-thread screws are not equivalent. No locking torque or material strength is certified.'})
  prep=[lower,motor];ringed=prep+[washer,ring];seated=ringed+[base];closed=seated+[cap]
  step=lambda title,text,keys,from_v,visible,fast=[]:{'title':title,'text':text,'movingKeys':keys,'from':from_v,'to':[0.,0.,0.],'visibleKeys':visible,'fasteners':fast}
  s['steps']=[
   step('Fit the lower link to the bare motor','Prepare this pair off the knee. Align the locating pegs with the case before tightening.',[lower],(outward*12).tolist(),prep),
   step('Fasten the two case corners','Use the existing two case screws; the new bracket is still off.',[],[0,0,0],prep,['2 × M2 × 10 TAP case screws']),
   step('Place the metal rear washer','Put the existing 0.5 mm metal washer at the rear centre. It is separate from the black printed sleeve.',[washer],(outward*8).tolist(),prep+[washer]),
   step('Retain the rear centre','Use the original rear-centre screw through that washer. Keep hand snug.',[],[0,0,0],prep+[washer],['1 × M2.6 × 8 TAP + 0.5 mm metal washer']),
   step('Slide on the new black sleeve','The new 10.4 mm bore clears the nominal 10 mm boss. The sleeve can float; do not glue it or force a press fit.',[ring],(outward*12).tolist(),ringed),
   step('Bring the complete pair into the open base','With the removable cheek off, lower the motor, link, sleeve and washer together from above.',[lower,motor,ring,washer],[0,0,30],seated),
   step('Start the four output screws loosely','Use the unchanged motor-output holes. Leave them loose until the cheek registers.',[],[0,0,0],seated,['4 × M2 × 4 TAP output screws']),
   step('Close the removable cheek','Slide the two straight guide tongues down the open-top side slots. Check that the ring is seated and the orange side closes without force.',[cap],(outward*12).tolist(),closed),
   step('Retain the removable side','Use two black PHS_M2X08_TAP_K screws from above. These lock the side to the base and leave the sleeve free.',[f'{side}_cheek_screw1',f'{side}_cheek_screw2'],(screwOutward*10).tolist(),closed+[f'{side}_cheek_screw1',f'{side}_cheek_screw2'],['2 × M2 × 8 TAP · PHS_M2X08_TAP_K black screws']),
   step('Seat evenly, then hand snug','Check alignment and free manual joint movement with torque off before final tightening. No calibrated torque or physical fit is established here.',[],[0,0,0],closed+[f'{side}_cheek_screw1',f'{side}_cheek_screw2'],['Finish the previously started 4 output screws; check case/rear retainers']),
   step('Reuse the yellow foot','Its original hole and axle interface are retained. Use the existing single foot retainer; follow the main guide for its placement.',[],[0,0,0],closed+[foot,f'{side}_cheek_screw1',f'{side}_cheek_screw2'],['1 × M2 × 6 TAP foot retainer'])]
  s['steps'][0]['pathStatus']='Original lower/motor nominal contact retained; this step is not a strict zero-overlap certificate.'
  s['steps'][5]['pathStatus']='Candidate package path tested against open base; right retains the original thin source mating-face contact.'
  s['steps'][8]['pathStatus']='TAP screw insertion deliberately engages printed pilot material; threads shown as a cylinder envelope.'
  s['joint']={'movingKeys':[base,cap,foot,f'{side}_cheek_screw1',f'{side}_cheek_screw2'],'fixedKeys':[lower,motor,washer],'axis':[0.,1. if side=='left' else -1.,0.],'center':[-31.7771,64.5 if side=='left' else -64.5,-81.5],'limits':[-90.,90.],'unit':'degrees','note':'Source simulation limits are shown for comparison. Original bracket already collides at some extremes; candidate must not be presented as a collision-free ±90° joint. Motor output horn rotates with ankle, while its case stays with lower; the context mesh includes both.'}
  s['fitNote']='New sleeve OD14.6 / ID10.4 / width2.8 mm. Both inner and outer interfaces are sliding clearances; nominal combined radial float about0.4 mm. Captured axially, not glued to the link. Actual printed clearance and stiffness are unverified.'
  s['statusNote']='Digital prototype only. Existing lower link, motor, foot and washer retained; base/cheek/sleeve are replacement prints, not instructions to cut current stock.'
  s['fastenerSummary']='Reuse original 2 case + 1 rear/washer + 4 output + 1 foot screws. Add only 2 black M2×8 TAP (PHS_M2X08_TAP_K) removable-side screws per side.'
  s['checkSummary']='Compare the blocked original bracket with the open-base package approach; fit and movement still require physical checks.'
  for k in s['contextKeys']+[('ankle' if side=='left' else 'right_ankle'),('smallring' if side=='left' else 'right_smallring')]:
   p=rows[k];identities[k]={'sourceId':p['sourceId'],'sourceTransformWorld':p['sourceTransformWorld'],'positionSha256':hashlib.sha256(base64.b64decode(p['positionB64'])).hexdigest(),'indexSha256':hashlib.sha256(base64.b64decode(p['indexB64'])).hexdigest()}
  for p in s['parts']:
   if p['key']==base:p['name']=side.title()+' orange ankle base'
   elif p['key']==cap:p['name']=side.title()+' removable orange side'
   elif p['key']==ring:p['name']=side.title()+' black sliding sleeve'
   p['stlSha256']=sha(p['stl'])
 manifest['sourceMeshIdentities']=identities;manifest['sourceHashes']={str(SIM/k):v for k,v in d['sourceHashes'].items() if k.endswith('.3mf') or k.endswith('.stp') or k.endswith('.xml')};manifest['generatorSha256']=sha(R/'generate_candidate.py');manifest['manifestBuilderSha256']=sha(__file__)
 manifest['parameters']={'splitLocalZ':-1.6,'sidePillarTopLocalZ':7.1,'sourceOuterWingsKeptOnBaseAtAbsX':11.,'sideScrewHeadSeatsLocal':[[-12.,6.,4.5],[12.,6.,4.5]],'sideScrewOutwardAxisLocal':[0,1,0],'sideScrewTipLocal':[[-12.,-2.,4.5],[12.,-2.,4.5]],'basePillarsLocal':{'xCentres':[-12.,12.],'xWidth':4.,'yRange':[-4.5,2.],'zRange':[1.65,7.1]},'openTopRegisters':{'tongueXWidth':2.,'slotXWidth':2.2,'tongueYRange':[1.6,2.],'slotYRange':[1.5,2.05],'zRange':[1.65,7.1],'clampingFacesY':2.,'lateralNominalClearancePerSide':.1},'sleeveOD':14.6,'sleeveID':10.4,'sleeveWidth':2.8,'sleeveChamfer':.2,'recommendedPrintBedFaces':{'base':'Left local+X/right local-X to bed, per independent print-review. Native supports and material fit remain unverified.','cheek':'NO accepted print orientation. local+Z-down supplied only as a trial; floating large surface and horizontal bearing-ceiling tradeoffs remain. Not print-ready.','sleeve':'one axial annular end flat on bed'},'strengthQualification':'Threaded pilot rectangular host has at least1.2mm lateral wall before threads, about1.0mm after a2mm outer thread. No four-wall, torque or load-capacity claim.'}
 manifest['fitAlternativesAnalysis']=[{'bore':10.2,'nominalDiametralBossClearance':.2,'comment':'Less radial play; smaller tolerance allowance for printed hole undersize.'},{'bore':10.3,'nominalDiametralBossClearance':.3,'comment':'Intermediate clearance, not exported as a separate confusing stock part.'},{'bore':10.4,'nominalDiametralBossClearance':.4,'selected':True,'comment':'Prototype favors insertion clearance over minimal play; printed fit still needs measurement.'}]
 (R/'preview-data.json').write_text(json.dumps(manifest,indent=2)+'\n');(R/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('CANDIDATE_MANIFEST_READY',sha(R/'preview-data.json'),flush=True)
if __name__=='__main__':finalize(json.loads((R/'preview-data.json').read_text()))
