"""Single causal speaker cage ear relocation; original speaker and shell stay fixed."""
from pathlib import Path
import json,hashlib,gc,os
assert os.environ.get('MICRODUCK_BOUNDED_CAD')
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;F=D.parents[1]/'power-sensor/head-controller-study/final-integration-20261009';src=F/'custom-harness-package.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(q):
 assert sha(q['file'])==q['sha256'];m=trimesh.load(q['file'],force='mesh');m.apply_transform(q['worldTransform']);s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError,(q['key'],s.status());return s
parts=json.loads(src.read_text())['parts'];rows={q['key']:q for q in parts};speakerrow=next(q for q in parts if q['key']=='REFERENCE current speaker');keeperrow=next(q for q in parts if q['key']=='REFERENCE current speaker_keeper');cradlerow=next(q for q in parts if q['key']=='current_cradle');caprow=next(q for q in parts if q['key']=='current_cap');cap=load(caprow);sp=load(speakerrow)
def box(c,d):return mf.Manifold.cube(d,True).translate(c)
def cyl(c,r,h):return mf.Manifold.cylinder(h,r,r,64,True).translate(c)
def capsule(z,h):return mf.Manifold.batch_hull([cyl([20,-21.5,z],10.85,h),cyl([30,-21.5,z],10.85,h)])
def bounds(s):return np.array(s.bounding_box()).reshape(2,3).tolist()
def export(s,name):
 mesh=s.to_mesh64();m=trimesh.Trimesh(np.asarray(mesh.vert_properties)[:,:3],np.asarray(mesh.tri_verts),process=False);p=D/name;p.write_text(trimesh.exchange.stl.export_stl_ascii(m));back=trimesh.load(p,force='mesh');assert back.is_watertight and back.is_winding_consistent;return {'file':str(p),'sha256':sha(p),'volumeMm3':s.volume(),'bounds':bounds(s),'closed':True}
checks=[];made={};old={}
for name,row,z,h in [('speaker_cradle',cradlerow,132.04,1.2),('speaker_keeper',keeperrow,135.95,1.)]:
 a=load(row);old[name]=a;core=a^capsule(z,h);cuts=a-core
 # Opposed long-axis ears leave controller Y span unobstructed. New bosses/holes
 # retain the existing M2.5x8 source interface, but acquire new roof seats.
 b=core
 for x in [5.,45.]:
  ringx=10.5 if x<25 else 39.5
  b+=box([(x+ringx)/2,-21.5,z],[abs(ringx-x),5.2,h])+cyl([x,-21.5,z],2.6,h)
  b-=cyl([x,-21.5,z],1.4,10)
 if name=='speaker_keeper':
  B=np.array(b.bounding_box()).reshape(2,3);near=cap^box(B.mean(0),B[1]-B[0]+2);b-=near.minkowski_sum(box([0,0,0],[1.,1.,1.]))
 checks.append({'part':name,'oldCapIntersectionMm3':(a^cap).volume(),'oldEarRemovedMm3':cuts.volume(),'retainedCoreCapIntersectionMm3':(core^cap).volume(),'newCapIntersectionMm3':(b^cap).volume(),'speakerIntersectionMm3':(b^sp).volume(),'components':len(b.decompose())})
 made[name]=b
# Conformal roof posts retain the exterior exactly. Only source roof patches
# translated inward fill the columns; pilots stop below the original outside.
posts=[];mounts=[];capmesh=trimesh.load(caprow['file'],force='mesh');capmesh.apply_transform(caprow['worldTransform'])
for x in [5.,45.]:
 y=-21.5;seat=136.45
 disk=np.array([[x,y,seat]]+[[x+2.6*np.cos(a),y+2.6*np.sin(a),seat]for a in np.linspace(0,2*np.pi,65)[:-1]])
 loc,ind,_=capmesh.ray.intersects_location(disk,np.tile([0,0,1],(len(disk),1)),multiple_hits=True)
 heights={i:sorted(loc[ind==i,2])for i in range(len(disk))};assert all(len(z)>=2 for z in heights.values()),'Post outside roof projection'
 minOuter=min(z[-1]for z in heights.values());maxInner=max(z[0]for z in heights.values())
 pilotDepth=3.3;assert minOuter-seat-pilotDepth>.6,('Blind pilot external skin',x,minOuter-seat-pilotDepth)
 near=cap^box([x,y,148],[5.3,5.3,40]);column=mf.Manifold.batch_boolean([near.translate([0,0,-dz])for dz in np.arange(0,31,.5)],mf.OpType.Add)
 post=cyl([x,y,(seat+160)/2],2.6,160-seat)^column
 post-=cyl([x,y,seat+pilotDepth/2],1.05,pilotDepth)
 posts.append(post);mounts.append({'xyMm':[x,y],'seatZMm':seat,'pilotDiameterMm':2.1,'pilotDepthMm':pilotDepth,'bossDiameterMm':5.2,'sourceRayMinimumOuterZMm':minOuter,'minimumSampledAxialBlindSkinMm':minOuter-seat-pilotDepth,'sourceRayMaximumInnerZMm':maxInner,'fastener':'M2.5 x 8 tapping engineering intent; verify actual plastic-thread fit','stackMm':5.01,'engagementMm':2.99,'bottomAllowanceMm':.31})
postset=mf.Manifold.batch_boolean(posts,mf.OpType.Add);made['speaker_roof_posts']=postset
capWithPosts=cap+postset;assert len(capWithPosts.decompose())==len(cap.decompose())
export(capWithPosts,'cap-with-speaker-posts-candidate-world.stl')
out={'sourceManifest':str(src),'sourceSha256':sha(src),'scriptSha256':sha(__file__),'wholeHeadAccepted':False,'speakerTransformUnchanged':speakerrow['worldTransform'],'mountHoleCentersMm':[[5,-21.5],[45,-21.5]],'checks':checks,'mounts':mounts,'parts':[{'key':k,**export(s,k+'-candidate-world.stl')}for k,s in made.items()]}
(D/'candidate.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(checks))
