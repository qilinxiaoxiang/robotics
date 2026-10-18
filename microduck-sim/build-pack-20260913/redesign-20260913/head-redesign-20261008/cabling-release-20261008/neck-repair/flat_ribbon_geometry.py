"""Two smooth receiving channels enclose11 individually unchanged round wires."""
import math,json
import numpy as np,trimesh,manifold3d as mf
import flat_yaw_geometry as g
from rolling_loop_math import rolling_loop
from prepare_single_candidate import JOINTS,rot,add,sub

def channels(pose):
 row={'jointDegrees':{}} if pose==-1 else json.loads(g.w.BASE.read_text())['samples'][pose];q=row['jointDegrees'];parent={k:q.get(k,0) for k in ['neck_pitch','head_pitch']};answer=[]
 for R,wide,thin,keys in [(31,5.31,1.41,['pi-5v-2','pi-5v-4','pi-gnd-6','pi-gnd-14','openrb-ground']),(35,5.51,1.26,['imu-vin','imu-sda','imu-scl','imu-gnd','audio-vin','audio-return'])]:
  loop=rolling_loop([26,0,97],[0,0,1],[2**-.5,-2**-.5,0],R,18,math.radians(87),math.radians(q.get('head_yaw',0)),.4);points=[]
  for p in loop['points']:
   p=g.w.moved(p,parent)
   for name,origin,axis in JOINTS:p=add(origin,rot(sub(p,origin),axis,-math.radians(q.get(name,0))))
   points.append(p)
  n=g.w.moved([2**-.5,-2**-.5,0],parent,True)
  for name,origin,axis in JOINTS:n=rot(n,axis,-math.radians(q.get(name,0)))
  answer.append({'points':points,'thinNormal':n,'halfWidth':wide,'halfThickness':thin,'wireIds':keys})
 return answer

def channel_solid(s):
 ps=np.array(s['points']);t=np.gradient(ps,axis=0);t/=np.linalg.norm(t,axis=1)[:,None];n=np.array(s['thinNormal']);vs=[];fs=[]
 for p,tt in zip(ps,t):
  n-=tt*(n@tt);n/=np.linalg.norm(n);b=np.cross(tt,n)
  for x,y in [(1,1),(-1,1),(-1,-1),(1,-1)]:vs.append(p+x*s['halfThickness']*n+y*s['halfWidth']*b)
 for i in range(len(ps)-1):
  for j in range(4):a=i*4+j;b=i*4+(j+1)%4;c=(i+1)*4+j;d=(i+1)*4+(j+1)%4;fs.extend([[a,b,d],[a,d,c]])
 e=(len(ps)-1)*4;fs.extend([[0,2,1],[0,3,2],[e,e+1,e+2],[e,e+2,e+3]])
 m=trimesh.Trimesh(vs,fs,process=True);m.fix_normals();return g.conv(m)
