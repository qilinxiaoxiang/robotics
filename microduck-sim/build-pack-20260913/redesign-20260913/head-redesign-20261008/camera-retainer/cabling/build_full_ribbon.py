#!/usr/bin/env python3
"""Full-length, conservative-width SC1892 routing candidate with explicit failure gates.
The route is a finite-radius planar strip, never a cosmetic line or clipped length.
"""
from pathlib import Path
import json,hashlib,base64,sys
import numpy as np,trimesh,manifold3d as mf
from scipy.optimize import brentq
D=Path(__file__).resolve().parent;R=D/'rotated-camera-candidate';H=D.parent.parent;C=H/'curved-head';G=H.parent/'leg-guide-20261006'
data=json.loads((G/'full-build-data.json').read_text());P={p['key']:p for p in data['parts']}
def man(m):
 m=m.copy();m.process();return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
def tri(s):
 a=s.to_mesh();return trimesh.Trimesh(np.asarray(a.vert_properties)[:,:3],np.asarray(a.tri_verts),process=True)
def dec(k):
 p=P[k];return man(trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True))
def box(lo,hi):return mf.Manifold.cube(np.array(hi)-lo).translate(lo)
# World mount derived from rotated camera connector exit; Zero drawing places
# CSI at65mm board end. Its exact contact height and insertion depth are assumptions.
cam=np.array([74.73,9.3706236,131.1145958]);pi=np.array([65.8,32.4886208,131.0496]);end_z=cam[2]
# 5mm/4.4mm contact insertion reservations are explicit assumptions, not claimed
# SC1892 manufacturer insertion-depth values. These count toward200mm.
def make_path(loopx,radius=6.):
 wp=np.array([cam-[0,5,0],[cam[0],40,end_z],[loopx,40,end_z],[loopx,20,end_z],[46,20,end_z],[46,38.4886208,end_z],[pi[0],38.4886208,end_z],pi-[0,4.4,0]],float)
 # Pi port Z differs0.065mm from camera; retain planar routing and record this
 # connector height uncertainty separately rather than a kink hidden by a mesh.
 wp[-1,2]=end_z
 cuts=[]
 for i in range(1,len(wp)-1):
  u=wp[i]-wp[i-1];u/=np.linalg.norm(u);v=wp[i+1]-wp[i];v/=np.linalg.norm(v);theta=np.arccos(np.clip(u@v,-1,1));d=radius*np.tan(theta/2);axis=np.cross(u,v);axis/=np.linalg.norm(axis);a=wp[i]-u*d;b=wp[i]+v*d;center=a+np.cross(axis,u)*radius;cuts.append((a,b,center,axis,theta,d))
 # Each straight must have nonnegative remaining length after tangent cuts.
 for i in range(len(wp)-1):
  used=(cuts[i-1][5] if i else 0)+(cuts[i][5] if i<len(cuts) else 0)
  assert np.linalg.norm(wp[i+1]-wp[i])+1e-7>=used,(i,'fillets overlap')
 pts=[wp[0]];total=0.;prev=wp[0]
 for a,b,center,axis,theta,d in cuts:
  le=np.linalg.norm(a-prev);n=max(1,int(np.ceil(le/.25)));pts.extend(np.linspace(prev,a,n+1)[1:]);total+=le
  va=a-center;n=max(2,int(np.ceil(radius*theta/.25)))
  for ang in np.linspace(0,theta,n+1)[1:]:pts.append(center+va*np.cos(ang)+np.cross(axis,va)*np.sin(ang)+axis*np.dot(axis,va)*(1-np.cos(ang)))
  total+=radius*theta;prev=b
 le=np.linalg.norm(wp[-1]-prev);n=max(1,int(np.ceil(le/.25)));pts.extend(np.linspace(prev,wp[-1],n+1)[1:]);total+=le
 return np.array(pts),total,wp
loopx=brentq(lambda x:make_path(x)[1]-200.,-20,20);points,L,waypoints=make_path(loopx)
# Entire body16mm wide, narrowing only over final6mm to mini end11.5mm.
# This conservative receiving envelope does not assert SC1892 body's true width.
s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))];width=16-4.5*np.clip((s-(s[-1]-6))/6,0,1);thickness=.6
v=np.gradient(points,axis=0);v/=np.linalg.norm(v,axis=1)[:,None];w=np.tile([0,0,1.],(len(points),1));n=np.cross(v,w);verts=[]
for p,ww,nn,wd in zip(points,w,n,width):verts.extend([p-ww*wd/2-nn*thickness/2,p+ww*wd/2-nn*thickness/2,p+ww*wd/2+nn*thickness/2,p-ww*wd/2+nn*thickness/2])
faces=[[0,2,1],[0,3,2]]
for i in range(len(points)-1):
 for j in range(4):a=4*i+j;b=4*i+(j+1)%4;c=b+4;d=a+4;faces.extend([[a,b,c],[a,c,d]])
nv=len(verts);faces.extend([[nv-4,nv-3,nv-2],[nv-4,nv-2,nv-1]])
m=trimesh.Trimesh(verts,faces,process=True);trimesh.repair.fix_normals(m);cable=man(m);assert cable.status()==mf.Error.NoError;assert m.is_watertight
m.export(D/'sc1892-full-200mm-BLOCKED-world.stl')
files={'curved_cap':C/'curved-cap-final-candidate-world.stl','camera':R/'camera-shifted-reference-world.stl','retainer':R/'camera-retainer-world.stl','face':R/'face-with-camera-anchors-world.stl','six_camera_screws':R/'camera-all-six-screw-envelopes-world.stl'}
for name in ['openrb','speaker','amplifier']:files[name]=C/(name+'-curved-layout-world.stl')
for name in ['zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails','audio-roof-posts','speaker-cradle','speaker-keeper','cap-eight-screw-heads-four-nuts']:files[name]=C/(name+'-world.stl')
obs={k:man(trimesh.load_mesh(p)) for k,p in files.items()};obs.update({k:dec(k) for k in ['pi','head_bottom','jaw_support','motor14','motor15']})
# Only mating contact slots may be occupied: their receiving geometry is missing
# in the source board envelopes; no shell collision is excluded.
slots={'camera':box(cam-[.5,5.1,8.1],cam+[.5,.01,8.1]),'zero_w_components':box(pi-[.5,4.5,5.9],pi+[.5,.01,5.9])}
hits={}
for k,o in obs.items():
 q=cable^(o-slots[k] if k in slots else o);vol=max(0,q.volume());hits[k]={'volumeMm3':vol,'intersectionBoundsMm':list(q.bounding_box()) if vol>1e-5 else None}
# Full cap/OpenRB/audio closure assembly translated40→0Z; FFC is body/face-side.
closure=[]
for dz in np.arange(40,-.001,-.5):
 row={}
 for k in ['curved_cap','openrb','audio-roof-posts','speaker','amplifier','speaker-cradle','speaker-keeper','cap-eight-screw-heads-four-nuts']:
  vol=max(0,(obs[k].translate([0,0,float(dz)])^cable).volume())
  if vol>1e-5:row[k]=vol
 closure.append({'offsetZMm':float(dz),'intersectionsMm3':row})
blocking={k:v for k,v in hits.items() if v['volumeMm3']>1e-5};status='BLOCKED_CONSERVATIVE_FULL_WIDTH_ROUTE' if blocking else 'CANDIDATE_GEOMETRY_CLEAR_NOT_PHYSICAL_CERTIFICATION'
report={'checked':'2026-10-08','status':status,'netUnchanged':'SC1224 camera15contact -> SC1892 -> ZeroW22contact CSI','existingCable':'SC1892','nominalLengthMm':200,'analyticCenterlineLengthMm':L,'meshChordLengthMm':float(s[-1]),'maxCenterlineStepMm':float(np.linalg.norm(np.diff(points,axis=0),axis=1).max()),'minimumBendRadiusMm':6,'bendRadiusEvidence':'Design assumption; no manufacturer SC1892 minimum bend radius found. Not a tested safe radius.','fullBodyReceivingWidthMm':16,'miniEndWidthMm':11.5,'receivingThicknessMm':.6,'widthThicknessEvidence':'Conservative receiving dimensions, not measured SC1892 body dimensions. No5mm-body pass is permitted.','cameraMouthWorldMm':cam.tolist(),'piMouthWorldMm':pi.tolist(),'piContactHeightMismatchMm':float(end_z-pi[2]),'contactInsertionAssumptionsMm':[5,4.4],'rotation':'Camera -90deg about worldX; horizontal/vertical FOV67x102, image rotation required','waypointsMm':waypoints.tolist(),'centerlineWorldMm':points.tolist(),'staticChecks':hits,'blockingIntersections':blocking,'closurePath':{'moving':['curved_cap','openrb','audio-roof-posts','speaker','amplifier','speaker-cradle','speaker-keeper'],'fixed':['fullFFC','camera','retainer','face','ZeroW'],'stepMm':.5,'samples':closure},'assemblyOrder':['Power disconnected; work with detached face and loose ZeroW before closing head.','Install camera and four camera screws onto retainer, then attach retainer to face with two wing screws.','Lay existing200mm cable through open routing clips before latching either end; no closed shell hole is threaded.','Open camera latch, seat15contact free end squarely by contact marking, close latch.','With ZeroW supported outside its final mount, open22contact latch, seat mini end by contact marking, close latch.','Only after a full-width route passes, mount Pi and retain excess in a radius-controlled loose loop; keep all cable outside fastener driver paths.','Cap closure prohibited by the current blocking report; do not force the ribbon or hide excess length.'],'clamping':'No clamp issued because the full-width route does not pass; a clip at this failed path would institutionalize the collision.','freeEndAndLatchStatus':'Connector mating strokes and finger clearance need exact connector/cable measurement; board envelope is not detailed latch CAD.','viewerPolicy':'Diagnostic red blocked candidate only; do not replace published cable with an apparently assembled green route.','requiredMeasurements':['Actual SC1892 middle ribbon maximum width and total thickness including shielding','Rigid/stiffener lengths and thickness at both ends','Actual ZeroW CSI mouth height and latch travel in selected board pose','Permitted static minimum bend radius or a non-damaging fit test'],'physicalFitVerified':False,'manufacturingCertified':False,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files.values()},'sources':[{'url':'https://www.raspberrypi.com/products/camera-cable/','fact':'Camera cable22-way support for Zero models and200mm length option'},{'path':str(H.parent/'design-contract.json'),'fact':'ExistingSC1892camera200mm15-to22net'}, {'url':'https://datasheets.raspberrypi.com/rpizero/raspberry-pi-zero-w-mechanical-drawing.pdf','fact':'CSI at end of65x30board; exact contact height not dimensioned'}]}
(D/'full-ribbon-report.json').write_text(json.dumps(report,indent=2)+'\n')
part={'key':'eye_camera_sc1892_full_diagnostic','name':'SC1892 200mm full route — blocked','color':'#d24b45','moduleId':'camera','partKind':'cable','geometryKind':'blocked-routing-candidate','description':'Conservative16mm width; explicit interference remains. Do not install or treat as passed.','positionB64':base64.b64encode(np.asarray(m.vertices,dtype='<f4').tobytes()).decode(),'indexB64':base64.b64encode(np.asarray(m.faces,dtype='<u4').tobytes()).decode(),'bounds':m.bounds.tolist(),'center':m.bounds.mean(axis=0).tolist(),'sourceTransformWorld':np.eye(4).tolist(),'triangles':len(m.faces),'approachVector':[0,0,0]}
(D/'viewer-fragment.json').write_text(json.dumps({'diagnosticOnly':True,'requiresGeometryFix':True,'append':[part],'replacements':[]},separators=(',',':'))+'\n')
print(json.dumps({'status':status,'lengthMm':L,'loopX':loopx,'blocking':blocking},indent=2))
# Candidate investigation exits normally; only explicit --accept may gate a handoff.
if '--accept' in sys.argv:assert not blocking and abs(end_z-pi[2])<.01,'Full ribbon acceptance failed; see report.'
