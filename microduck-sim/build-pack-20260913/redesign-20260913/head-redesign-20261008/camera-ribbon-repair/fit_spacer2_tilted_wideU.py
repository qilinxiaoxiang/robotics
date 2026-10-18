"""One fixed-side cavity topology, exact flat-to-cylindrical map; no board search."""
from pathlib import Path
import os,json,math,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
D=Path(__file__).resolve().parent;Q=D/'fixed-pose-local-bend';T=np.array(json.loads((Q/'pi-spacer2-pose.json').read_text())['worldTransform']);mouth=np.array(json.loads((Q/'pi-spacer2-pose.json').read_text())['csiMouthWorldMm']);target=mouth-4.4*T[:3,1];want=np.column_stack([-T[:3,1],-T[:3,2],T[:3,0]])
def family(x):
 C,bridge,north,south,up,E,Rlast,F,alpha,phi1,phi2,lastangle,lastphi,planarU=x
 C=50.5;bridge=10.;alpha=.07
 ops=[('S',9),('B',math.pi-alpha,-.04,-1,1),('S',C),('B',math.pi/2,0,1,1),('S',bridge),('B',math.pi/2,0,1,1),('S',north),('B',planarU,0,1,2),('S',south),('B',math.pi,phi1,1,1),('S',up),('B',math.pi,phi2,1,1),('S',E),('B',lastangle,lastphi,-1,Rlast),('S',F)]
 p=np.array([75.63,9.3706236-5,131.1145958]);t=np.array([0.,1,0]);w=np.array([0.,0,1]);s=0.;bends=[];pr=[]
 for op in ops:
  if op[0]=='S':
   L=op[1];pr.append({'kind':'straight','s0':s,'s1':s+L,'p':p.copy(),'t':t.copy(),'w':w.copy()});p=p+t*L;s+=L
  else:
   angle,phi,sign,R=op[1:];n=np.cross(t,w);e=w*math.cos(phi)+t*math.sin(phi);q=t*math.cos(phi)-w*math.sin(phi);L=R*angle/math.cos(phi);b={'kind':'cylindrical','s0':s,'s1':s+L,'p':p.copy(),'t':t.copy(),'w':w.copy(),'n':n,'e':e,'q':q,'angle':angle,'phi':phi,'sign':sign,'R':R};bends.append(b);pr.append(b);p=p+e*(R*angle*math.tan(phi))+q*R*math.sin(angle)+n*(sign*R*(1-math.cos(angle)));qp=q*math.cos(angle)+n*sign*math.sin(angle);t=e*math.sin(phi)+qp*math.cos(phi);w=e*math.cos(phi)-qp*math.sin(phi);s+=L
 return p,t,w,s,bends,pr
def residual(x):
 p,t,w,L,b,pr=family(x);rr=Rotation.from_matrix(want.T@np.column_stack([t,w,np.cross(t,w)])).as_rotvec()*30;gap=[z['s0']-a['s1']-5.75*abs(math.tan(a['phi']))-5.75*abs(math.tan(z['phi'])) for a,z in zip(b,b[1:])];ret=pr[12];yu=pr[7]['p'][1]+2;zlow=ret['p'][2]+(yu-ret['p'][1])*ret['t'][2]/ret['t'][1]-5.75*abs(ret['w'][2]-ret['w'][1]*ret['t'][2]/ret['t'][1]);return np.r_[p-target,rr,L-200,np.minimum(np.array(gap)-.3,0)*5,min(zlow-(pr[7]['p'][2]+5.75*abs(pr[7]['w'][2])+2*abs(pr[7]['n'][2])+2*abs(pr[7]['t'][2])+.5),0)*5]
if __name__=='__main__':
 old=json.loads((Q/'spacer2-tilted-complete-fit.json').read_text());base=np.array(old['parameters']);base[[0,1,8]]=[50.5,10,.07];base[6]=3.25;base[7]=8.6;ids=[2,3,4,5,6,7,9,10,11,12,13]
 def unpack(z):x=base.copy();x[ids]=z;return x
 lo=[10,6,9,24,3.25,8.4,.45,-1.05,3,-.35,3.02];hi=[42,28,19,61,6,16,1.05,-.45,3.28,.35,3.26]
 fit=least_squares(lambda z:residual(unpack(z)),base[ids],bounds=(lo,hi),max_nfev=700,xtol=1e-11,ftol=1e-11,gtol=1e-11);x=unpack(fit.x);p,t,w,L,b,pr=family(x);r={'accepted':False,'parameters':x.tolist(),'constraintResidual':residual(x).tolist(),'maxConstraintResidual':float(max(abs(residual(x)))),'materialLengthMm':L,'endpointMm':p.tolist(),'primitives':[{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in z.items()} for z in pr]};(Q/'spacer2-tilted-wideU-fit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='primitives'}))
