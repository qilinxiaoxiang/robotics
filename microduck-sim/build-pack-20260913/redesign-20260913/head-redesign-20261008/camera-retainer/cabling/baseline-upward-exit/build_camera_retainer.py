#!/usr/bin/env python3
"""Removable eye-camera retainer: source exterior preserved, four drawing holes.
Candidate geometry, not manufacturing approval for a populated Pi board.
"""
from pathlib import Path
import base64,hashlib,json
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent;G=H.parent/'leg-guide-20261006'
raw=(G/'full-build-data.json').read_bytes();data=json.loads(raw);parts={p['key']:p for p in data['parts']};feas=json.loads((H/'camera-eye-feasibility.json').read_text())
shift=np.array([-1.6,0,0.]);holes=np.array(feas['cameraMountHoleBackFaceWorldMm'])+shift
# Align the nominal drawing hole plane to the actual float32 STL PCB planes.
cam_planes=np.unique(trimesh.load_mesh(H/'camera-in-eye-world.stl').vertices[:,0]);back=float(cam_planes[1]+shift[0]);front=float(cam_planes[2]+shift[0]);holes[:,0]=back;
framefront=back-.5;frameback=back-2.4;bossback=back-5.5
cy=float(holes[:,1].mean());zs=sorted(set(holes[:,2]));zmid=122.;ears=[[frameback,cy-18,zmid],[frameback,cy+18,zmid]]
def solid(mesh):
 mesh=mesh.copy();mesh.process();out=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,np.float32),np.asarray(mesh.faces,np.uint32)));assert out.status()==mf.Error.NoError;return out
def tri(s):
 m=s.to_mesh();return trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=True)
def load(path):return solid(trimesh.load_mesh(path,process=True))
def box(lo,hi):return mf.Manifold.cube(np.array(hi)-lo).translate(lo)
def cyl_x(xlo,xhi,y,z,r):return mf.Manifold.cylinder(xhi-xlo,r,circular_segments=64).rotate([0,90,0]).translate([xlo,y,z])
def original(k):
 p=parts[k];return solid(trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True))
def ov(a,b):return max(0.,float((a^b).volume()))
def export(s,name):
 p=D/name;tri(s).export(p);m=trimesh.load_mesh(p,process=True);assert m.is_watertight,(name,'not watertight');assert solid(m).status()==mf.Error.NoError;return str(p)
face=load(H/'face-eye-camera-clearance-world.stl');eye=load(H/'eye-trim-camera-clearance-world.stl');camera_raw=load(H/'camera-in-eye-world.stl').translate(shift);ribbon=load(H/'camera-ribbon-exit-reference-world.stl').translate(shift)
curved_path=H/'curved-head/community-curved-head-world.stl';curved=load(curved_path)
# Side rails and a lower crossbar stay outside the PCB footprint. No broad
# rear plate is allowed to bear against unknown camera components.
ret=mf.Manifold();rail_y=[cy-14.5,cy+14.5];bottom_z=zs[0]-4.1
for y in rail_y:ret=ret+box([frameback,y-1.6,bottom_z-1.0],[framefront,y+1.6,zs[1]+2.4])
ret=ret+box([frameback,rail_y[0]-1.6,bottom_z-1.0],[framefront,rail_y[1]+1.6,bottom_z+1.0])
for x,y,z in holes:
    ret=ret+cyl_x(bossback,framefront,y,z,2.4)+cyl_x(framefront,back,y,z,1.9)
    ry=rail_y[0] if y<cy else rail_y[1]
    ret=ret+box([frameback,min(y,ry)-.8,z-1.4],[framefront,max(y,ry)+.8,z+1.4])
    # Blind1.6mm pilot;6mm TAP screw passes1.12mm PCB then enters4.88mm.
    ret=ret-cyl_x(bossback+.4,back+.05,y,z,.8)
anchors=mf.Manifold();anchor_pilot=[]
for x,y,z in ears:
    ret=ret+cyl_x(frameback,back,y,z,2.8)
    ry=rail_y[0] if y<cy else rail_y[1]
    ret=ret+box([frameback,min(y,ry)-.7,z-1.5],[framefront,max(y,ry)+.7,z+1.5])
    ret=ret-cyl_x(frameback-.1,back+.1,y,z,1.1)
    post=cyl_x(back,81.15,y,z,2.8)-cyl_x(back-.01,80.75,y,z,.8)
    anchors=anchors+post;anchor_pilot.append([back,y,z])
face_candidate=face+anchors
assert len(ret.decompose())==1 and len(face_candidate.decompose())==1
# The shipped envelope is a filled PCB slab. Core only the four Ø2.2 drawing
# interfaces for fastener assessment; do not pretend it is populated PCB CAD.
camera_holes=camera_raw
for x,y,z in holes:camera_holes=camera_holes-cyl_x(back-.005,front+.005,y,z,1.1)
# Six specified M2x6TAP screws: four camera (head on lens/front side), two face
# wings (head behind bracket). Modeled smooth shaft/head are fit envelopes.
screws=[];screw_solid=mf.Manifold()
for i,(x,y,z) in enumerate(holes,1):
 shaft=cyl_x(front-6,front,y,z,1);head=cyl_x(front,front+1.5,y,z,2)
 screws.append({'id':f'camera-{i}','spec':'M2 x 6 TAP','worldHeadSeatMm':[front,y,z],'outwardAxis':[1,0,0],'shaftLengthMm':6,'headEnvelopeDiameterMm':4,'headEnvelopeHeightMm':1.5,'throughPcbMm':1.12,'plasticEngagementMm':4.88,'blindPilotDiameterMm':1.6,'pilotDepthMm':5.1,'tipToPilotBottomMm':.22,'supportPadOuterDiameterMm':3.8,'solid':shaft+head});screw_solid=screw_solid+shaft+head
for i,(x,y,z) in enumerate(ears,1):
 shaft=cyl_x(frameback,frameback+6,y,z,1);head=cyl_x(frameback-1.5,frameback,y,z,2)
 screws.append({'id':f'face-wing-{i}','spec':'M2 x 6 TAP','worldHeadSeatMm':[frameback,y,z],'outwardAxis':[-1,0,0],'shaftLengthMm':6,'headEnvelopeDiameterMm':4,'headEnvelopeHeightMm':1.5,'throughRetainerMm':2.4,'plasticEngagementMm':3.6,'blindPilotDiameterMm':1.6,'pilotDepthMm':80.75-back,'tipToPilotBottomMm':80.75-frameback-6,'solid':shaft+head})
fixed={'face':face_candidate,'eye':eye,'curved_top':curved,'Pi_Zero_outline_only':original('pi'),'head_bottom':original('head_bottom'),'jaw_support':original('jaw_support'),'motor15':original('motor15'),'motor14':original('motor14')}
static={name:{q:ov(s,f) for q,f in fixed.items()} for name,s in [('retainer',ret),('camera',camera_holes),('ribbon_first12mm',ribbon)]}
# Include supplied populated Zero W reservations, keeping their measured status explicit.
board_files=[H/'curved-head'/f'{n}-world.stl' for n in ['zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails','openrb-curved-layout']]
for p in board_files:
 assert p.exists(),p
 fixed[p.stem]=load(p)
static={name:{q:ov(s,f) for q,f in fixed.items()} for name,s in [('retainer',ret),('camera',camera_holes),('ribbon_first12mm',ribbon)]}
# Reservations are supplied acceptance envelopes, not a measured hardware certificate.
for name,row in static.items():
 for q,v in row.items():assert v<1e-5,(name,q,v)
assert ov(ret,camera_raw)<1e-5,('retainer/camera',ov(ret,camera_raw))
assert ov(ret,ribbon)<1e-5
hardware_static={}
for sc in screws:
 permitted={'retainer'} if sc['id'].startswith('camera-') else {'face'}
 obstacles={**fixed,'camera':camera_holes,'retainer':ret}
 vals={q:ov(sc['solid'],obj) for q,obj in obstacles.items() if q not in permitted}
 assert max(vals.values())<1e-5,(sc['id'],'hardware static',vals)
 hardware_static[sc['id']]={'intersectionsMm3':vals,'intentionalSelfTappingHost':list(permitted)}
# Camera mounts onto detached frame before any face closure.
camera_seating=[]
for dx in np.linspace(20,0,81):
 vol=ov(camera_holes.translate([dx,0,0]),ret);assert vol<1e-5,(dx,vol)
 camera_seating.append({'offsetXmm':float(dx),'overlapMm3':vol})
# Prove visible exterior unchanged: all additions are behind X81.15; their
# sampled YZ silhouette is backed by unchanged native face material at X81.30.
face_mesh=tri(face);probes=[]
for _,y,z in ears:
 for yy in np.arange(y-2.8,y+2.801,.2):
  for zz in np.arange(z-2.8,z+2.801,.2):
   if (yy-y)**2+(zz-z)**2<=2.8**2:probes.append([81.30,yy,zz])
inside=face_mesh.contains(np.array(probes));assert all(inside),('anchor front projection outside original face',int((~inside).sum()))
assert ov(anchors,box([81.151,-100,50],[100,100,200]))<1e-8
# Assembled camera/bracket/four camera screws move together. Pi and robot are
# absent because this is genuinely a detached face bench operation.
cartridge=camera_holes+ret+screw_solid
entry=[]
for dx in np.linspace(-30,0,121):
 vals={q:ov(cartridge.translate([dx,0,0]),f) for q,f in {'face':face_candidate,'eye':eye}.items()}
 assert max(vals.values())<1e-5,(dx,vals)
 entry.append({'offsetXmm':float(dx),'overlapMm3':vals})
# The two front-side bolt shafts are installed before the face; the two wing
# drivers are used after cartridge insertion but before the Pi is mounted.
tool_checks=[]
for s in screws:
 c=np.array(s['worldHeadSeatMm']);axis=np.array(s['outwardAxis']);origin=c+axis*1.55
 tool=cyl_x(origin[0],origin[0]+45,c[1],c[2],1.5) if axis[0]>0 else cyl_x(origin[0]-45,origin[0],c[1],c[2],1.5)
 scene={'camera':camera_holes,'retainer':ret} if s['id'].startswith('camera-') else {'camera':camera_holes,'retainer':ret,'face':face_candidate,'eye':eye}
 vals={q:ov(tool,f) for q,f in scene.items()};assert max(vals.values())<1e-5,(s['id'],vals)
 handle=cyl_x(origin[0]+45,origin[0]+105,c[1],c[2],9) if axis[0]>0 else cyl_x(origin[0]-105,origin[0]-45,c[1],c[2],9)
 # Conservative coaxial Ø40mm grip/finger reservation around the Ø18mm handle.
 grip=cyl_x(origin[0]+45,origin[0]+105,c[1],c[2],20) if axis[0]>0 else cyl_x(origin[0]-105,origin[0]-45,c[1],c[2],20)
 handles={q:ov(handle,f) for q,f in scene.items()};grips={q:ov(grip,f) for q,f in scene.items()}
 assert max([*handles.values(),*grips.values()])<1e-5,(s['id'],'handle/grip',handles,grips)
 negative=ov(tool,original('pi')) if s['id'].startswith('face-wing') else ov(tool,face_candidate)
 assert negative>1e-3,(s['id'],'negative control failed',negative)
 tool_checks.append({'screwId':s['id'],'diameterMm':3,'usableShaftLengthMm':45,'headOffsetMm':1.55,'obstacles':list(scene),'intersectionsMm3':vals,'prematurePiOrFaceClosureIntersectionMm3':negative,'handleEnvelope':{'diameterMm':18,'lengthMm':60,'beginsAfterShaftMm':45,'intersectionsMm3':handles},'coaxialGripReservation':{'diameterMm':40,'lengthMm':60,'intersectionsMm3':grips,'scope':'Assumed hand envelope on detached bench subassembly; actual user/tool variation remains'},'handleAndFingerEnvelopeValidated':True})
# Recheck the shifted lens frustum against unchanged exterior and curved top.
opt=feas['optics'];target=np.array(opt['lensFrontCenterWorldMm'])+shift;h=np.tan(np.deg2rad(51));v=np.tan(np.deg2rad(33.5));pts=[]
for length in [.05,200.]:
 for sy in [-1,1]:
  for sz in [-1,1]:pts.append(target+[length,sy*(3.475+length*h),sz*(3.475+length*v)])
fov=solid(trimesh.convex.convex_hull(pts));fov_checks={q:ov(fov,f) for q,f in {'face':face_candidate,'eye':eye,'curved_top':curved,'retainer':ret}.items()};assert max(fov_checks.values())<1e-5,fov_checks
# A40pin header must be evaluated with its actual orientation/height. Emit a
# separate conservative reservation only after board geometry is supplied.
exports={name:export(obj,name) for name,obj in [('camera-retainer-world.stl',ret),('face-with-camera-anchors-world.stl',face_candidate),('camera-shifted-reference-world.stl',camera_holes),('camera-ribbon-shifted-reference-world.stl',ribbon),('camera-shifted-fov-world.stl',fov),('camera-four-screw-envelopes-world.stl',screw_solid),('camera-all-six-screw-envelopes-world.stl',sum((sc['solid'] for sc in screws),mf.Manifold()))]}
source_files=[H/'camera-eye-feasibility.json',H/'face-eye-camera-clearance-world.stl',H/'eye-trim-camera-clearance-world.stl',H/'camera-in-eye-world.stl',curved_path]+board_files
report={'problemIds':['P5','P6'],'checked':'2026-10-08','status':'digital_candidate_with_populated_zero_w_reservations_physical_measurement_pending','cameraShiftFromEyeCandidateMm':shift.tolist(),'lensFrontWorldMm':target.tolist(),'cameraMountHolesWorldMm':holes.tolist(),'officialHoleDiameterMm':2.2,'officialHoleSource':'https://datasheets.raspberrypi.com/camera/camera-module-3-wide-mechanical-drawing.pdf','drawingVerified':'2026-10-08','cameraEnvelopeBoundary':'Dimension-built PCB/lens/connector envelopes; four Ø2.2 holes cored from official drawing only. Populated rear electronics, actual head dimensions and autofocus excursion need physical check. Four Ø3.8 support pads bear only around mounting holes; no lens or autofocus clamp.',
'parts':[{'name':'Removable U-frame camera retainer','quantity':1,'minimumRailSectionMm':[1.9,3.2],'cameraBossLengthMm':5.5},{'name':'Face with two interior mounting bosses','quantity':1,'exteriorFacePreserved':True,'eyeOuterOutlinePreserved':True,'anchorDiameterMm':5.6}],
'fasteners':[{k:v for k,v in s.items() if k!='solid'} for s in screws], 'fastenerCount':6,'nuts':0,'fastenerSource':'Existing assembly-fasteners.json M2 x 6 TAP specification; self-tapping1.6mm printed pilots are reused from existing bracket conventions, not a thread-strength certification. Quantity is candidate demand, not stock confirmation.',
'assembly':[{'step':1,'action':'On the bench, put camera on the four support pads and install four M2x6TAP screws from the lens/front face. Keep detached from duck face.','tool':'PH driver fitting actual screw head; checked straight Ø3mm shaft45mm','check':'PCB rests flat on four pads without lens contact or bowing; stop before overtightening.'},{'step':2,'action':'Seat/latch camera ribbon while the rear connector is accessible; lay its first12mm through the open upper frame.','tool':'Fingers or nonmarring handling tool; actual connector latch not fully modeled','check':'Connector fully seated and latched; no fold at exit.'},{'step':3,'action':'Translate the entire camera+frame+four screws from behind into the detached face along+X.','tool':'Hand support, no force fit','check':'Both side ears meet the new face bosses.'},{'step':4,'action':'From behind, install two M2x6TAP wing screws into the face bosses.','tool':'Checked Ø3mm shaft45mm; Pi must remain absent','check':'Frame retained without bowing PCB.'},{'step':5,'action':'Mount selected Pi only after populated-board/header/cable space is checked against this cartridge.','tool':'Board-specific source fasteners; unresolved until board pose is selected','check':'No header, plug or ribbon interference; do not infer fit from65x30 slab.'}],
'cameraSeating':{'moving':'camera','fixed':'retainer','stepMm':.25,'samples':camera_seating},'screwStaticChecks':hardware_static,'staticIntersectionsMm3':static,'cameraRetainerIntersectionMm3':ov(ret,camera_raw),'cameraRibbonRetainerIntersectionMm3':ov(ret,ribbon),'faceFrontProjectionSamples':len(probes),'faceFrontProjectionAllInsideOriginal':bool(all(inside)),'faceExteriorComparison':{'originalFacePreservedByUnion':True,'newAnchorMaxXmm':81.15,'unchangedFrontProbeXmm':81.30,'eyeMeshUnchanged':True},
'cartridgeInsertion':{'moving':['camera','retainer','four_camera_screws'],'fixed':['detached_face_with_anchors','eye_trim'],'stepMm':.25,'samples':entry,'PiAbsent':True},'driverChecks':tool_checks,'opticalFrustumIntersectionsMm3':fov_checks,
'boardBoundary':{'confirmedOptions':['Pi Zero W with soldered40pin header (possibly WH)','Pi3ModelB V1.2'],'referenceChecked':'Existing65x30mm slab plus separate components, soldered40pinheader/housing and solder-tail reservations','headerOccupancyIncluded':True,'reservationSource':'curved-head Zero W: components3.8mm, header+housing/exit15mm, GPIO solder tails2mm; physical dimensions pending measurement','completeBoardFitVerified':False,'manufacturingCertified':False},
'exports':exports,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},'dataSha256':hashlib.sha256(raw).hexdigest(),'physicalFitVerified':False,'manufacturingCertified':False}
# Viewer-ready world meshes: transforms are identities, never the old tower pose.
def viewerpart(obj,key,name,color,kind,description):
 mesh=tri(obj);bounds=mesh.bounds
 return {'key':key,'name':name,'color':color,'colorName':'Camera mount candidate','sourceId':None,'sourceName':'eye-camera-retainer-candidate','body':'jaw_soft','referenceMesh':key,'index':0,'stage':0,'moduleId':'camera','description':description,'aliases':name,'bounds':bounds.tolist(),'center':bounds.mean(axis=0).tolist(),'dimensions':(bounds[1]-bounds[0]).tolist(),'positionB64':base64.b64encode(np.asarray(mesh.vertices,dtype='<f4').tobytes()).decode(),'indexB64':base64.b64encode(np.asarray(mesh.faces,dtype='<u4').tobytes()).decode(),'triangles':len(mesh.faces),'sourceTransformWorld':np.eye(4).tolist(),'geometryKind':'dimensioned-candidate','partKind':kind,'approachVector':[0,0,0]}
append=[viewerpart(ret,'eye_camera_retainer','Eye camera removable retainer','#dd932a','print','Four official camera mounting holes; two rear face screws. Candidate, physical fit pending.')]
for sc in screws:
 export(sc['solid'],sc['id']+'-screw-world.stl')
 append.append(viewerpart(sc['solid'],'eye_'+sc['id'].replace('-','_')+'_screw',sc['id']+' M2 x 6 TAP','#929ba4','hardware','M2 x 6 TAP nominal envelope; Ø4 x 1.5 mm head assumption, actual head measurement pending.'))
fragment={'coordinateSystem':'World millimetres; identity transform','append':append,'replacements':[viewerpart(camera_holes,'camera_board','Camera Module 3 Wide','#3d7268','electronics','Dimensioned envelope, rear electronics and AF excursion physical check pending.'),viewerpart(face_candidate,'face_panel','Face with interior camera anchors','#f4f4ef','print','Original visible face preserved; two new hidden mounting bosses.')]}
(D/'viewer-fragment.json').write_text(json.dumps(fragment,separators=(',',':'))+'\n')
(D/'camera-retainer-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('CAMERA_RETAINER_CANDIDATE_PASS',json.dumps({'bounds':ret.bounding_box(),'cameraShift':shift.tolist(),'fasteners':6,'static':static,'tools':tool_checks,'fov':fov_checks}))
