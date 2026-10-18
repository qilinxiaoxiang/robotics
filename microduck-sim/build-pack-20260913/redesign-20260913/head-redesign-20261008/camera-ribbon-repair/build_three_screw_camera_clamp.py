"""Three non-collinear perimeter screws clamp four PCB lands without forward screw tips."""
from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0])
read(D/'build_reverse_nut_camera.py')
cam=load(D/'camera-roll90-rearseat4-world.stl').translate([.8,0,0]);fov=load(D/'camera-fov-roll90-rearseat4-world.stl').translate([.8,0,0]);af=load(D/'camera-rearseat4-af-additional-receiving-world.stl').translate([.8,0,0]);oldEye=n['source']('eye_trim');eye=oldEye
src=D/'build_face_mounts124.py';read(src);nn={'__file__':str(src)};exec(src.read_text().split('hardware=[]')[0],nn);face=nn['stripped'];n['hashes'].update(nn['n']['hashes']);del nn
rows=json.loads(read(D/'local-camera-roll90-rearseat4-pi-report.json'))['screws'][:4];xs=np.unique(cam.to_mesh64().vert_properties[:,0]);pred=rows[0]['headSeatMm'][0]+.8;front=float(xs[np.argmin(abs(xs-pred))]);back=float(xs[np.argmin(abs(xs-(pred-1.12)))]);frameback=back-2.4
rear=mf.Manifold();pads=mf.Manifold();pegs=mf.Manifold();lands=[]
for i,row in enumerate(rows):
 _,y,z=row['headSeatMm'];pad=cyl(front,81.15,y,z,2.4);pads+=pad
 rear+=cyl(frameback,back,y,z,2.4)
 # left-side rail carries each bearing land; lower rails sit above the GPIO solder-tail region.
 zmid=z+1.2 if z<130 else z+1.2
 rear+=box([frameback,-16.4,zmid-.8],[back,y,zmid+.8])
 lands.append({'id':row['id'],'centerYZ':[y,z],'frontContactWorldX':front,'rearContactWorldX':back,'radiusMm':2.4})
# A round locator and relieved secondary locator register the PCB; no fastener loads the camera/lens housing.
_,y,z=rows[0]['headSeatMm'];pegs+=cyl(back+.12,front+.01,y,z,1.0)
_,y,z=rows[2]['headSeatMm'];peg=cyl(back+.12,front+.01,y,z,1.0)^box([back,-50,z-.8],[front+.02,50,z+.8]);pegs+=peg
rear+=box([frameback,-17.2,117.5],[back,-15.6,148.0]);rear+=box([frameback,-17.2,146.4],[back,19.0,148.0])
anchors=[(-18.091378211975098,119.),(-18.091378211975098,147.2),(17.908621788024902,147.2)];hardware={};holes=[];pilots=mf.Manifold()
for i,(y,z) in enumerate(anchors,1):
 # 1.5mm through plate +2.5mm threaded engagement with existing M2x4 TAP.
 seat=back-1.5;rear+=cyl(seat,back,y,z,2.8);rear-=cyl(seat-.05,back+.05,y,z,1.1)
 # Bridges connect to the left or upper full frame; screw counterbores are open from the rear.
 zy=119. if i==1 else 147.2
 rear+=box([seat,min(y,-16.4),zy-.8],[back,max(y,-16.4)+.01,zy+.8])-cyl(seat-.05,back+.05,y,z,1.1)
 rear-=cyl(frameback-.1,seat,y,z,2.15)
 pilot=cyl(back-.01,back+2.8,y,z,.8);pilots+=pilot;anchor=cyl(back,81.15,y,z,3.1);face+=anchor
 hardware['camera_clamp_screw_'+str(i)]=cyl(seat,seat+4,y,z,1)+cyl(seat-1.5,seat,y,z,2)
 holes.append({'id':'camera_clamp_screw_'+str(i),'spec':'M2 x 4 TAP','headSeatMm':[seat,y,z],'outwardAxis':[-1,0,0],'throughPrintedMm':1.5,'threadEngagementMm':2.5,'pilotDepthMm':2.8,'nominalTipMarginMm':.3,'frontSolidWallAfterPilotMm':81.39900207519531-(back+2.8)})
face=(face+pads+pegs)-pilots
# Rear relief only; visible eye contour/front half-space remains unchanged.
receiving=(pads+pegs)^box([60,-40,110],[81.15,40,155]);eye-=receiving
camReceiving=cam+cam.translate([0,.2,0])+cam.translate([0,-.2,0])+cam.translate([0,0,.2])+cam.translate([0,0,-.2]);cut=camReceiving^box([front+.05,-40,110],[81.15,40,155]);eye-=cut;face-=cut
solids={'camera_board_clamped':cam,'camera_fov_clamped':fov,'camera_af_clamped':af,'camera_three_screw_clamp':rear,'face_three_screw_camera':face,'eye_three_screw_camera':eye}|hardware
exports={k:export(s,k) for k,s in solids.items()};checks=[];toolChecks=[]
pirows=json.loads(read(O/'pi-geometry-manifest.json'))['parts']
for row in pirows+ [{'key':'head_cap','mesh':'usb-access/usb-repair/cap-usb-positive-x225-world.stl'}]:
 fixed=load(H/row['mesh'])
 for k,q in solids.items():
  if 'fov' in k or '_af' in k:continue
  v,bb=n['volume'](q,fixed);checks.append({'part':k,'obstacle':row['key'],'overlapMm3':v,'boundsMm':bb})
 del fixed;gc.collect()
for k,q in [('camera',cam),('clamp',rear),('FOV',fov),('AF',af)]+list(hardware.items()):
 for fk,fixed in [('camera',cam),('face',face),('eye',eye)]:
  if k=='camera' and fk=='camera':continue
  v,bb=n['volume'](q,fixed);checks.append({'part':k,'obstacle':fk,'overlapMm3':v,'boundsMm':bb})
for row in holes:
 seat,y,z=row['headSeatMm'];tool=cyl(seat-46.5,seat-1.5,y,z,1.5)+cyl(seat-106.5,seat-46.5,y,z,9)
 for fk,fixed in [('camera',cam),('clamp',rear),('face',face),('eye',eye)]:
  v,bb=n['volume'](tool,fixed);toolChecks.append({'id':row['id'],'obstacle':fk,'overlapMm3':v,'boundsMm':bb})
protect=box([81.15,-80,80],[120,80,180]);sourceContact=oldEye^n['source']('face_panel');contact=eye^face
r={'integrationReady':False,'status':'LOCAL_FOUR_LAND_THREE_SCREW_CLAMP_PROTOTYPE','exports':exports,'screws':holes,'pcbBearingLands':lands,'locatorMethod':'one round2mm peg plus secondary2mm peg relieved to1.6mm alongZ, in source2.2mm holes; other two holes bear without rigid pegs','physicalStrengthVerified':False,'pilotCutAfterUnion':True,'screwLengthReceivingMm':[3.85,4.15],'printedThroughReceivingMm':[1.4,1.6],'threadEngagementReceivingMm':[2.25,2.75],'minimumPilotTipMarginUnderReceivingMm':.05,'layerHeightDesignMaxMm':.2,'minimumFullFrontWallLayers':3,'sourceFaceEyeContactMm3':max(0,sourceContact.volume()),'newFaceEyeContactMm3':max(0,contact.volume()),'newFaceEyeOutsideSourceContactMm3':max(0,(contact-sourceContact).volume()),'eyeProtectedSurfaceRemovedMm3':max(0,((oldEye-eye)^protect).volume()),'faceBodies':len(face.decompose()),'clampBodies':len(rear.decompose()),'eyeBodies':len(eye.decompose()),'checks':checks,'toolChecks':toolChecks,'sourceHashes':n['hashes']};(O/'camera-three-screw-clamp-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'bodies':[r['faceBodies'],r['clampBodies'],r['eyeBodies']],'failures':[x for x in checks+toolChecks if x['overlapMm3']>1e-5],'sourceContact':r['sourceFaceEyeContactMm3'],'newOutside':r['newFaceEyeOutsideSourceContactMm3']},indent=2))
