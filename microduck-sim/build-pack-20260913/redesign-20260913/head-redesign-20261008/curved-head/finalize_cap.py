"""Source-bound populated curved cap: local rail relief, assembly trajectories and mounting access."""
from pathlib import Path
import base64,json,hashlib,io,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;V=D.parent;src=V.parent/'leg-guide-20261006/full-build-data.json';data=json.loads(src.read_text());P={p['key']:p for p in data['parts']}
def man(m):return mf.Manifold(mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32)))
def tri(s):
 q=s.to_mesh();return trimesh.Trimesh(np.array(q.vert_properties)[:,:3],np.array(q.tri_verts),process=True)
loadedHashes={}
def load(f):
 b=f.read_bytes();loadedHashes[str(f.relative_to(V))]=hashlib.sha256(b).hexdigest();return man(trimesh.load(io.BytesIO(b),file_type='stl',force='mesh'))
def dec(k):
 p=P[k];return man(trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True))
def hits(a,b):
 aa=np.array(a.bounding_box()).reshape(2,3);bb=np.array(b.bounding_box()).reshape(2,3)
 if np.any(aa[0]>=bb[1]) or np.any(bb[0]>=aa[1]):return 0.
 return max(0.,float((a^b).volume()))
cap=load(D/'curved-cap-with-internal-posts-and-usb-world.stl')+load(D/'audio-roof-posts-world.stl')
usb=load(V/'usb-access/openrb-usb-c-receiving-world.stl');ua=np.array(json.loads((V/'usb-access/usb-report.json').read_text())['outwardAxis']);usbcut=mf.Manifold.batch_hull([usb,usb.translate(ua*30)]).minkowski_sum(mf.Manifold.cube([1,1,1],center=True));removedUsbC=cap^usbcut;cap-=usbcut
old=cap;bottom=dec('head_bottom');cuts=[]
for dz in np.arange(40,-.0001,-.25):
 cut=cap^bottom.translate([0,0,-dz])
 if cut.volume()>1e-5:cuts.append(cut)
cut=mf.Manifold.batch_boolean(cuts,mf.OpType.Add)
print('RAIL_CUT',cut.volume(),cut.bounding_box(),flush=True)
# Expand only the actual rail collision set by 0.20mm per side. Preserve the
# source outer surface except the explicitly declared local service/rail openings.
relief=cut.minkowski_sum(mf.Manifold.cube([.4,.4,.4],center=True));removed=old^relief;cap=old-relief
tri(removed).export(D/'internal-rail-relief-removed-world.stl');cap=cap.simplify(.00003);tri(cap).export(D/'curved-cap-final-candidate-world.stl')
for repairRound in range(3):
 stlmesh=trimesh.load(D/'curved-cap-final-candidate-world.stl',force='mesh');cap=man(stlmesh)
 if stlmesh.is_watertight and len(stlmesh.split())==1:break
 cap=cap.simplify(.00003);tri(cap).export(D/'curved-cap-final-candidate-world.stl')
stlmesh=trimesh.load(D/'curved-cap-final-candidate-world.stl',force='mesh');assert stlmesh.is_watertight and len(stlmesh.split())==1;cap=man(stlmesh)
print('CAP',len(cap.decompose()),cap.volume(), 'REMOVED',removed.volume(),removed.bounding_box(),flush=True)
excluded={'head_cap','camera_pitch_foot','camera_cradle','camera_board','camera_ribbon','face_panel','eye_trim','openrb','amplifier','speaker','audio_carrier'}
replacedHardware=[k for k,p in P.items() if str(p.get('fastenerId','')).startswith(('E-camera_','E-openrb-','E-audio'))]
fixed={k:dec(k) for k in P if k not in excluded and k not in replacedHardware}
# All source parts are present, not just the active head stage.
for k,f in [('face_panel','camera-retainer/face-with-camera-anchors-world.stl'),('camera_board','camera-retainer/camera-shifted-reference-world.stl'),('camera_retainer','camera-retainer/camera-retainer-world.stl'),('eye_trim','eye-trim-camera-clearance-world.stl')]:fixed[k]=load(V/f)
if (V/'camera-retainer/camera-all-six-screw-envelopes-world.stl').exists():fixed['camera_six_screws']=load(V/'camera-retainer/camera-all-six-screw-envelopes-world.stl')
for k in ['zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails']:fixed[k]=load(D/(k+'-world.stl'))
moving={'head_cap':cap}
for k in ['openrb','amplifier','speaker']:moving[k]=load(D/(k+'-curved-layout-world.stl'))
for k in ['speaker-cradle','speaker-keeper']:moving[k]=load(D/(k+'-world.stl'))
if (D/'cap-eight-screw-heads-four-nuts-world.stl').exists():moving['cap_hardware']=load(D/'cap-eight-screw-heads-four-nuts-world.stl')
rows=[];peak={}
for dz in np.arange(40,-.0001,-.25):
 h={}
 for k,s in moving.items():
  q=s.translate([0,0,dz])
  for n,o in fixed.items():
   vol=hits(q,o)
   if vol>1e-4:h[k+'--'+n]=vol;peak[k+'--'+n]=max(peak.get(k+'--'+n,0),vol)
 rows.append({'offsetZmm':float(dz),'intersectionsMm3':h})
print('PEAK',peak,flush=True)
report={'problemIds':['P5','P6'],'sourceDataSha256':hashlib.sha256(src.read_bytes()).hexdigest(),'stlSimplificationToleranceMm':.00003,'stlReadbackVerified':True,'stlRepairRounds':repairRound,'shellWatertight':stlmesh.is_watertight,'shellBodies':len(cap.decompose()),'replacedSourceHardware':replacedHardware,'usbCOpeningRemovedMm3':removedUsbC.volume(),'railRelief':{'removedVolumeMm3':removed.volume(),'boundsWorldMm':np.array(removed.bounding_box()).reshape(2,3).tolist(),'clearancePerSideMm':.2},'closurePath':{'startOffsetMm':[0,0,40],'endOffsetMm':[0,0,0],'stepMm':.25,'moving':list(moving),'fixed':list(fixed),'samples':rows,'peakIntersectionsMm3':peak},'loadedMeshHashes':loadedHashes,'sourceHashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.glob('*.stl')},'physicalFitVerified':False,'manufacturingAccepted':False}
(D/'populated-cap-assembly.json').write_text(json.dumps(report,indent=2)+'\n')
