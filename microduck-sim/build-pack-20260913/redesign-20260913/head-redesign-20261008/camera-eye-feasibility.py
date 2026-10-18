"""P5/P6: fit the existing Camera Module 3 Wide into the native central eye.

Isolated digital candidate. Preserves canonical guide/CAD. Camera source is an
existing dimension-built installation envelope, not detailed manufacturer CAD.
"""
from pathlib import Path
import base64,hashlib,json
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parent;SIM=R.parents[1];SOURCE=R/'leg-guide-20261006/full-build-data.json';raw=SOURCE.read_bytes();data=json.loads(raw);by={p['key']:p for p in data['parts']};mesh={};sol={}
def man(m):
 m=m.copy();m.process();s=mf.Manifold(mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32)));assert s.status()==mf.Error.NoError,str(s.status());return s
def tri(s):
 m=s.to_mesh();return trimesh.Trimesh(np.array(m.vert_properties)[:,:3],np.array(m.tri_verts),process=True)
def get(k):
 if k not in sol:
  p=by[k];mesh[k]=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True);sol[k]=man(mesh[k])
 return sol[k]
def box(bounds,padding=0):
 lo=np.array(bounds[0])-padding;hi=np.array(bounds[1])+padding;return mf.Manifold.cube(hi-lo).translate(lo)
def overlaps(s,items):return {k:max(0.,float((s^q).volume())) for k,q in items.items()}
F=SIM/'hardware-design-20260912/whole-robot-20260912/electrical/head-layout/final';body=np.array(by['camera_board']['sourceTransformWorld']);components={}
for name in ['pcb','lens_body','lens','rear_connector','ribbon_keepout']:
 components[name]=trimesh.load(F/f'camera_{name}_assembly.stl',force='mesh').apply_transform(body)
lens=components['lens'];old=np.array([lens.bounds[1,0],*lens.bounds.mean(0)[1:]]);eye=get('eye_trim');eye_center=mesh['eye_trim'].bounds.mean(0);target=np.array([88.,eye_center[1],eye_center[2]]);delta=target-old;transform=np.eye(4);transform[:3,3]=delta
for name,m in components.items():m.apply_translation(delta)
cam=get('camera_board').translate(delta);camera_mesh=tri(cam);camera_mesh.export(D/'camera-in-eye-world.stl')
# Exact existing outline, with local interior relief only. Keep .30 mm nominal
# envelope clearance. PCB relief stops short of the original outer face plane.
pocket=mf.Manifold()
for name in ['pcb','lens_body','rear_connector']:
 bounds=components[name].bounds.copy();bounds[0,0]-=30
 pocket=pocket+box(bounds,.30)
# Reserve a 20.6 mm wide, 12 mm straight ribbon exit behind the face.
ribbon_box=box(components['ribbon_keepout'].bounds,.30);pocket=pocket+ribbon_box
face_cut=get('face_panel')-pocket;trim=get('eye_trim')-pocket
# Pocketing may sever obsolete central mounting posts. Remove those islands
# explicitly rather than exporting unprintable loose remnants. Outer Pi pilots
# remain on the main face and are checked independently below.
face_components=sorted(face_cut.decompose(),key=lambda q:q.volume(),reverse=True);removed_posts=[{'volumeMm3':float(q.volume()),'boundsMm':list(q.bounding_box())} for q in face_components[1:]];face=face_components[0]
assert len(face.decompose())==1 and len(trim.decompose())==1
assert tri(face).is_watertight and tri(trim).is_watertight
tri(face).export(D/'face-eye-camera-clearance-world.stl');tri(trim).export(D/'eye-trim-camera-clearance-world.stl');tri(pocket).export(D/'camera-eye-pocket-reference-world.stl');tri(ribbon_box).export(D/'camera-ribbon-exit-reference-world.stl')
# Board mounting-hole interfaces retained from official drawing coordinates.
# Old global zero-pitch PCB bottom is Z178.7813137, width spans Y±12.5.
old_pcb=trimesh.load(F/'camera_pcb_assembly.stl',force='mesh').apply_transform(body)
holes=[]
for y in [-10.5,10.5]:
 for z in [2.,14.5]:holes.append((np.array([old_pcb.bounds[0,0],old_pcb.bounds.mean(0)[1]+y,old_pcb.bounds[0,2]+z])+delta).tolist())
fixed_names=['pi','openrb','head_cap','jaw_support','head_bottom','motor15','motor14','amplifier','speaker','audio_carrier']
fixed={k:get(k) for k in fixed_names};native={'face_panel':get('face_panel'),'eye_trim':get('eye_trim'),**fixed};candidate={'face_panel':face,'eye_trim':trim,**fixed}
original_hits=overlaps(cam,native);candidate_hits=overlaps(cam,candidate);assert max(candidate_hits.values())<1e-5,candidate_hits
# A .25 mm inflated camera AABB is deliberately not used: it would bridge empty
# regions of the module. Each measured component reserves its own local bounds.
component_gaps={k:float(cam.min_gap(q,100)) for k,q in candidate.items()}
# Conservative square-pupil frustum: official 102°H×67°V, lens diameter6.95.
# This geometric non-occlusion test does not model distortion or calibration.
pupil=3.475;h=np.tan(np.deg2rad(51));v=np.tan(np.deg2rad(33.5));pts=[]
for length in [.05,200.]:
 for hs in [-1,1]:
  for vs in [-1,1]:pts.append(target+[length,hs*(pupil+length*h),vs*(pupil+length*v)])
frustum=man(trimesh.convex.convex_hull(pts));tri(frustum).export(D/'camera-eye-fov-reference-world.stl');fov_hits=overlaps(frustum,candidate);assert max(fov_hits.values())<1e-5,fov_hits
# Test the real proposed bench order: camera enters the detached face before
# the Pi is mounted. Pi is intentionally absent from this one bench path.
entry=[]
for offset in np.linspace(-30,0,121):
 vals=overlaps(cam.translate([offset,0,0]),{'face_panel':face,'eye_trim':trim});assert max(vals.values())<1e-5,(offset,vals)
 entry.append({'offsetXmm':float(offset),'maxIntersectionMm3':max(vals.values())})
# Sample retained front skin along X within the camera PCB pocket footprint.
fm=tri(face);yz=[(y,z) for y in np.linspace(target[1]-12.79,target[1]+12.79,33) for z in np.linspace(target[2]-14.69,target[2]+9.75,33)];points=np.array([[60,y,z] for y,z in yz]);locations,ray_ids,_=fm.ray.intersects_location(points,np.tile([1,0,0],(len(points),1)));skin=[]
for i in np.unique(ray_ids):
 xs=np.sort(locations[ray_ids==i,0])
 for a,b in zip(xs[::2],xs[1::2]):
  if a>=79.99 and b>80.0001:skin.append({'pointYZ':points[i,1:].tolist(),'innerX':float(a),'outerX':float(b),'thicknessXmm':float(b-a)})
new_skin=[r for r in skin if r['innerX']<80.01];minimum=min(skin,key=lambda r:r['thicknessXmm']);native_hits,_,_=mesh['face_panel'].ray.intersects_location([[60,*minimum['pointYZ']]],[[1,0,0]])
wall={'samples':len(skin),'minimumSampledXThicknessMm':minimum['thicknessXmm'],'minimumSample':minimum,'nativeSourceIntersectionsAtMinimumXmm':sorted(native_hits[:,0].tolist()),'newPocketSkinSamples':len(new_skin),'minimumNewPocketFrontSkinMm':min(r['thicknessXmm'] for r in new_skin),'scope':'Directional surviving-skin samples only, not a universal minimum wall or strength certificate. The thinnest .298mm source lip is unchanged; newly cut pocket fronts retain at least1.399mm at these samples.'}
assert wall['minimumNewPocketFrontSkinMm']>1.39
(D/'camera-eye-wall-samples.json').write_text(json.dumps({**wall,'rows':skin},indent=2)+'\n')
# Preserve only the Zero-outline reference and pilots; populated-board fit is unverified.
pi_screws=[s for s in data['screws'] if s.get('groupId')=='pi'];pi_keep=[]
for s in pi_screws:
 axis=np.array(s['world_axis']);c=np.array(s['world_center_mm']);T=trimesh.geometry.align_vectors([0,0,1],axis);T[:3,3]=c-axis*3.;cyl=trimesh.creation.cylinder(radius=2.6,height=8,sections=48).apply_transform(T);cut=max(0.,float((man(cyl)^pocket).volume()));pi_keep.append({'screw':s['id'],'removedPilotKeepoutVolumeMm3':cut});assert cut<1e-6
# Aperture samples use planar source sections rather than guessed eye diameter.
apertures=[]
for x in [81.4,82,85,88,89.39]:
 section=mesh['eye_trim'].section(plane_origin=[x,*target[1:]],plane_normal=[1,0,0]);minimum=None
 if section is not None:
  for line in section.discrete:
   p=line[:,1:]-target[1:];a=p[:-1];b=p[1:];ab=b-a;tt=np.clip(-np.sum(a*ab,1)/np.maximum(np.sum(ab*ab,1),1e-20),0,1);rr=np.linalg.norm(a+tt[:,None]*ab,axis=1);minimum=min(float(rr.min()),minimum if minimum is not None else np.inf)
 apertures.append({'planeXmm':x,'guaranteedCenteredNativeClearDiameterMm':2*minimum if minimum is not None else None})
# Optical blind region at beak height must remain visible to system design.
beak_z=109.;drop=target[2]-beak_z;nearest_forward=drop/v;optics={'lensFrontCenterWorldMm':target.tolist(),'axisWorld':[1,0,0],'horizontalFovDegrees':102,'verticalFovDegrees':67,'nativeEyeFrontXmm':float(mesh['eye_trim'].bounds[1,0]),'lensRecessMm':float(mesh['eye_trim'].bounds[1,0]-target[0]),'conservativeSquarePupilDiameterMm':6.95,'frustumNearMm':.05,'frustumFarMm':200,'intersectionsMm3':fov_hits,'beakHeightReferenceWorldZmm':beak_z,'minimumForwardDistanceToBeakHeightAtZeroTiltMm':nearest_forward,'focusMinimumOfficialMm':50,'warning':'At zero tilt the lower image edge reaches beak-height objects only about33mm forward of the lens. Close grasp/contact can leave the image or be inside the 50mm focus limit; head pitch/approach planning and real calibration remain required.'}
# Cable connector stays behind face; its immediate straight exit is cleared.
ribbon_hits=overlaps(ribbon_box,candidate);assert max(ribbon_hits.values())<1e-5,ribbon_hits
source_meshes={k:{'verticesSha256':hashlib.sha256(base64.b64decode(by[k]['positionB64'])).hexdigest(),'indicesSha256':hashlib.sha256(base64.b64decode(by[k]['indexB64'])).hexdigest(),'sourceTransformWorld':by[k]['sourceTransformWorld']} for k in ['camera_board','face_panel','eye_trim',*fixed_names]}
report={'problemIds':['P5','P6'],'checked':'2026-10-08','status':'feasible-eye-package-bench-entry-sampled-retention-and-cable-loop-pending','singleCentralEye':True,'sourceDataSha256':hashlib.sha256(raw).hexdigest(),'sourceMeshes':source_meshes,'officialSources':[{'url':'https://www.raspberrypi.com/products/camera-module-3/','verified':'2026-10-08','facts':{'wideOverallNominalMm':[25,24,12.4],'connector':'15-pin1mmFPC'}},{'url':'https://datasheets.raspberrypi.com/camera/camera-module-3-wide-mechanical-drawing.pdf','verified':'2026-10-08','facts':{'pcbMm':[25,23.862,1.12],'mountHolesMm':[[2,2],[23,2],[2,14.5],[23,14.5]],'mountHoleDiameterMm':2.2,'lensDiameterMm':6.95,'lensBodyMm':[10.8,10.8,4.07]}},{'url':'https://www.raspberrypi.com/documentation/accessories/camera.html#hardware-specification','verified':'2026-10-08','facts':{'fovHdeg':102,'fovVdeg':67,'focusMinimumMm':50}}],'cameraModelKind':'Existing dimension-built component envelopes from official drawing; not detailed manufacturer CAD. Nominal modeled depth12.17mm vs product approximate12.4mm; .30mm local relief is retained. Actual autofocus-body excursion and cable termination must be checked.','cameraTransformFromCurrentGuideWorld':transform.tolist(),'cameraSourceWorldToCandidate':transform.tolist(),'cameraWorldBoundsMm':camera_mesh.bounds.tolist(),'nativeEyeOuterBoundsMm':mesh['eye_trim'].bounds.tolist(),'nativeApertureSections':apertures,'originalCameraIntersectionsMm3':original_hits,'candidateCameraIntersectionsMm3':candidate_hits,'candidateMinimumGapsMm':component_gaps,'minimumGapSearchLimitMm':100,'faceRemovedMm3':get('face_panel').volume()-face.volume(),'originalFaceComponents':len(get('face_panel').decompose()),'faceComponentsImmediatelyAfterPocket':len(face_components),'removedObsoleteCentralPostIslands':removed_posts,'eyeTrimRemovedMm3':get('eye_trim').volume()-trim.volume(),'faceComponents':len(face.decompose()),'eyeTrimComponents':len(trim.decompose()),'cameraMountHoleBackFaceWorldMm':holes,'mountHoleAxisWorld':[1,0,0],'straightBenchInsertion':{'moving':'camera envelope','fixed':['candidate face_panel','candidate eye_trim'],'startOffsetMm':[-30,0,0],'endOffsetMm':[0,0,0],'stepMm':.25,'samples':entry,'PiMustBeAbsent':True,'scope':'Finite sampled rear entry on detached face, before Pi mounting. Final camera retention and actual cable loop are separate.'},'faceWallSamples':wall,'retentionStatus':'Candidate files provide clearance pockets and the four exact mounting interfaces, not a validated camera-retaining bracket. Add a removable four-point retainer; mount camera and latch ribbon on detached face before reinstalling Pi. Do not use adhesive or clamp autofocus lens body.','piPilotKeepoutChecks':pi_keep,'ribbonInitialExitIntersectionsMm3':ribbon_hits,'ribbonRouteStatus':'Only camera connector and first12mm exit reserved. Full board-specific cable loop, populated connector clearance, bend radius and latch access remain unverified. Pi 3 is not modeled.','optics':optics,'unchanged':['Zero-outline reference slab pose and four mounting pilots; not complete-board fit','OpenRB/audio positions','head-cap shell geometry','native single-eye outside outline'],'candidateReplacementParts':['face_panel with local interior camera/ribbon clearance','eye_trim with local rear lens-body relief','camera retaining bracket not yet designed; obsolete central post remnants removed, original Pi pilots retained'],'removeFromCandidateAssembly':['camera_pitch_foot','camera_cradle','fourM2cameraPCBmountnutsandexistingmountfasteners must be reassigned by integrated retention design'],'exports':{n:str(D/n) for n in ['camera-in-eye-world.stl','face-eye-camera-clearance-world.stl','eye-trim-camera-clearance-world.stl','camera-eye-pocket-reference-world.stl','camera-ribbon-exit-reference-world.stl','camera-eye-fov-reference-world.stl']},'physicalFitVerified':False,'purchasesMade':False}
from board_scope import apply_board_scope
apply_board_scope(report, data['parts'])
report['boardScope']=json.loads((D/'board-scope.json').read_text())
(D/'camera-eye-feasibility.json').write_text(json.dumps(report,indent=2)+'\n')
print('CAMERA_EYE_STATIC_PACKAGE_PASS',json.dumps({k:report[k] for k in ['cameraTransformFromCurrentGuideWorld','candidateMinimumGapsMm','faceRemovedMm3','eyeTrimRemovedMm3','faceComponents','eyeTrimComponents']}))
