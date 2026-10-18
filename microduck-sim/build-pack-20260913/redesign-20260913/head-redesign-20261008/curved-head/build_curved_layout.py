"""P5/P6: preserve the original curved head surface and relocate internal electronics.
Spatial candidates only. No canonical or stock geometry is overwritten.
"""
from pathlib import Path
import sys,json,base64,hashlib,itertools,time
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;REVIEW=D.parent;R=REVIEW.parent;SIM=R.parents[1];SOURCE=R/'leg-guide-20261006/full-build-data.json'
sys.path.insert(0,str(SIM/'hardware-design-20260912/whole-robot-20260912/assembly'))
from assembly_fk import fk,raw,ROBOT
B,G=fk();source=json.loads(SOURCE.read_text());parts={p['key']:p for p in source['parts']}
def man(m):
 s=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)));assert s.status()==mf.Error.NoError;return s
def tri(s):
 a=s.to_mesh();return trimesh.Trimesh(np.asarray(a.vert_properties)[:,:3],np.asarray(a.tri_verts),process=True)
def dec(k):
 p=parts[k];return trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
g=next(g for g in G if g['body']=='jaw_soft' and g['mesh']=='top_head_shell');native=raw('top_head_shell').apply_transform(g['world']);native.export(D/'community-curved-head-world.stl');cap=man(native)
meshes={k:dec(k) for k in ['head_yaw_link','motor13','neck_pitch','neck_pitch_ring','neck_link_a','neck_link_b','openrb','audio_carrier','amplifier','speaker','pi','head_bottom','jaw_support','motor14','motor15','jaw_frame','upper_pad','lower_pad','head_roll_ring_a','head_roll_ring_b']}
for k,f in [('camera_board','camera-in-eye-world.stl'),('face_panel','face-eye-camera-clearance-world.stl'),('eye_trim','eye-trim-camera-clearance-world.stl')]:meshes[k]=trimesh.load(REVIEW/f,force='mesh')
meshes['head_cap']=native
# SameSky official June2026 drawing: capsule30x20±.2, grill2.5±.2,
# total4±.2, rear magnetdia12.7±.2. Include +.5mm solder/lead receiving height.
a=mf.Manifold.cylinder(2.7,10.1,10.1,64).translate([0,-5,0]);b=a.translate([0,10,0]);speaker_body=mf.Manifold.batch_hull([a,b]);speaker_magnet=mf.Manifold.cylinder(2.,6.45,6.45,64).translate([0,0,2.7]);speaker_source=tri(speaker_body+speaker_magnet);speaker_source.apply_translation(meshes['speaker'].bounds.mean(0)-speaker_source.bounds.mean(0));meshes['speaker']=speaker_source
amp=trimesh.load(D/'adafruit3006-with-terminal-receiving-local.stl',force='mesh');amp.apply_translation(meshes['amplifier'].bounds.mean(0)-amp.bounds.mean(0));meshes['amplifier']=amp
for k,f in [('camera_board','camera-shifted-reference-world.stl'),('face_panel','face-with-camera-anchors-world.stl'),('camera_retainer','camera-retainer-world.stl')]:
 meshes[k]=trimesh.load(REVIEW/'camera-retainer'/f,force='mesh')
for k in ['zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails']:
 meshes[k]=trimesh.load(D/(k+'-world.stl'),force='mesh')
sol={k:man(m) for k,m in meshes.items()}
def intersects(a,k):return max(0,float((a^sol[k]).volume()))
fixed=['head_yaw_link','motor13','neck_pitch','neck_pitch_ring','neck_link_a','neck_link_b','camera_retainer','zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails','head_cap','head_bottom','jaw_support','motor14','motor15','jaw_frame','upper_pad','lower_pad','head_roll_ring_a','head_roll_ring_b','pi','camera_board','face_panel','eye_trim']
original={k:{q:intersects(sol[k],q) for q in fixed if intersects(sol[k],q)>.0001} for k in ['openrb','audio_carrier','amplifier','speaker']}
print('ORIGINAL',json.dumps(original),flush=True)
# A broad phase avoids expensive booleans on disjoint meshes. Minimum separation
# is enforced with manifold's exact bounded gap, not a global bbox substitution.
def evaluate(m,solid,keys,gap=.5):
 lo,hi=m.bounds;hits={}
 for k in keys:
  obs=meshes[k];olo,ohi=obs.bounds
  if np.any(lo>ohi+gap) or np.any(olo>hi+gap):continue
  v=max(0,float((solid^sol[k]).volume()))
  if v>1e-5:return None
  d=float(solid.min_gap(sol[k],gap))
  if d<gap-.0001:return None
 return True
moves={};selected={}
# Search the least movement first while retaining board orientation.
k='openrb';old=meshes[k].copy();center=old.bounds.mean(0)
from scipy.spatial.transform import Rotation
opts=[]
for yaw,pitch,roll in itertools.product([0,-2,2],[-4,-4.5,-3.5,-3,-5,-5.5,-6],[0]):
 rot=Rotation.from_euler('zyx',[yaw,pitch,roll],degrees=True).as_matrix()
 for delta in itertools.product([-2,-3,-1,0],[-.5,0,.5],[-1.5,-1.75,-1.25,-1,-.75,-2]):
  score=np.linalg.norm(delta)+.05*(abs(yaw)+abs(pitch)+abs(roll));opts.append((score,rot,np.array(delta),[yaw,pitch,roll]))
opts.sort(key=lambda x:x[0])
preferredRot=Rotation.from_euler('y',-3,degrees=True).as_matrix();opts=[(0,preferredRot,np.array([-1,0,-1.5]),[0,-3,0])]+opts
for count,(_,rot,delta,angles) in enumerate(opts):
 t=np.eye(4);t[:3,:3]=rot;t[:3,3]=center+delta-rot@center;m=old.copy().apply_transform(t);s=sol[k].transform(t[:3,:])
 if evaluate(m,s,fixed,.25):moves[k]=t;selected[k]=(m,s);print('SELECT',k,'count',count,'delta',delta.tolist(),'angles',angles,flush=True);break
 if count and count%1000==0:print('OPENRB_SEARCH',count,flush=True)
if k not in selected:raise RuntimeError('No OpenRB pose in declared rotation/translation search')
meshes[k],sol[k]=selected[k];fixed.append(k)
meshes[k].export(D/(k+'-curved-layout-world.stl'))
(D/'openrb-pose-checkpoint.json').write_text(json.dumps({'transformFromGuideWorld':moves[k].tolist(),'candidateBoundsMm':meshes[k].bounds.tolist()},indent=2)+'\n')
# The audio carrier is deliberately absent: its old rectangular roof mount is
# incompatible. Search both component orientations and locations inside the
# unchanged curved shell, bounded by the native shell envelope.
rotations=[]
for perm in itertools.permutations(range(3)):
 for signs in itertools.product([-1,1],repeat=3):
  rot=np.eye(3)[list(perm)]*np.array(signs)[:,None]
  if np.linalg.det(rot)>.5 and not any(np.allclose(rot,r) for r in rotations):rotations.append(rot)
for k in ['speaker','amplifier']:
 originalmesh=meshes[k].copy();center=originalmesh.bounds.mean(0);centered=originalmesh.copy().apply_translation(-center);oldsol=man(centered)
 opts=[]
 for rid,rot in enumerate(rotations):
  for x,y,z in itertools.product(np.arange(-18,73,3),np.arange(-36,37,3),np.arange(114,150,3)):
   dest=np.array([x,y,z]);score=np.linalg.norm(dest-center)+(0 if np.allclose(rot,np.eye(3)) else 8);opts.append((score,rid,dest))
 opts.sort(key=lambda a:a[0]);found=False
 if k=='amplifier':opts=[(0,next(i for i,r in enumerate(rotations) if np.allclose(r,np.eye(3))),np.array([33,-24,138]))]+opts
 if k=='speaker':
  preferred=np.eye(3)
  rid=next(i for i,r in enumerate(rotations) if np.allclose(r,preferred))
  opts=[(0,rid,np.array([-3,12,132]))]+opts
 for count,(_,rid,dest) in enumerate(opts):
  rot=rotations[rid];t=np.eye(4);t[:3,:3]=rot;t[:3,3]=dest-rot@center;m=originalmesh.copy().apply_transform(t);s=oldsol.transform(np.c_[rot,dest])
  # Do not accept an exterior placement simply because it misses shell material.
  if np.any(m.bounds[0]<[-27,-43,111]) or np.any(m.bounds[1]>[72,43,154]):continue
  if evaluate(m,s,fixed,.3):
   moves[k]=t;selected[k]=(m,s);meshes[k],sol[k]=m,s;fixed.append(k);found=True;print('SELECT',k,'tried',count,'center',dest.tolist(),'rotation',rot.tolist(),flush=True);break
 if not found:raise RuntimeError('No '+k+' pose in declared search')
# Export source-bound poses before mount development; no hidden legacy carrier.
for k,(m,s) in selected.items():m.export(D/(k+'-curved-layout-world.stl'))
oldcap=man(dec('head_cap'))
report={'problemIds':['P5','P6'],'status':'curved-shell-spatial-layout-retention-and-cabling-pending','sourceDataSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'communityShellSource':str(ROBOT/'assets/top_head_shell.stl'),'communityShellSourceSha256':hashlib.sha256((ROBOT/'assets/top_head_shell.stl').read_bytes()).hexdigest(),'nativeShellToWorld':g['world'].tolist(),'originalCurvedShell':{'watertight':native.is_watertight,'bodies':len(cap.decompose()),'boundsMm':native.bounds.tolist(),'volumeMm3':cap.volume()},'squareCapDifference':{'addedVsNativeMm3':(oldcap-cap).volume(),'removedVsNativeMm3':(cap-oldcap).volume(),'squareCapVolumeMm3':oldcap.volume()},'originalElectronicsIntersectionsMm3':original,'transformsFromGuideWorld':{k:t.tolist() for k,t in moves.items()},'replacements':{'head_cap':'community-curved-head-world.stl','amplifier':'amplifier-curved-layout-world.stl','face_panel':'../face-eye-camera-clearance-world.stl','eye_trim':'../eye-trim-camera-clearance-world.stl'},'removedParts':['camera_pitch_foot','camera_cradle','audio_carrier'],'selectedPartBoundsMm':{k:m.bounds.tolist() for k,(m,s) in selected.items()},'selectedPartIntersectionsMm3':{k:{q:intersects(s,q) for q in fixed if q!=k} for k,(m,s) in selected.items()},'selectedPartMinimumGapsMm':{k:{q:float(s.min_gap(sol[q],3)) for q in fixed if q!=k} for k,(m,s) in selected.items()},'minimumGapSearchLimitMm':3.,'shellExteriorDeviationMm':0.,'shellGeometryChanged':False,'boardScope':json.loads((D/'board-envelope-review.json').read_text()),'unresolved':['Electronic retention and replacement audio carrier','Full component and connector envelopes for exact Pi variant','Pi3B V1.2 is a bench option, not this head layout; ZeroW+40pin receiving envelopes are checked, actual header/plug dimensions remain a receiving check','Wire route, plugs and complete insertion paths','Physical fit, stiffness and acoustic performance'],'manufacturingAccepted':False,'physicalFitVerified':False}
(D/'curved-layout.json').write_text(json.dumps(report,indent=2)+'\n');print('CURVED_LAYOUT_SPATIAL_PASS',flush=True)
