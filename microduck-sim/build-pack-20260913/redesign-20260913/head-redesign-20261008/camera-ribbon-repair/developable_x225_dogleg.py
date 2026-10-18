"""One bounded U-return family. Each curved piece is an isometric cylinder,
including oblique bend axes; this is not a twisted rectangular sweep.
Use run_bounded_cad.py for both the numeric fit and STL export.
"""
from pathlib import Path
import os,json,math,hashlib,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np
from scipy.optimize import least_squares, root
from scipy.spatial.transform import Rotation
D=Path(__file__).resolve().parent
pose=json.loads((D/'positive-x225-pose.json').read_text());T=np.array(pose['worldTransform']);mouth=np.array(pose['csiMouthWorldMm']);cam=np.array([75.63,9.3706236,131.1145958]);target=cam-[0,5,0]
R=3.;W=16.;thickness=.6
initial=(mouth-4.4*T[:3,1],T[:3,1],T[:3,2]);want=np.column_stack([[0,-1,0],[0,0,1],[-1,0,0.]])
def family(x):
 L1,L2,L3,L4,L5,phi2,phi4,a4,a5,phi3,phi5=x
 ops=[('S',8.4),('B',math.pi/2,0.,-1),('S',L1),('B',math.pi/2,phi2,-1),('S',L2),('B',math.pi,phi3,1),('S',L3),('B',math.pi/2+a4,phi4,1),('S',L4),('B',math.pi/2+a5,phi5,1),('S',12.),('B',math.acos(2/3),0.,1),('B',math.acos(2/3),0.,-1),('S',L5)]
 p,t,w=[a.copy() for a in initial];s=0.;bends=[];primitives=[]
 for op in ops:
  if op[0]=='S':
   L=op[1];primitives.append({'kind':'straight','s0':s,'s1':s+L,'p':p.copy(),'t':t.copy(),'w':w.copy()});p=p+t*L;s+=L
  else:
   ang,phi,sign=op[1:];n=np.cross(t,w);e=w*math.cos(phi)+t*math.sin(phi);q=t*math.cos(phi)-w*math.sin(phi);L=R*ang/math.cos(phi)
   b={'kind':'cylindrical','s0':s,'s1':s+L,'p':p.copy(),'t':t.copy(),'w':w.copy(),'n':n,'e':e,'q':q,'angle':ang,'phi':phi,'sign':sign,'R':R};bends.append(b);primitives.append(b)
   p=p+e*(R*ang*math.tan(phi))+q*(R*math.sin(ang))+n*(sign*R*(1-math.cos(ang)))
   qp=q*math.cos(ang)+n*(sign*math.sin(ang));t=e*math.sin(phi)+qp*math.cos(phi);w=e*math.cos(phi)-qp*math.sin(phi);s+=L
 return p,t,w,s,bends,primitives

def residual(x,regularize=True):
 p,t,w,L,_,_=family(x);F=np.column_stack([t,w,np.cross(t,w)]);r=np.r_[p-target,Rotation.from_matrix(want.T@F).as_rotvec()*30,L-200]
 return np.r_[r,(x[0]-2.0)*.01,(x[3]-18.0)*.01,(x[4]-30.0)*.01] if regularize else r

def solve():
 x0=[2.,60,60,18.,30.,-.02,.05,0,0,0,0];lo=[1.5,40,40,12,27,-.35,-.35,-.4,-.4,-.35,-.35];hi=[4,80,80,30,38,.15,.35,.4,.4,.35,.35]
 fit=least_squares(residual,x0,bounds=(lo,hi),max_nfev=180,xtol=1e-11,ftol=1e-11,gtol=1e-11)
 fit=least_squares(lambda x:residual(x,False),fit.x,bounds=(lo,hi),max_nfev=80,xtol=1e-12,ftol=1e-12,gtol=1e-12)
 free=[1,2,4,6,7,8,10];base=fit.x.copy()
 def pack(z):
  x=base.copy();x[free]=z;return x
 polish=root(lambda z:residual(pack(z),False),base[free],method='lm',options={'maxiter':200})
 trial=pack(polish.x)
 if np.all(trial>=lo) and np.all(trial<=hi) and np.linalg.norm(residual(trial,False))<np.linalg.norm(residual(fit.x,False)):fit.x=trial
 return fit

def material_map(s,v,bends,final):
 # Flat sheet coordinates are material arclength s and transverse v. Each
 # cylinder maps orthogonal (a,b) coordinates without stretching either.
 for b in bends:
  ds=s-b['s0'];phi=b['phi'];ac=ds*math.sin(phi)+v*math.cos(phi);bc=ds*math.cos(phi)-v*math.sin(phi)
  if bc<0:return b['p']+b['t']*ds+b['w']*v,b['n']
  if bc<=R*b['angle']:
   a=bc/R;q=b['q'];n=b['n'];sign=b['sign'];return b['p']+b['e']*ac+q*(R*math.sin(a))+n*(sign*R*(1-math.cos(a))),n*math.cos(a)-q*(sign*math.sin(a))
 p,t,w,L=final
 return p+t*(s-L)+w*v,np.cross(t,w)

