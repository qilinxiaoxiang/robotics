"""Shared isolated flat loom geometry; caller must own bounded CAD guard."""
import json,math
import numpy as np,trimesh,manifold3d as mf
import segmented_yaw_forward_worker as w
from rolling_loop_math import rolling_loop
from prepare_single_candidate import JOINTS,rot,add,sub
def specs_for_pose(pose):
 row={'jointDegrees':{}} if pose==-1 else json.loads(w.BASE.read_text())['samples'][pose];q=row['jointDegrees'];parent={k:q.get(k,0) for k in ['neck_pitch','head_pitch']}
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
 return specs
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
