"""Rebuild four interior Pi pillars and two camera anchors without changing face exterior."""
from pathlib import Path
import os,json,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n)
source=n['source'];mesh=n['mesh'];volume=n['volume'];load=n['loadfile'];read=n['read'];read(Path(__file__))
pose=json.loads(read(D/'lowered-pose-pair-checks.json'));T=np.array(pose['worldTransform']);normal=T[:3,0]
rows=json.loads(read(D/'head-source-cache/head-screws.json'));read(H/'face-eye-camera-clearance-world.stl');old=load(H/'face-eye-camera-clearance-world.stl');face=old
# Delete only the protruding interiors of old supports; the face wall at X>=77.1 is retained.
for sc in rows:
 a=np.array(sc['world_center_mm']);face-=mf.Manifold.cube([77.1-68.8,8,8]).translate([68.8,a[1]-4,a[2]-4])
# Open rear receiver pockets for the actual rotated cartridge. Added posts/anchors follow.
ret=load(D/'retainer-roll90-local-world.stl');read(D/'retainer-roll90-local-world.stl');rb=np.array(ret.bounding_box()).reshape(2,3)
face-=mf.Manifold.cube([78.27999420166016-68.8,rb[1,1]-rb[0,1]+.6,rb[1,2]-rb[0,2]+.6]).translate([68.8,rb[0,1]-.3,rb[0,2]-.3])
cam=load(D/'camera-roll90-local-world.stl');read(D/'camera-roll90-local-world.stl');cb=np.array(cam.bounding_box()).reshape(2,3)
face-=mf.Manifold.cube([79.9-68.8,cb[1,1]-cb[0,1]+.6,cb[1,2]-cb[0,2]+.6]).translate([68.8,cb[0,1]-.3,cb[0,2]-.3])
removed=old-face;stripped=face
anchors=load(D/'camera-anchors-roll90-local-world.stl');read(D/'camera-anchors-roll90-local-world.stl');face+=anchors
hardware=[];posts=[]
def cylinder(a,d,l,r):
 # local cylinder z axis -> supplied axis; stable right-handed orthonormal basis.
 d=np.asarray(d)/np.linalg.norm(d);u=np.cross(d,[0,0,1.]);u/=np.linalg.norm(u);v=np.cross(d,u);M=np.column_stack([u,v,d,a]);return mf.Manifold.cylinder(l,r,circular_segments=48).transform(M)
for sc in rows:
 a=(T@np.r_[sc['world_center_mm'],1])[:3];b=a+normal*1.6;l=(80.9-b[0])/normal[0]
 post=cylinder(b,normal,l,3.0);pilot=cylinder(b-normal*.01,normal,5.51,1.05);post-=pilot;face+=post
 screw=cylinder(a,normal,6,1.25)+cylinder(a,-normal,1.5,2)
 name=sc['id']+'-lowered-screw-world.stl';mesh(screw).export(D/name);read(D/name)
 posts.append(post);hardware.append({'id':sc['id'],'spec':'M2.5 x 6 TAP Uxcell a16060200ux0367','headSeatMm':a.tolist(),'outwardAxis':(-normal).tolist(),'pcbThroughMm':1.6,'printedEngagementMm':4.4,'pilotDepthMm':5.5,'pilotDiameterMm':2.1,'radialWallMm':1.95,'tipMarginMm':1.1,'mesh':name,'postLengthMm':l})
# Physical roundtrip mesh, same normalized coordinates as subsequent checks.
out=D/'face-pi-camera-roll90-world.stl';mesh(face).export(out);read(out)
checks=[]
for k,f in [('pi','pi-lowered-pose-world.stl'),('components','zero_w_components-lowered-pose-world.stl'),('tails','zero_w_gpio_solder_tails-lowered-pose-world.stl'),('gpio','gpio_discrete12_receiving-lowered-pose-world.stl'),('camera','camera-roll90-local-world.stl'),('retainer','retainer-roll90-local-world.stl'),('csi_end','pi-lowered-end-turn--1-world.stl')]:
 s=load(D/f);read(D/f);v,bb=volume(face,s);checks.append({'part':k,'overlapMm3':v,'bounds':bb});del s;gc.collect()
# Construction clips modifications to x<81.15; exact exterior protected half-space comparison.
protect=mf.Manifold.cube([40,120,80]).translate([81.15,-60,90]);outerDelta=(face^protect)-(old^protect);outerRemoved=(old^protect)-(face^protect)
r={'accepted':False,'status':'FACE_PILLARS_LOCAL_CANDIDATE','worldTransform':T.tolist(),'sourceBodies':len(old.decompose()),'bodiesAfterOldPostRemoval':len(stripped.decompose()),'candidateBodies':len(face.decompose()),'watertight':mesh(face).is_watertight,'removedOldPostVolumeMm3':removed.volume(),'changedExteriorBeyondX81_15Mm3':max(0,outerDelta.volume())+max(0,outerRemoved.volume()),'oldPostRemovalExtent':{'x':[68.8,77.1],'yHalfwidth':4,'zHalfwidth':4},'fasteners':hardware,'checks':checks,'sourceHashes':n['hashes'],'physicalFitVerified':False,'strengthVerified':False}
(D/'face-roll90-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['sourceHashes','fasteners']},indent=2))
