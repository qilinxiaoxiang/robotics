"""Two-piece speaker perimeter cage and amplifier posts on the original curved cap."""
from pathlib import Path
import numpy as np,trimesh,manifold3d as mf,json,base64
D=Path(__file__).resolve().parent;V=D.parent;data=json.loads((V.parent/'leg-guide-20261006/full-build-data.json').read_text());P={p['key']:p for p in data['parts']}
def man(m):return mf.Manifold(mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32)))
def tri(s):
 q=s.to_mesh();return trimesh.Trimesh(np.array(q.vert_properties)[:,:3],np.array(q.tri_verts),process=True)
def cyl(c,r,h):return mf.Manifold.cylinder(h,r,r,48,True).translate(c)
def box(c,d):return mf.Manifold.cube(d,True).translate(c)
def capsule(center,r,half,h):return mf.Manifold.batch_hull([cyl(np.array(center)+[0,-half,0],r,h),cyl(np.array(center)+[0,half,0],r,h)])
capmesh=trimesh.load(D/'community-curved-head-world.stl',force='mesh');cap=man(capmesh)
fixed={}
for k in ['head_yaw_link','motor13','neck_pitch','neck_pitch_ring','head_bottom','jaw_support','motor14','motor15','jaw_frame','upper_pad','lower_pad','pi']:
 p=P[k];fixed[k]=man(trimesh.Trimesh(np.array(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3)),np.array(np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3)),process=True))
for k in ['openrb','speaker','amplifier']:fixed[k]=man(trimesh.load(D/(k+'-curved-layout-world.stl'),force='mesh'))
for k in ['zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails']:fixed[k]=man(trimesh.load(D/(k+'-world.stl'),force='mesh'))
def hits(s,skip=[]):return {k:float((s^q).volume()) for k,q in fixed.items() if k not in skip and float((s^q).volume())>1e-4}
# Perimeter support only; centre left open for the factory grille and magnet.
frame=capsule([-3,12,129.04],10.85,5,1.2)-capsule([-3,12,129.04],8.4,5,2)
keeper=capsule([-3,12,132.95],10.85,5,1.0)-capsule([-3,12,132.95],8.4,5,2)
speaker_holes=[[-16,7],[-16,17]]
for x,y in speaker_holes:
 frame+=box([(x-3)/2,y,129.04],[abs(x+3),5,1.2]);keeper+=box([(x-3)/2,y,132.95],[abs(x+3),5,1.0])
 frame+=cyl([x,y,129.04],2.6,1.2);keeper+=cyl([x,y,132.95],2.6,1.0)
 frame-=cyl([x,y,129],1.4,4);keeper-=cyl([x,y,133],1.4,4)
# Remove any cross bars over the transducer; only outer ears join its rim.
frame-=capsule([-3,12,129.04],8.4,5,2);keeper-=capsule([-3,12,132.95],8.4,5,2)
bb=np.array(keeper.bounding_box()).reshape(2,3);near=cap^box(bb.mean(0),bb[1]-bb[0]+1);keeper-=near.minkowski_sum(box([0,0,0],[.3,.3,.3]))
posts=[];rows=[]
def conform_to_source_roof(p):
 bb=np.array(p.bounding_box()).reshape(2,3);near=cap^box([*bb.mean(0)[:2],140],[*(bb[1]-bb[0]+.02)[:2],60])
 # Exact original roof patches translated only downward fill the inner column.
 # Overlapping 0.5mm layers are narrower than the source wall thickness.
 # The original roof is the highest surface: additions cannot protrude above it.
 column=mf.Manifold.batch_boolean([near.translate([0,0,-z]) for z in np.arange(0,31,.5)],mf.OpType.Add)
 return p^column

# Keeper and cage are screw-fastened to short roof bosses; no snap-through lip.
for x,y in speaker_holes:
 start=133.45;loc,_,_=capmesh.ray.intersects_location([[x,y,start]],[[0,0,1]],multiple_hits=True);h=float(loc[:,2].min()-start+.55)
 p=cyl([x,y,start+h/2],2.6,h)-cyl([x,y,start+2.5],1.05,5.2);p=conform_to_source_roof(p);posts.append(p);rows.append({'owner':'speaker-cage','xyMm':[x,y],'startZmm':start,'postLengthMm':h,'intersectionsMm3':hits(p)})
# Adafruit official PCB holes local[2.54,16.51] and[15.24,16.51].
amp=trimesh.load(D/'amplifier-curved-layout-world.stl',force='mesh');lo=amp.bounds[0];amp_holes=[[lo[0]+x,lo[1]+16.51] for x in [2.54,15.24]]
for x,y in amp_holes:
 start=lo[2]+1.57;loc,_,_=capmesh.ray.intersects_location([[x,y,start]],[[0,0,1]],multiple_hits=True);h=float(loc[:,2].min()-start+.55)
 p=cyl([x,y,start+h/2],2.,h)-cyl([x,y,start+3.5],1.05,7.2);p=conform_to_source_roof(p);posts.append(p);rows.append({'owner':'amplifier','xyMm':[x,y],'startZmm':start,'postLengthMm':h,'intersectionsMm3':hits(p)})
combined=mf.Manifold.batch_boolean(posts,mf.OpType.Add)
for name,s in [('speaker-cradle-world.stl',frame),('speaker-keeper-world.stl',keeper),('audio-roof-posts-world.stl',combined)]:tri(s).export(D/name)
report={'status':'audio-mount-candidate','outerSurfaceRule':'All roof bosses clipped by downward-filled exact native roof patches; no outward protrusion' ,'posts':rows,'frameIntersectionsMm3':hits(frame),'keeperIntersectionsMm3':hits(keeper),'frameBodies':len(frame.decompose()),'keeperBodies':len(keeper.decompose()),'frameWatertight':tri(frame).is_watertight,'keeperWatertight':tri(keeper).is_watertight,'speakerAssembly':'Place speaker into open lower perimeter cradle; fit separate rear keeper; screw pair to roof bosses from below with cap detached. Nothing snaps through a closed lip.','amplifierAssembly':'Prewire amp and clamp terminal wires on bench; two PCB mounting holes fasten to roof posts from below, with cap detached.','fastenerIntent':'Four M2.5 x 8 tapping screws: speaker pair 5.01mm stack/2.99mm engagement; amp pair 1.57mm stack/6.43mm engagement. This is a geometric hardware requirement, not an inventory or purchase assertion.','manufacturingAccepted':False,'physicalFitVerified':False}
(D/'audio-mounts.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
