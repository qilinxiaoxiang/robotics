"""Finite actual-route subtraction diagnostic, one source part/pose, no release."""
import argparse,json,math
from pathlib import Path
import segmented_yaw_forward_worker as w
w.core.guard();w.current();sr=json.loads((w.OUT/'self-summary.json').read_text());assert sr['passed'] and sr['planHash']==w.sha(w.OUT/'plan.json')
import numpy as np,trimesh,manifold3d as mf
from prepare_single_candidate import JOINTS,rot,add,sub
ap=argparse.ArgumentParser();ap.add_argument('--pose',type=int,required=True);ap.add_argument('--part',choices=['head_bottom','jaw_support'],required=True);o=ap.parse_args();row,g=w.route(o.pose);q=row['jointDegrees'];pts=[]
for pp in g['points']:
 for name,origin,axis in JOINTS:pp=add(origin,rot(sub(pp,origin),axis,-math.radians(q.get(name,0))))
 pts.append(pp)
ps=np.array(pts);t=np.gradient(ps,axis=0);t/=np.linalg.norm(t,axis=1)[:,None];normal=np.array([1.,0,0]);normal-=t[0]*(normal@t[0]);
if np.linalg.norm(normal)<.1:normal=np.array([0.,1,0]);normal-=t[0]*(normal@t[0])
normal/=np.linalg.norm(normal);v=[];faces=[];sides=24;radius=4.05
for pp,tt in zip(ps,t):
 normal-=tt*(normal@tt);normal/=np.linalg.norm(normal);bb=np.cross(tt,normal)
 for j in range(sides):a=2*math.pi*j/sides;v.append(pp+radius*(math.cos(a)*normal+math.sin(a)*bb))
for i in range(len(ps)-1):
 for j in range(sides):a=i*sides+j;b=i*sides+(j+1)%sides;c=(i+1)*sides+j;dd=(i+1)*sides+(j+1)%sides;faces.extend([[a,b,dd],[a,dd,c]])
for j in range(1,sides-1):faces.extend([[0,j+1,j],[(len(ps)-1)*sides,(len(ps)-1)*sides+j,(len(ps)-1)*sides+j+1]])
wire=trimesh.Trimesh(v,faces,process=True);wire.fix_normals();assert wire.is_watertight and wire.is_volume
man=w.H/'camera-ribbon-repair/positive-x225/candidate-manifest.json';manifest=json.loads(man.read_text());data=w.H.parent/'leg-guide-20261006/full-build-data.json';guide=json.loads(data.read_text())
if o.part=='head_bottom':src=w.H/manifest['replacementMeshes'][o.part];part=trimesh.load(src,force='mesh',process=True)
else:
 p=next(p for p in guide['parts'] if p['key']==o.part);src=w.H.parents[2]/p['sourceFile'];part=trimesh.load(src,force='mesh',process=True);part.apply_transform(p['sourceTransformWorld'])
assert part.is_watertight and part.is_volume
conv=lambda m:mf.Manifold(mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32)))
a,b=conv(wire),conv(part);assert a.status()==b.status()==mf.Error.NoError and a.volume()>0 and b.volume()>0
hit=a^b;candidate=b-a;assert hit.status()==candidate.status()==mf.Error.NoError
OUT=w.D/'yaw-structural-channel';OUT.mkdir(exist_ok=True)
def export(solid,name):
 if solid.volume()<=0:return None
 x=solid.to_mesh();m=trimesh.Trimesh(x.vert_properties[:,:3],x.tri_verts,process=False);assert m.is_watertight and m.is_volume;p=OUT/name;m.export(p);r=trimesh.load(p,force='mesh');assert r.is_watertight and r.is_volume;return {'file':str(p),'sha256':w.sha(p),'volumeMm3':float(solid.volume()),'components':len(r.split()),'bounds':r.bounds.tolist()}
protected=[]
for screw in guide['screws']:
 if screw.get('groupId')!='motor_support_frame':continue
 x,y,z=screw['world_center_mm'];guard=mf.Manifold.cylinder(40,4,4,48).translate([x,y,95]);s=hit^guard;assert s.status()==mf.Error.NoError;protected.append({'id':screw['id'],'axisWorld':screw['world_axis'],'centerWorld':screw['world_center_mm'],'protectedNativeMaterialWithinRadiusMm':4,'protectedZIntervalMm':[95,135],'removedMm3':float(s.volume())})
for k in ['head_roll_ring_a','head_roll_ring_b']:
 p=next(p for p in guide['parts'] if p['key']==k);lo,hi=np.array(p['bounds']);lo-=2;hi+=2;guard=mf.Manifold.cube((hi-lo).tolist()).translate(lo.tolist());s=hit^guard;assert s.status()==mf.Error.NoError;protected.append({'id':k,'region':'Source bearing bounds +2mm all directions','removedMm3':float(s.volume())})
r={'accepted':False,'sourceModified':False,'finiteDiagnosticOnly':True,'pose':o.pose,'jointDegrees':q,'part':o.part,'cutterNominalRadialMm':radius,'meaning':'Actual sampled-route loft plus about0.5mm radial design clearance, used to test whether even local grooves can preserve structural zones. Neither loft coverage between poses nor a release geometry is proved.','hit':export(hit,f'{o.pose}__{o.part}__intersection.stl'),'candidate':export(candidate,f'{o.pose}__{o.part}__finite-cut.stl'),'protectedRegions':protected,'protectedNativeMaterialUntouched':all(p['removedMm3']<1e-8 for p in protected),'sourceHashes':{str(p):w.sha(p) for p in [Path(__file__),src,man,data,w.OUT/'plan.json']}};w.save(OUT/f'{o.pose}__{o.part}.json',r);print(json.dumps(r))
