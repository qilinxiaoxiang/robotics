"""Finite per-wire flat loom structural diagnostic. No canonical geometry mutation."""
import argparse,json,math
from pathlib import Path
import segmented_yaw_forward_worker as w
from rolling_loop_math import rolling_loop
from prepare_single_candidate import JOINTS,rot,add,sub
w.core.guard()
import numpy as np,trimesh,manifold3d as mf
ap=argparse.ArgumentParser();ap.add_argument('--pose',type=int,required=True);ap.add_argument('--part',choices=['head_bottom','jaw_support'],required=True);o=ap.parse_args()
OUT=w.D/'flat-yaw-channel';OUT.mkdir(exist_ok=True)
row={'jointDegrees':{}} if o.pose==-1 else json.loads(w.BASE.read_text())['samples'][o.pose];q=row['jointDegrees'];parent={k:q.get(k,0) for k in ['neck_pitch','head_pitch']}
netfile=w.D/'low-voltage-neck-net-map.json';nets=json.loads(netfile.read_text())
specs=[]
for ids,R,pitch,od in [(['pi-5v-2','pi-5v-4','pi-gnd-6','pi-gnd-14','openrb-ground'],31,1.95,1.8),(['imu-vin','imu-sda','imu-scl','imu-gnd','audio-vin','audio-return'],35,1.7,1.5)]:
 for j,key in enumerate(ids):
  zi=(j-(len(ids)-1)/2)*pitch;g=rolling_loop([26,0,97+zi],[0,0,1],[2**-.5,-2**-.5,0],R,18-2*zi,math.radians(87),math.radians(q.get('head_yaw',0)),.35)
  ps=[]
  for p in g['points']:
   p=w.moved(p,parent)
   for name,origin,axis in JOINTS:p=add(origin,rot(sub(p,origin),axis,-math.radians(q.get(name,0))))
   ps.append(p)
  specs.append({'key':key,'receivingODMm':od,'R':R,'zi':zi,'lengthMm':g['analyticLengthMm'],'minimumBendRadiusMm':g['minimumCenterlineRadiusMm'],'points':ps})
def conv(m):
 assert m.is_watertight and m.is_volume
 s=mf.Manifold(mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32)));assert s.status()==mf.Error.NoError and s.volume()>0;return s
def tube(points,r):
 ps=np.array(points);t=np.gradient(ps,axis=0);t/=np.linalg.norm(t,axis=1)[:,None];n=np.array([1.,0,0]);n-=t[0]*(n@t[0])
 if np.linalg.norm(n)<.1:n=np.array([0.,1,0]);n-=t[0]*(n@t[0])
 n/=np.linalg.norm(n);vs=[];fs=[];sides=16;r=(r+.005)/math.cos(math.pi/sides)
 for pp,tt in zip(ps,t):
  n-=tt*(n@tt);n/=np.linalg.norm(n);bb=np.cross(tt,n)
  for j in range(sides):a=2*math.pi*j/sides;vs.append(pp+r*(math.cos(a)*n+math.sin(a)*bb))
 for i in range(len(ps)-1):
  for j in range(sides):a=i*sides+j;b=i*sides+(j+1)%sides;c=(i+1)*sides+j;d=(i+1)*sides+(j+1)%sides;fs.extend([[a,b,d],[a,d,c]])
 for j in range(1,sides-1):fs.extend([[0,j+1,j],[(len(ps)-1)*sides,(len(ps)-1)*sides+j,(len(ps)-1)*sides+j+1]])
 m=trimesh.Trimesh(vs,fs,process=True);m.fix_normals();return conv(m)
man=w.H/'camera-ribbon-repair/positive-x225/candidate-manifest.json';manifest=json.loads(man.read_text());data=w.H.parent/'leg-guide-20261006/full-build-data.json';guide=json.loads(data.read_text())
if o.part=='head_bottom':src=w.H/manifest['replacementMeshes'][o.part];part=trimesh.load(src,force='mesh',process=True)
else:
 p=next(p for p in guide['parts'] if p['key']==o.part);src=w.H.parents[2]/p['sourceFile'];part=trimesh.load(src,force='mesh',process=True);part.apply_transform(p['sourceTransformWorld'])
b=conv(part);cuts=[];hitparts=[];wirehits=[]
for spec in specs:
 a=tube(spec['points'],spec['receivingODMm']/2+.5);hit=a^b;assert hit.status()==mf.Error.NoError
 wirehits.append({'key':spec['key'],'removedMm3':hit.volume()});cuts.append(a);hitparts.append(hit)
 print(json.dumps(wirehits[-1]),flush=True)
candidate=b
for c in cuts:candidate=candidate-c
hit=hitparts[0]
for c in hitparts[1:]:hit=hit+c;assert hit.status()==candidate.status()==mf.Error.NoError
protected=[]
for screw in guide['screws']:
 if screw.get('groupId')!='motor_support_frame':continue
 x,y,z=screw['world_center_mm'];zone=mf.Manifold.cylinder(40,4,4,48).translate([x,y,95]);removed=hit^zone;axis=mf.Manifold.cylinder(40,.001,.001,12).translate([x,y,95]);gap=axis.min_gap(hit,8) if hit.volume()>0 else 8
 protected.append({'id':screw['id'],'center':screw['world_center_mm'],'R4RemovedMm3':removed.volume(),'axisDistanceToRemovedMaterialLowerBoundMm':gap,'searchCapMm':8,'pilotRadiusMm':1.1,'radialWallLowerBoundMm':gap-1.1,'actualThreadOnly':False,'removedBounds':list(removed.bounding_box()) if removed.volume()>1e-7 else None,'actualThreadZoneRemovedMm3':(hit ^ mf.Manifold.cylinder(8,2.6,2.6,48).translate([x,y,z-6])).volume()})
for k in ['head_roll_ring_a','head_roll_ring_b']:
 p=next(p for p in guide['parts'] if p['key']==k);lo,hi=np.array(p['bounds']);lo-=2;hi+=2;zone=mf.Manifold.cube((hi-lo).tolist()).translate(lo.tolist());protected.append({'id':k,'bearingBoundsPlusMm':2,'removedMm3':(hit^zone).volume()})
def export(s,name):
 if s.volume()<=0:return None
 beforeVolume=s.volume();nativeComponents=len(s.decompose());componentVolumes=sorted([c.volume() for c in s.decompose()],reverse=True);s=s.as_original().simplify(.001);assert s.status()==mf.Error.NoError;m=s.to_mesh();m=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);assert m.is_watertight and m.is_volume;p=OUT/name;m.export(p);r=trimesh.load(p,force='mesh');return {'nativeComponents':nativeComponents,'nativeComponentVolumesMm3':componentVolumes,'simplifyToleranceMm':.001,'simplifyVolumeDeltaMm3':s.volume()-beforeVolume,'exportReadbackWatertight':bool(r.is_watertight),'exportReadbackPositiveVolume':bool(r.is_volume),'file':str(p),'sha256':w.sha(p),'volumeMm3':s.volume(),'components':len(r.split()),'bounds':r.bounds.tolist()}
r={'accepted':False,'finiteDiagnosticOnly':True,'pose':o.pose,'jointDegrees':q,'part':o.part,'radialDesignClearanceMm':.5,'individualWires':[{k:v for k,v in s.items() if k!='points'} for s in specs],'individualCuts':wirehits,'hit':export(hit,f'{o.pose}__{o.part}__removed.stl'),'candidate':export(candidate,f'{o.pose}__{o.part}__cut.stl'),'protectedRegions':protected,'sourceHashes':{str(p):w.sha(p) for p in [Path(__file__),src,man,data,netfile,w.D/'rolling_loop_math.py',w.BASE]}}
w.save(OUT/f'{o.pose}__{o.part}.json',r);print(json.dumps(r))
