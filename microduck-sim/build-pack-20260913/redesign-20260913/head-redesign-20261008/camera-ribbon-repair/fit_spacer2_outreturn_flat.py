"""One fixed-side cavity topology, exact flat-to-cylindrical map; no board search."""
from pathlib import Path
import os,json,math,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
D=Path(__file__).resolve().parent;Q=D/'fixed-pose-local-bend';T=np.array(json.loads((Q/'pi-spacer2-pose.json').read_text())['worldTransform']);mouth=np.array(json.loads((Q/'pi-spacer2-pose.json').read_text())['csiMouthWorldMm']);target=mouth-4.4*T[:3,1];want=np.column_stack([-T[:3,1],-T[:3,2],T[:3,0]])
def family(x):
 C,A,B,DD,E,Rlast,F,alpha,phi1,phi2,lastangle,lastphi,u1angle=x
 ops=[('S',9),('B',math.pi-alpha,0,-1,1),('S',C),('B',math.pi,phi1,-1,1),('S',A),('B',u1angle,0,1,1.2),('S',B),('B',math.pi,0,1,1.35),('S',DD),('B',math.pi,phi2,1,1),('S',E),('B',lastangle,lastphi,1,Rlast),('S',F)]
 p=np.array([75.63,9.3706236-5,131.1145958]);t=np.array([0.,1,0]);w=np.array([0.,0,1]);s=0.;bends=[];pr=[]
 for op in ops:
  if op[0]=='S':
   L=op[1];pr.append({'kind':'straight','s0':s,'s1':s+L,'p':p.copy(),'t':t.copy(),'w':w.copy()});p=p+t*L;s+=L
  else:
   angle,phi,sign,R=op[1:];n=np.cross(t,w);e=w*math.cos(phi)+t*math.sin(phi);q=t*math.cos(phi)-w*math.sin(phi);L=R*angle/math.cos(phi);b={'kind':'cylindrical','s0':s,'s1':s+L,'p':p.copy(),'t':t.copy(),'w':w.copy(),'n':n,'e':e,'q':q,'angle':angle,'phi':phi,'sign':sign,'R':R};bends.append(b);pr.append(b);p=p+e*(R*angle*math.tan(phi))+q*R*math.sin(angle)+n*(sign*R*(1-math.cos(angle)));qp=q*math.cos(angle)+n*sign*math.sin(angle);t=e*math.sin(phi)+qp*math.cos(phi);w=e*math.cos(phi)-qp*math.sin(phi);s+=L
 return p,t,w,s,bends,pr
def residual(x):
 p,t,w,L,b,pr=family(x);rr=Rotation.from_matrix(want.T@np.column_stack([t,w,np.cross(t,w)])).as_rotvec()*30;gap=[z['s0']-a['s1']-8*abs(math.tan(a['phi']))-8*abs(math.tan(z['phi'])) for a,z in zip(b,b[1:])];return np.r_[p-target,rr,L-200,np.minimum(np.array(gap)-.3,0)*5]
if __name__=='__main__':
 lo=[30,8.5,14,8.5,40,1,5,.06,-.82,.75,3.0,-.01,3.06];hi=[37,16,35,30,66,6,15,.08,-.75,.82,3.28,.01,3.22];x0=[36,12,32,19,60,2.5,8,.07,-math.pi/4,math.pi/4,math.pi,0,math.pi];fit=least_squares(residual,x0,bounds=(lo,hi),max_nfev=500,xtol=1e-11,ftol=1e-11,gtol=1e-11);p,t,w,L,b,pr=family(fit.x);r={'integrationReady':False,'accepted':False,'scope':'One inter-board-cavity vertical serpentine; no obstacle acceptance until exactcheck','parameters':fit.x.tolist(),'maxConstraintResidual':float(max(abs(residual(fit.x)))),'materialLengthMm':L,'endpointMm':p.tolist(),'targetMm':target.tolist(),'endTangent':t.tolist(),'endWidth':w.tolist(),'primitives':[{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in z.items()} for z in pr],'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Q/'pi-spacer2-pose.json']}};(Q/'spacer2-rev2-outreturn-flat-fit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['primitives','sourceHashes']},indent=2))
