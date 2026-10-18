"""Internal cap mounts and explicit assembly-path diagnostics, source surfaces retained."""
from pathlib import Path
import json,base64,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;V=D.parent;G=V.parent/'leg-guide-20261006';data=json.loads((G/'full-build-data.json').read_text());P={p['key']:p for p in data['parts']};layout=json.loads((D/'curved-layout.json').read_text())
def man(m):return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
def tri(s):
 a=s.to_mesh();return trimesh.Trimesh(np.asarray(a.vert_properties)[:,:3],np.asarray(a.tri_verts),process=True)
def dec(k):
 p=P[k];return trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
def cyl(a,b,r,n=48):
 axis=np.array(b)-a;T=trimesh.geometry.align_vectors([0,0,1],axis);T[:3,3]=(np.array(a)+b)/2;return man(trimesh.creation.cylinder(radius=r,height=np.linalg.norm(axis),sections=n).apply_transform(T))
native=trimesh.load(D/'community-curved-head-world.stl',force='mesh');cap=man(native);oldcap=cap
meshes={k:dec(k) for k in ['head_yaw_link','motor13','neck_pitch','neck_pitch_ring','neck_link_a','neck_link_b','head_bottom','jaw_support','motor14','motor15','jaw_frame','upper_pad','lower_pad','head_roll_ring_a','head_roll_ring_b','pi']}
for k in ['openrb','speaker','amplifier']:meshes[k]=trimesh.load(D/(k+'-curved-layout-world.stl'),force='mesh')
for k in ['zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails','zero_w_usb_moulding']:meshes[k]=trimesh.load(D/(k+'-world.stl'),force='mesh')
for k,f in [('camera_board','camera-shifted-reference-world.stl'),('face_panel','face-with-camera-anchors-world.stl'),('camera_retainer','camera-retainer-world.stl')]:meshes[k]=trimesh.load(V/'camera-retainer'/f,force='mesh')
meshes['eye_trim']=trimesh.load(V/'eye-trim-camera-clearance-world.stl',force='mesh');sol={k:man(m) for k,m in meshes.items()}
# Roof mounts stop inside the original curved wall, never at an enlarged box.
T=np.array(layout['transformsFromGuideWorld']['openrb']);axis=T[:3,:3]@np.array([0,0,1.]);posts=[];holes=[];postrows=[]
for screw in [s for s in data['screws'] if s['id'].startswith('E-openrb-')]:
 c=(T@np.r_[screw['world_center_mm'],1])[:3];seat=c+axis*1.6;A=trimesh.geometry.align_vectors([0,0,1],axis)[:3,:3]
 origins=np.array([seat+A@np.array([3*np.cos(a),3*np.sin(a),.02]) for a in np.linspace(0,2*np.pi,24,endpoint=False)]+[seat+axis*.02]);directions=np.tile(axis,(len(origins),1));loc,ri,ti=native.ray.intersects_location(origins,directions,multiple_hits=True);dist=np.sum((loc-origins[ri])*axis,axis=1);first=[float(min(dist[ri==i])) for i in range(len(origins)) if len(dist[ri==i])];assert len(first)==len(origins)
 h=min(first)+.5;p=cyl(seat,seat+axis*h,3.0);through=cyl(c-axis*2,seat+axis*(h+.1),1.2);p=p-through
 # Two lateral nut windows form a removable captive-nut seat; no roof piercing.
 center=seat+axis*2.5;nut=trimesh.creation.cylinder(radius=4.3/np.sqrt(3),height=1.8,sections=6);nt=trimesh.geometry.align_vectors([0,0,1],axis);nt[:3,3]=center;cut=man(nut.apply_transform(nt));slot=trimesh.creation.box([8,4.3,1.8]);nt[:3,3]=center;cut=cut+man(slot.apply_transform(nt));p=p-cut
 bb=np.array(p.bounding_box()).reshape(2,3);near=sol['openrb']^mf.Manifold.cube(bb[1]-bb[0]+1).translate(bb[0]-.5)
 p=p-near.minkowski_sum(mf.Manifold.cube([.3,.3,.3],center=True))
 hits={k:max(0,float((p^q).volume())) for k,q in sol.items() if max(0,float((p^q).volume()))>1e-4};postrows.append({'screw':screw['id'],'pcbHoleCenterWorldMm':c.tolist(),'axisWorld':axis.tolist(),'postLengthMm':h,'roofRayInnerDistanceRangeMm':[min(first),max(first)],'intersectionsMm3':hits});print('POST',postrows[-1],flush=True);posts.append(p);holes.append(through)
new=cap+mf.Manifold.batch_boolean(posts,mf.OpType.Add)
# Cut the actual plug receiving volume locally, with0.5mm clearance. The shell
# outside this declared service opening is not offset, scaled or replaced.
usb=meshes['zero_w_usb_moulding'];lo,hi=usb.bounds;usbcut=mf.Manifold.cube(hi-lo+1).translate(lo-.5);removed_usb=new^usbcut;new=new-usbcut
tri(new).export(D/'curved-cap-with-internal-posts-and-usb-world.stl');tri(mf.Manifold.batch_boolean(posts,mf.OpType.Add)).export(D/'openrb-four-internal-posts-world.stl')
# Grouped cap descent: audio is a body-side candidate, OpenRB travels with cap.
fixed={k:q for k,q in sol.items() if k not in ['openrb','zero_w_usb_moulding']};moving={'curved_cap':new,'openrb':sol['openrb']};rows=[];peak={}
for dz in np.arange(40,-.0001,-.5):
 hits={}
 for k,s in moving.items():
  q=s.translate([0,0,dz]);b=np.array(q.bounding_box()).reshape(2,3)
  for n,obs in fixed.items():
   ob=np.array(obs.bounding_box()).reshape(2,3)
   if np.any(b[0]>=ob[1]) or np.any(ob[0]>=b[1]):continue
   vol=max(0,float((q^obs).volume()))
   if vol>.02:hits[k+'--'+n]=vol;peak[k+'--'+n]=max(peak.get(k+'--'+n,0),vol)
 rows.append({'offsetZmm':float(dz),'intersectionsMm3':hits})
print('CLOSURE_PEAK',peak,flush=True)
report={'status':'internal-roof-mount-candidate-assembly-path-investigation','posts':postrows,'shellWatertight':tri(new).is_watertight,'shellBodies':len(new.decompose()),'usbOpeningRemovedMm3':removed_usb.volume(),'usbReceivingEnvelope':'25x18x8mm, plus0.5mm local relief; moulding must be measured','exteriorPolicy':'Original curved source retained except explicitly localized USB service opening. Added posts terminate inside original wall; no outward bulge.','closurePath':{'startOffsetMm':[0,0,40],'endOffsetMm':[0,0,0],'stepMm':.5,'moving':['curved_cap','openrb'],'fixed':list(fixed),'samples':rows,'peakIntersectionsMm3':peak},'pending':['Roof-post fastener stack and side-nut access require independent checks','Audio carrier retention not yet complete','Camera cable loop and USB plug receiving dimensions','Full physical fit/strength'],'physicalFitVerified':False}
(D/'mounts-and-paths.json').write_text(json.dumps(report,indent=2)+'\n')
