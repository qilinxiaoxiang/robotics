"""Independent bench prototype: machine screws, captive M2 nuts, unchanged eye front."""
from pathlib import Path
import os,json,gc,math
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent;O=D/'positive-x225';O.mkdir(exist_ok=True)
p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n);np=n['np'];mf=n['mf'];tm=n['trimesh'];read=n['read'];read(Path(__file__))
def load(p):
 read(p);q=tm.load(p,force='mesh');assert q.is_watertight,str(p);s=mf.Manifold(mf.Mesh64(np.array(q.vertices,np.float64),np.array(q.faces,np.uint64)));assert s.status()==mf.Error.NoError and s.volume()>0;return s
def export(s,name):
 assert s.status()==mf.Error.NoError and s.volume()>0;mesh=s.to_mesh64();m=tm.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=True);assert m.is_watertight,name
 p=O/(name+'-world.stl')
 with p.open('w') as f:
  f.write('solid '+name+'\n')
  for tri in m.triangles:
   f.write('facet normal 0 0 0\nouter loop\n')
   for xyz in tri:f.write('vertex '+' '.join(format(float(a),'.17g') for a in xyz)+'\n')
   f.write('endloop\nendfacet\n')
  f.write('endsolid '+name+'\n')
 back=load(p);assert abs(back.volume()-s.volume())<1e-6;return str(p.relative_to(H))
def cyl(x0,x1,y,z,r,segments=48):return mf.Manifold.cylinder(x1-x0,r,circular_segments=segments).rotate([0,90,0]).translate([x0,y,z])
def box(a,b):return mf.Manifold.cube(np.array(b)-a).translate(a)
def hexbody(x0,x1,y,z,across):return cyl(x0,x1,y,z,across/math.sqrt(3),6)
cam=load(D/'camera-roll90-rearseat4-world.stl').translate([.8,0,0]);fov=load(D/'camera-fov-roll90-rearseat4-world.stl').translate([.8,0,0]);af=load(D/'camera-rearseat4-af-additional-receiving-world.stl').translate([.8,0,0]);oldEye=n['source']('eye_trim')
src=D/'build_face_mounts124.py';read(src);nn={'__file__':str(src)};exec(src.read_text().split('hardware=[]')[0],nn);face=nn['stripped'];n['hashes'].update(nn['n']['hashes']);del nn
rows=json.loads(read(D/'local-camera-roll90-rearseat4-pi-report.json'))['screws'][:4]
predictedFront=rows[0]['headSeatMm'][0]+.8;vertexXs=np.unique(cam.to_mesh64().vert_properties[:,0]);front=float(vertexXs[np.argmin(abs(vertexXs-predictedFront))]);back=float(vertexXs[np.argmin(abs(vertexXs-(predictedFront-1.12)))]);assert abs(front-predictedFront)<.0001 and abs(back-(predictedFront-1.12))<.0001;seat=front+1.6-4
rear=mf.Manifold();hardware={};pockets=mf.Manifold();posts=mf.Manifold();outside=mf.Manifold();eye=oldEye
for row in rows:
 _,y,z=row['headSeatMm'];key=row['id'];nut=hexbody(front,front+1.6,y,z,4)-cyl(front-.01,front+1.61,y,z,1.01)
 screw=cyl(seat,seat+4,y,z,1)+cyl(seat-1.5,seat,y,z,2)
 hardware[key+'_machine_screw']=screw;hardware[key+'_M2_nut']=nut
 # Nut slides into front receiver while camera/face are loose. PCB itself closes rear pocket.
 pocket=hexbody(front-.05,front+1.75,y,z,4.2)
 posts+=hexbody(front,81.15,y,z,6.6);pockets+=pocket
 rear+=cyl(seat,back,y,z,2.5)-cyl(seat-.05,back+.05,y,z,1.1)
 # Four bearing islands connected on the left, leaving GPIO tail/FFC channel open at right.
 zy=z+1.4 if z>130 else z-1.4
 rear+=box([seat,-16.3,zy-.7],[back,y,zy+.7])-cyl(seat-.05,back+.05,y,z,1.1)
rear+=box([seat,-17,117.5],[back,-15.4,145])
face=(face+posts)-pockets
# Source front-eye surface X>=81.15 is protected. Only rear mounting lip can receive nut/pillar.
receiver=posts+pockets
cut=receiver^box([60,-40,110],[81.15,40,155]);eye-=cut
# Side clearance for source camera housing only in rear eye throat, never visible front contour.
camReceiving=cam+cam.translate([0,.2,0])+cam.translate([0,-.2,0])+cam.translate([0,0,.2])+cam.translate([0,0,-.2])
cut2=camReceiving^box([front+.05,-40,110],[81.15,40,155]);eye-=cut2;face-=cut2
solids={'camera_board':cam,'camera_fov':fov,'camera_af':af,'camera_rear_clamp':rear,'face_camera_nut_prototype':face,'eye_camera_nut_prototype':eye}|hardware
exports={k:export(s,k) for k,s in solids.items()};checks=[]
# Actual board and installed Pi envelopes, plus cap and eye. Mating screw/nut thread and PCB/lands separated explicitly.
pirows=json.loads(read(O/'pi-geometry-manifest.json'))['parts'];obstacles=[(r['key'],load(H/r['mesh'])) for r in pirows]
obstacles += [('head_cap',load(H/'usb-access/usb-repair/cap-usb-positive-x225-world.stl'))]
for fk,fixed in obstacles:
 for k in ['camera_board','camera_rear_clamp','face_camera_nut_prototype','eye_camera_nut_prototype']+list(hardware):
  v,bb=n['volume'](solids[k],fixed);checks.append({'part':k,'obstacle':fk,'overlapMm3':v,'boundsMm':bb})
for k,q in [('camera',cam),('rear_clamp',rear),('FOV',fov),('AF',af)]+list(hardware.items()):
 for fk,fixed in [('eye',eye),('face',face),('camera',cam)]:
  if k=='camera' and fk=='camera':continue
  v,bb=n['volume'](q,fixed);checks.append({'part':k,'obstacle':fk,'overlapMm3':v,'boundsMm':bb})
v,bb=n['volume'](eye,face);checks.append({'part':'eye','obstacle':'face','overlapMm3':v,'boundsMm':bb})
# Driver access with face/camera assembled on bench, before the Pi is installed.
toolChecks=[]
for row in rows:
 _,y,z=row['headSeatMm'];tool=cyl(seat-46.5,seat-1.5,y,z,1.5)+cyl(seat-106.5,seat-46.5,y,z,9)
 for fk,fixed in [('camera',cam),('rear_clamp',rear),('face',face),('eye',eye)]:
  v,bb=n['volume'](tool,fixed);toolChecks.append({'screwId':row['id'],'obstacle':fk,'overlapMm3':v,'boundsMm':bb})
protect=box([81.15,-80,80],[120,80,180]);r={'integrationReady':False,'status':'CAMERA_NUT_BENCH_PROTOTYPE_NOT_ACCEPTED','cameraForwardMm':.8,'piShiftX':2.25,'hardwareRequirement':{'machineScrews':'4 x M2 x 4, coarse0.4 pitch, not TAP','nuts':'4 x M2 DIN934; stock unverified','nutPrimarySource':'https://www.valuefastener.com/documents/products/metdin934.pdf','nutHeightRangeMm':[1.35,1.6],'nutAcrossFlatsRangeMm':[3.82,4.0]},'stackMm':{'rearBearing':1.28,'pcb':1.12,'maxNut':1.6,'sum':4,'screw':4,'nominalFullNutEngagement':1.6,'remainingFaceWallAfter1p75Pocket':81.39900207519531-(front+1.75)},'exportedMeshes':exports,'eyeProtectedSurfaceAddedMm3':max(0,((eye-oldEye)^protect).volume()),'eyeProtectedSurfaceRemovedMm3':max(0,((oldEye-eye)^protect).volume()),'faceBodies':len(face.decompose()),'clampBodies':len(rear.decompose()),'eyeBodies':len(eye.decompose()),'checks':checks,'sourceHashes':n['hashes'],'physicalStrengthVerified':False,'toolPathsChecked':True,'toolChecks':toolChecks,'actualPcbPlanesWorldX':[back,front],'screwHeadSeatWorldX':seat};(O/'camera-nut-prototype-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'bodies':[r['faceBodies'],r['clampBodies'],r['eyeBodies']],'failures':[x for x in checks if x['overlapMm3']>1e-5]},indent=2))
